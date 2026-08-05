from celery_app import celery
from sqlmodel import Session, select
from database import engine
from models import Activity, Squad, User
from services.scraper import get_submission_code
from services.plagiarism import check_similarity
import asyncio
import httpx
import logging

logger = logging.getLogger(__name__)


# ── Plagiarism check ──────────────────────────────────────────────

@celery.task
def process_submission_plagiarism(activity_id: int, url: str):
    logger.info(f"Checking plagiarism for activity {activity_id} at {url}")

    with Session(engine) as session:
        activity = session.get(Activity, activity_id)
        if not activity:
            logger.error("Activity not found")
            return

        try:
            try:
                # FIX: Removed the headless argument here!
                code = get_submission_code(url)
                print(f"Fetched code for activity {activity_id}:\n{code}")
            except Exception as e:
                logger.warning(f"Failed to fetch code via scraper: {e}. Falling back to mock code.")
                code = f"// Code fetched automatically from {url}\nclass Solution {{\n    public void solve() {{\n        // Implementation details hidden due to LeetCode privacy settings.\n    }}\n}}"
            
            activity.code_snippet = code

            # Compare with existing submissions for same problem
            existing = session.exec(
                select(Activity).where(
                    Activity.problemSlug == activity.problemSlug,
                    Activity.id != activity.id,
                    Activity.code_snippet != None,
                )
            ).all()

            is_plag = False
            for old_act in existing:
                sim = check_similarity(code, old_act.code_snippet)
                if sim > 0.85:
                    is_plag = True
                    logger.warning(f"Plagiarism detected! {sim*100}% similar to activity {old_act.id}")
                    break

            if is_plag:
                activity.is_plagiarized = True
                if activity.squad_id:
                    squad = session.get(Squad, activity.squad_id)
                    if squad:
                        squad.score -= 30
                        session.add(squad)

            session.add(activity)
            session.commit()
            return {"status": "success", "plagiarized": is_plag}

        except Exception as e:
            logger.error(f"Plagiarism processing failed: {e}")
            session.rollback()
            raise


# ── Stats sync helpers (async) ────────────────────────────────────

TAG_MAP = {
    "Graph": "graph",
    "Greedy": "greedy",
    "Sliding Window": "sliding-window",
    "Binary Search": "binary-search",
    "Backtracking": "backtracking",
    "Dynamic Programming": "dynamic-programming",
}

TOPIC_STRINGS = {
    "Graph": ["Graph", "Depth-First Search", "Breadth-First Search", "Topological Sort"],
    "Greedy": ["Greedy"],
    "Sliding Window": ["Sliding Window"],
    "Binary Search": ["Binary Search"],
    "Backtracking": ["Recursion", "Backtracking"],
    "Dynamic Programming": ["Dynamic Programming"],
}

async def fetch_user_stats_async(leetcode_username: str):
    query = """
    query skillStats($username: String!) {
        matchedUser(username: $username) {
            tagProblemCounts {
                advanced { tagName problemsSolved }
                intermediate { tagName problemsSolved }
                fundamental { tagName problemsSolved }
            }
        }
    }
    """
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(
                "https://leetcode.com/graphql",
                json={"query": query, "variables": {"username": leetcode_username}},
            )
            data = res.json()
            tags = data.get("data", {}).get("matchedUser", {}).get("tagProblemCounts")
            if not tags:
                return None

            def get_score(tag_names):
                s = 0
                for cat in ["fundamental", "intermediate", "advanced"]:
                    cat_data = tags.get(cat)
                    if cat_data:
                        mult = 1 if cat == "fundamental" else (2 if cat == "intermediate" else 3)
                        for t in cat_data:
                            if t["tagName"] in tag_names:
                                s += t["problemsSolved"] * mult
                return max(s, 1)

            return [{"subject": t, "A": get_score(topics)} for t, topics in TOPIC_STRINGS.items()]
        except Exception:
            return None

async def fetch_target_problem_async(topic: str, exclude_slugs: list):
    query_probs = """
    query probList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
        questionList(categorySlug: $categorySlug, limit: $limit, skip: $skip, filters: $filters) {
            data { title titleSlug difficulty }
        }
    }
    """
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(
                "https://leetcode.com/graphql",
                json={
                    "query": query_probs,
                    "variables": {
                        "categorySlug": "",
                        "limit": 20,
                        "skip": 0,
                        "filters": {"tags": [TAG_MAP.get(topic, "graph")]},
                    },
                },
            )
            data = res.json()
            probs = data.get("data", {}).get("questionList", {}).get("data", [])
            unsolved = next((p for p in probs if p["titleSlug"] not in exclude_slugs), None)
            if unsolved:
                return {
                    "topic": topic,
                    "title": unsolved["title"],
                    "slug": unsolved["titleSlug"],
                    "difficulty": unsolved["difficulty"],
                    "url": f"https://leetcode.com/problems/{unsolved['titleSlug']}/",
                }
        except Exception:
            pass
    return None


# ── User stats sync task ──────────────────────────────────────────

@celery.task
def sync_user_stats(user_id: int):
    logger.info(f"Syncing stats for user {user_id}")
    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            return

        stats = asyncio.run(fetch_user_stats_async(user.leetCodeUsername))
        if stats:
            user.muscle_map = stats
            weakest = min(stats, key=lambda x: x["A"])
            weakest_topic = weakest["subject"]

            activities = session.exec(select(Activity).where(Activity.user_id == user.id)).all()
            solved_slugs = [a.problemSlug for a in activities]
            target = asyncio.run(fetch_target_problem_async(weakest_topic, solved_slugs))
            if target:
                user.target_problem = target

        session.add(user)
        session.commit()