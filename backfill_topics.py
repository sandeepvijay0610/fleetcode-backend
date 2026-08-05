import httpx
from sqlmodel import Session, select
from database import engine
from models import Activity

query = """
query questionData($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    difficulty
    topicTags {
      name
    }
  }
}
"""

def update_activities():
    with Session(engine) as session:
        activities = session.exec(select(Activity)).all()
        
        for activity in activities:
            if not activity.topics or activity.topics == []:
                print(f"Fetching topics for {activity.problemSlug}...")
                with httpx.Client() as client:
                    try:
                        res = client.post(
                            "https://leetcode.com/graphql",
                            json={
                                "query": query,
                                "variables": {"titleSlug": activity.problemSlug}
                            },
                            headers={"User-Agent": "Mozilla/5.0"}
                        )
                        data = res.json()
                        question = data.get("data", {}).get("question", {})
                        if question:
                            tags = [t["name"] for t in question.get("topicTags", [])]
                            difficulty = question.get("difficulty", "Unknown")
                            activity.topics = tags
                            if difficulty:
                                activity.difficulty = difficulty
                            session.add(activity)
                            print(f"Updated {activity.problemSlug}: {tags}, {difficulty}")
                        else:
                            print(f"Failed to fetch {activity.problemSlug}")
                    except Exception as e:
                        print(f"Error fetching {activity.problemSlug}: {e}")
        session.commit()
        print("Done!")

if __name__ == "__main__":
    update_activities()
