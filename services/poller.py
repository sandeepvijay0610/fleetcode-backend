import httpx
from datetime import datetime, timezone
from sqlmodel import Session, select
from database import engine
from models import User, Squad, Activity

LEETCODE_QUERY = """
query recentAcSubmissions($username: String!, $limit: Int!) {
    recentAcSubmissionList(username: $username, limit: $limit) {
        id
        title
        titleSlug
        timestamp
    }
}
"""

QUESTION_QUERY = """
query questionData($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    difficulty
    topicTags {
      name
    }
  }
}
"""

# Track when the poller started – only count submissions after this time
POLLER_START_TIME = datetime.now(timezone.utc).timestamp()


async def fetch_user_submissions(client, user, session):
    """Fetch recent submissions for one user, detect new solves, award XP."""
    print(f"[RADAR] Scanning {user.leetCodeUsername}...")
    try:
        res = await client.post(
            "https://leetcode.com/graphql",
            json={
                "query": LEETCODE_QUERY,
                "variables": {"username": user.leetCodeUsername, "limit": 10},
            },
            headers={"User-Agent": "Mozilla/5.0"},
        )
        data = res.json()
        submissions = data.get("data", {}).get("recentAcSubmissionList", [])

        new_solve_detected = False

        for sub in submissions:
            solved_time = datetime.fromtimestamp(int(sub["timestamp"]), tz=timezone.utc)

            # Skip submissions that existed before the poller started
            if solved_time.timestamp() < POLLER_START_TIME:
                continue

            # Check if this submission is already recorded
            existing = session.exec(
                select(Activity)
                .where(Activity.user_id == user.id)
                .where(Activity.problemSlug == sub["titleSlug"])
            ).first()

            if not existing:
                print(f"[RADAR] 🎯 NEW SOLVE: {user.fleetCodeId} solved {sub['title']}")
                new_solve_detected = True

                new_activity = Activity(
                    user_id=user.id,
                    squad_id=user.squad_id,
                    problemName=sub["title"],
                    problemSlug=sub["titleSlug"],
                    solvedAt=solved_time.replace(tzinfo=None),
                    xpAwarded=10,
                )
                
                # Fetch topics for the new activity
                try:
                    q_res = await client.post(
                        "https://leetcode.com/graphql",
                        json={
                            "query": QUESTION_QUERY,
                            "variables": {"titleSlug": sub["titleSlug"]}
                        },
                        headers={"User-Agent": "Mozilla/5.0"}
                    )
                    q_data = q_res.json()
                    question = q_data.get("data", {}).get("question", {})
                    if question:
                        new_activity.topics = [t["name"] for t in question.get("topicTags", [])]
                        new_activity.difficulty = question.get("difficulty", "Unknown")
                except Exception as e:
                    print(f"[RADAR] Error fetching topics for {sub['titleSlug']}: {e}")

                session.add(new_activity)

                # Award XP to squad
                squad = session.get(Squad, user.squad_id) if user.squad_id else None
                if squad:
                    squad.score += 10

                session.commit()
                session.refresh(new_activity)

                # Dispatch plagiarism check
                try:
                    if "id" in sub:
                        sub_url = f"https://leetcode.com/problems/{sub['titleSlug']}/submissions/{sub['id']}/"
                        from tasks import process_submission_plagiarism
                        process_submission_plagiarism.delay(new_activity.id, sub_url)
                        print(f"[RADAR] 🚀 Dispatched plagiarism task for {new_activity.id}")
                except Exception as e:
                    print(f"[RADAR] ⚠️ Failed to dispatch plagiarism task: {e}")

        # If they solved something new, refresh their stats cache
        if new_solve_detected:
            try:
                from tasks import sync_user_stats
                sync_user_stats.delay(user.id)
                print(f"[RADAR] 🔄 Dispatched stats sync for {user.fleetCodeId}")
            except Exception as e:
                print(f"[RADAR] ⚠️ Failed to dispatch stats sync: {e}")

    except Exception as e:
        print(f"[RADAR] ❌ Failed to scan {user.leetCodeUsername}: {e}")


async def runRadarSweep(db=None):
    """Run a full radar sweep across all verified, squad-linked users."""
    import asyncio
    print("=" * 45)
    print("[RADAR] 📡 INITIATING GLOBAL RADAR SWEEP...")

    session = db if db else Session(engine)

    try:
        active_users = session.exec(
            select(User).where(User.isVerified == True, User.squad_id != None)
        ).all()

        print(f"[RADAR] Found {len(active_users)} active operators.")

        async with httpx.AsyncClient() as client:
            tasks = [fetch_user_submissions(client, u, session) for u in active_users]
            await asyncio.gather(*tasks)

        print("[RADAR] ✅ SWEEP COMPLETE.")
        print("=" * 45 + "\n")

    except Exception as e:
        print(f"[RADAR] ❌ CRITICAL ENGINE FAILURE: {e}")
    finally:
        if not db:
            session.close()


def start_poller():
    """Launch the APScheduler background poller with an 8‑second interval."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(runRadarSweep, "interval", seconds=8)
    scheduler.start()
    print("⚙️  Radar Poller Armed – sweeping every 8 seconds.")