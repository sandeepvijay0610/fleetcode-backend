from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from database import get_session
from models import Squad

router = APIRouter()


@router.get("/")
def get_leaderboard(db: Session = Depends(get_session)):
    squads = db.exec(select(Squad).order_by(Squad.score.desc()).limit(10)).all()
    return [
        {
            "rank": idx + 1,
            "name": squad.name,
            "score": squad.score,
            "streak": squad.streak,
        }
        for idx, squad in enumerate(squads)
    ]