from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON
from typing import List, Optional
import uuid
from datetime import datetime

class User(SQLModel, table=True):
    __tablename__ = "users"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    role: str = Field(default="STUDENT")
    is_verified: bool = Field(default=False)
    is_premium: bool = Field(default=False)
    failed_attempts: int = Field(default=0)
    locked_until: Optional[datetime] = None


class OAuthIdentity(SQLModel, table=True):
    __tablename__ = "oauth_identities"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    provider: str
    provider_user_id: str = Field(index=True)
    user_id: str = Field(foreign_key="users.id")

class UserProfile(SQLModel, table=True):
    __tablename__ = "user_profiles"
    user_id: str = Field(foreign_key="users.id", primary_key=True)
    full_name: str
    skills: List[str] = Field(default=[], sa_column=Column(JSON))
    goals: List[str] = Field(default=[], sa_column=Column(JSON))


class Doubt(SQLModel, table=True):
    __tablename__ = "doubts"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="users.id")
    title: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved: bool = Field(default=False)