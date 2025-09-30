from sqlmodel import Session, select
from .models_gamify import PointsLog, Milestone, UserBadge, Badge
from .models import User
from .db import engine
from datetime import datetime
import redis
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = redis.from_url(REDIS_URL, decode_responses=True)

def award_points(session: Session, target_user_id: str, points: int, assigned_by: str = None, reason: str = None, activity_id: str = None):
    # atomic-ish: we do this in a DB transaction (Session commit at end)
    user = session.get(User, target_user_id)
    if not user:
        raise ValueError("target user not found")

    # insert log
    log = PointsLog(user_id=target_user_id, points=points, reason=reason, assigned_by=assigned_by, activity_id=activity_id)
    session.add(log)

    # update denormalized total
    user.points_total = (user.points_total or 0) + points
    session.add(user)

    # monthly summary update could be done here (omitted for brevity)

    # commit happens in caller (so they manage session.commit())

    # publish to redis for realtime updates
    payload = {
        "type": "points.awarded",
        "user_id": target_user_id,
        "delta": points,
        "new_total": user.points_total,
        "reason": reason
    }
    try:
        r.publish(f"user:{target_user_id}:notifications", str(payload))
        # also notify floor/leaderboard channel if user has floor
        if user.floor_id:
            r.publish(f"floor:{user.floor_id}:leaderboard", str({"type":"leaderboard.update","user_id":target_user_id,"new_total":user.points_total}))
    except Exception:
        # Redis optional — failures shouldn't block award
        pass

    return log

def check_and_award_milestones(session: Session, user_id: str):
    # find milestones <= user.points_total and not yet awarded
    user = session.get(User, user_id)
    if not user: 
        return []
    stmt = select(Milestone).where(Milestone.points_required <= user.points_total)
    milestones = session.exec(stmt).all()
    awarded = []
    for m in milestones:
        # check user already has badge (if milestone.badge_id)
        if not m.badge_id:
            continue
        q = select(UserBadge).where(UserBadge.user_id == user_id, UserBadge.badge_id == m.badge_id)
        exists = session.exec(q).first()
        if exists:
            continue
        ub = UserBadge(user_id=user_id, badge_id=m.badge_id)
        session.add(ub)
        awarded.append(m)
        # notify
        try:
            r.publish(f"user:{user_id}:notifications", str({"type":"milestone.unlocked","milestone_id":m.id,"badge_id":m.badge_id,"title":m.title}))
        except Exception:
            pass
    return awarded
