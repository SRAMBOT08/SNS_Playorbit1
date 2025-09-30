from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field
from uuid import uuid4

def gen_uuid():
    return str(uuid4())

class PointsLog(SQLModel, table=True):
    id: str = Field(default_factory=gen_uuid, primary_key=True)
    user_id: str
    points: int
    reason: Optional[str] = None
    assigned_by: Optional[str] = None
    activity_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    month: str = Field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m"))

class Badge(SQLModel, table=True):
    id: str = Field(default_factory=gen_uuid, primary_key=True)
    name: str
    description: Optional[str] = None
    icon_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Milestone(SQLModel, table=True):
    id: str = Field(default_factory=gen_uuid, primary_key=True)
    title: str
    points_required: int
    badge_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserBadge(SQLModel, table=True):
    id: str = Field(default_factory=gen_uuid, primary_key=True)
    user_id: str
    badge_id: str
    awarded_at: datetime = Field(default_factory=datetime.utcnow)
