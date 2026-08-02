from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from database import get_session
from models import User, Squad, SquadCreate, SquadJoin, LeaveSquad
from services.poller import runRadarSweep

router = APIRouter()


@router.post("/create", status_code=status.HTTP_201_CREATED)
def create_squad(data: SquadCreate, db: Session = Depends(get_session)):
    # Check squad name uniqueness
    existing = db.exec(select(Squad).where(Squad.name == data.squad_name)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Squad name already in use.")

    user = db.exec(select(User).where(User.fleetCodeId == data.username)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Operator not found.")
    if user.squad_id:
        raise HTTPException(status_code=400, detail="Operator already in a squad.")

    new_squad = Squad(name=data.squad_name)
    db.add(new_squad)
    db.commit()
    db.refresh(new_squad)

    user.squad_id = new_squad.id
    db.commit()

    return {"message": "Squad created successfully.", "squad_name": new_squad.name}


@router.post("/join")
def join_squad(data: SquadJoin, db: Session = Depends(get_session)):
    user = db.exec(select(User).where(User.fleetCodeId == data.username)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Operator not found.")
    if user.squad_id:
        raise HTTPException(status_code=400, detail="Operator already in a squad.")

    squad = db.exec(select(Squad).where(Squad.name == data.squad_id)).first()
    if not squad:
        raise HTTPException(status_code=404, detail="Squad not found.")
    if len(squad.users) >= 4:
        raise HTTPException(status_code=400, detail="Squad is full (max 4 members).")

    user.squad_id = squad.id
    db.commit()

    return {"message": "Joined squad successfully.", "squad_name": squad.name}


@router.post("/leave")
def leave_squad(data: LeaveSquad, db: Session = Depends(get_session)):
    user = db.exec(select(User).where(User.fleetCodeId == data.username)).first()
    if not user or not user.squad_id:
        raise HTTPException(status_code=400, detail="Operator is not in a squad.")

    user.squad_id = None
    db.commit()
    return {"message": "Left the squad."}


@router.get("/force-sync")
async def force_sync(db: Session = Depends(get_session)):
    try:
        await runRadarSweep(db)
        return {"message": "Manual radar sweep executed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))