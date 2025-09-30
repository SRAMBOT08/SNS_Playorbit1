from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from uuid import uuid4

def gen_uuid():
    return str(uuid4())

class Floor(SQLModel, table=True):
    id: str = Field(default_factory=gen_uuid, primary_key=True)
    name: str
    wing: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class User(SQLModel, table=True):
    id: str = Field(default_factory=gen_uuid, primary_key=True)
    name: str
    email: str = Field(index=True, unique=True)
    password_hash: str
    role: str = Field(default="student")  # student|mentor|floorwing|admin
    floor_id: Optional[str] = Field(default=None, foreign_key="floor.id")
    points_total: int = 0
    is_banned: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
