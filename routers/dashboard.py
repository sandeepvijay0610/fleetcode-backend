from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func
from database import get_session
from models import User, Squad, Activity

router = APIRouter()


@router.get("/{username}")
def get_dashboard(username: str, db: Session = Depends(get_session)):
    user = db.exec(select(User).where(User.fleetCodeId == username)).first()
    if not user or not user.squad_id:
        return {"hasSquad": False}

    squad = db.get(Squad, user.squad_id)
    if not squad:
        return {"hasSquad": False}

    # Calculate rank (how many squads have higher score)
    higher_scoring = db.exec(
        select(func.count()).where(Squad.score > squad.score)
    ).one()

    # Build roster
    roster = []
    for member in squad.users:
        member_solved = db.exec(
            select(func.count(Activity.id))
            .where(Activity.user_id == member.id)
            .where(Activity.squad_id == squad.id)
        ).one()
        
        member_score = db.exec(
            select(func.sum(Activity.xpAwarded))
            .where(Activity.user_id == member.id)
            .where(Activity.squad_id == squad.id)
        ).one() or 0

        # Calculate streak
        user_activities = db.exec(
            select(Activity.solvedAt)
            .where(Activity.user_id == member.id)
            .order_by(Activity.solvedAt.desc())
        ).all()
        
        member_streak = 0
        if user_activities:
            from datetime import datetime, timedelta
            unique_dates = sorted(list({a.date() for a in user_activities}), reverse=True)
            today = datetime.utcnow().date()
            if unique_dates:
                if unique_dates[0] == today or unique_dates[0] == (today - timedelta(days=1)):
                    member_streak = 1
                    current = unique_dates[0]
                    for d in unique_dates[1:]:
                        if (current - d).days == 1:
                            member_streak += 1
                            current = d
                        else:
                            break
                            
        # Calculate topic counts
        topic_counts = {
            "Hashing": 0, "Recursion": 0, "Backtracking": 0, "Sort": 0, 
            "Search": 0, "Greedy": 0, "DP": 0, "BFS": 0, "DFS": 0, "Others": 0
        }
        
        member_full_activities = db.exec(
            select(Activity)
            .where(Activity.user_id == member.id)
            .where(Activity.squad_id == squad.id)
        ).all()
        
        for activity in member_full_activities:
            for t in (activity.topics or []):
                t_lower = t.lower()
                matched = False
                if "hash" in t_lower:
                    topic_counts["Hashing"] += 1
                    matched = True
                elif "recursion" in t_lower:
                    topic_counts["Recursion"] += 1
                    matched = True
                elif "backtracking" in t_lower:
                    topic_counts["Backtracking"] += 1
                    matched = True
                elif "sort" in t_lower:
                    topic_counts["Sort"] += 1
                    matched = True
                elif "search" in t_lower:
                    if "breadth" in t_lower or "bfs" in t_lower:
                        topic_counts["BFS"] += 1
                    elif "depth" in t_lower or "dfs" in t_lower:
                        topic_counts["DFS"] += 1
                    else:
                        topic_counts["Search"] += 1
                    matched = True
                elif "greedy" in t_lower:
                    topic_counts["Greedy"] += 1
                    matched = True
                elif "dynamic" in t_lower or "memoization" in t_lower or "dp" in t_lower:
                    topic_counts["DP"] += 1
                    matched = True
                elif "breadth" in t_lower or "bfs" in t_lower:
                    topic_counts["BFS"] += 1
                    matched = True
                elif "depth" in t_lower or "dfs" in t_lower:
                    topic_counts["DFS"] += 1
                    matched = True
                
                # If we mapped this topic to a known category, we are done with this activity
                if matched:
                    break
            else:
                # If none of the activity's topics matched our predefined list (or it had no topics)
                # Count it as 'Others' exactly once
                if activity.topics:
                    topic_counts["Others"] += 1

        roster.append({
            "fleetCodeId": member.fleetCodeId,
            "leetCodeUsername": member.leetCodeUsername,
            "username": member.fleetCodeId,
            "leetcode_username": member.leetCodeUsername,
            "solved": member_solved,
            "score": member_score,
            "streak": member_streak,
            "topicCounts": topic_counts,
            "muscleMap": member.muscle_map if member.muscle_map else [],
        })

    # Recent activities
    recent = db.exec(
        select(Activity)
        .where(Activity.squad_id == squad.id)
        .order_by(Activity.solvedAt.desc())
        .limit(50)
    ).all()

    activities_data = [
        {
            "problemName": a.problemName,
            "solvedAt": a.solvedAt.isoformat(),
            "xpAwarded": a.xpAwarded,
            "is_plagiarized": a.is_plagiarized,
            "username": a.user.fleetCodeId if a.user else "Unknown",
            "code_snippet": a.code_snippet,
        }
        for a in recent
    ]

    # Calculate total solved
    total_solved = db.exec(
        select(func.count(Activity.id)).where(Activity.squad_id == squad.id)
    ).one()

    return {
        "hasSquad": True,
        "squadName": squad.name,
        "score": squad.score,
        "total_solved": total_solved,
        "rank": higher_scoring + 1,
        "streak": squad.streak,
        "roster": roster,
        "target": user.target_problem if user.target_problem else None,
        "weakestTopic": user.target_problem.get("topic") if user.target_problem else "Unknown",
        "activities": activities_data,
    }