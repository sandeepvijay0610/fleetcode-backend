from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from datetime import datetime
from pydantic import BaseModel


# ─── Database Tables (SQLModel) ───────────────────────────────────

class Squad(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    score: int = Field(default=0)
    streak: int = Field(default=0)
    spotterTokens: int = Field(default=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    users: List["User"] = Relationship(back_populates="squad")
    activities: List["Activity"] = Relationship(back_populates="squad")


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    fleetCodeId: str = Field(unique=True, index=True)
    password: str
    leetCodeUsername: str
    isVerified: bool = Field(default=False)

    radarArrays: int = Field(default=0)
    radarDP: int = Field(default=0)
    radarTrees: int = Field(default=0)
    radarStrings: int = Field(default=0)
    radarMath: int = Field(default=0)
    radarGraphs: int = Field(default=0)

    muscle_map: Optional[List[dict]] = Field(default=None, sa_column=Column(JSON))
    target_problem: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow)

    squad_id: Optional[int] = Field(default=None, foreign_key="squad.id")
    squad: Optional[Squad] = Relationship(back_populates="users")

    activities: List["Activity"] = Relationship(back_populates="user")


class Activity(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    problemName: str
    problemSlug: str
    difficulty: str = Field(default="Unknown")
    topics: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    solvedAt: datetime
    xpAwarded: int = Field(default=10)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user_id: int = Field(foreign_key="user.id")
    user: User = Relationship(back_populates="activities")

    squad_id: Optional[int] = Field(default=None, foreign_key="squad.id")
    squad: Optional[Squad] = Relationship(back_populates="activities")

    code_snippet: Optional[str] = Field(default=None)
    is_plagiarized: bool = Field(default=False)


# ─── Request/Response Schemas ─────────────────────────────────────

class UserRegister(BaseModel):
    username: str
    password: str
    leetcode_username: str


class UserLogin(BaseModel):
    username: str
    password: str


class SquadCreate(BaseModel):
    username: str
    squad_name: str


class SquadJoin(BaseModel):
    username: str
    squad_id: str


class LeaveSquad(BaseModel):
    username: str