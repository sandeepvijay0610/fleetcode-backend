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
        roster.append({
            "fleetCodeId": member.fleetCodeId,
            "leetCodeUsername": member.leetCodeUsername,
            "muscleMap": member.muscle_map if member.muscle_map else [],
        })

    # Recent activities
    recent = db.exec(
        select(Activity)
        .where(Activity.squad_id == squad.id)
        .order_by(Activity.solvedAt.desc())
        .limit(5)
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

    return {
        "hasSquad": True,
        "squadName": squad.name,
        "score": squad.score,
        "rank": higher_scoring + 1,
        "streak": squad.streak,
        "roster": roster,
        "target": user.target_problem if user.target_problem else None,
        "weakestTopic": user.target_problem.get("topic") if user.target_problem else "Unknown",
        "activities": activities_data,
    }