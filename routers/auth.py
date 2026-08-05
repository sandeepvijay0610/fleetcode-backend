from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
import bcrypt
import jwt
import os
from datetime import datetime, timezone, timedelta
import httpx

from database import get_session
from models import User, UserRegister, UserLogin, Squad

router = APIRouter()

SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload.update({"exp": expire})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: Session = Depends(get_session)):
    existing = db.exec(select(User).where(User.fleetCodeId == user_data.username)).first()
    if existing:
        raise HTTPException(status_code=400, detail="FleetCode ID already in use.")

    new_user = User(
        fleetCodeId=user_data.username,
        password=hash_password(user_data.password),
        leetCodeUsername=user_data.leetcode_username,
        isVerified=False,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token({"sub": user_data.username})
    return {
        "message": "Operator registered. Proceed to radar verification.",
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/login")
def login(user_data: UserLogin, db: Session = Depends(get_session)):
    user = db.exec(select(User).where(User.fleetCodeId == user_data.username)).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid Operator ID.")
    if not verify_password(user_data.password, user.password):
        raise HTTPException(status_code=400, detail="Invalid Passcode.")
    if not user.isVerified:
        raise HTTPException(status_code=403, detail="Radar verification incomplete.")

    access_token = create_access_token({"sub": user.fleetCodeId})
    squad_name = None
    if user.squad_id:
        squad = db.get(Squad, user.squad_id)
        if squad:
            squad_name = squad.name

    return {
        "message": "Authentication successful",
        "username": user.fleetCodeId,
        "squadName": squad_name,
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.get("/verify/{username}")
async def verify_leetcode(username: str, db: Session = Depends(get_session)):
    user = db.exec(select(User).where(User.fleetCodeId == username)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Operator not found.")
    if user.isVerified:
        return {"verified": True}

    query = """
    query recentSubmissions($username: String!, $limit: Int!) {
        recentSubmissionList(username: $username, limit: $limit) {
            titleSlug
            timestamp
        }
    }
    """
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(
                "https://leetcode.com/graphql",
                json={
                    "query": query,
                    "variables": {"username": user.leetCodeUsername, "limit": 20},
                },
                headers={"User-Agent": "Mozilla/5.0"},
            )
            data = res.json()
        except Exception as e:
            print(f"[Radar] Error: {e}")
            return {"verified": False}

    submissions = data.get("data", {}).get("recentSubmissionList")
    if not submissions:
        return {"verified": False}

    target = next((s for s in submissions if s["titleSlug"] == "find-the-duplicate-number"), None)
    if not target:
        return {"verified": False}

    submission_time = int(target["timestamp"])
    registered_at = int(user.created_at.timestamp())

    if submission_time >= (registered_at - 60):
        user.isVerified = True
        db.commit()
        return {"verified": True}

    return {"verified": False}