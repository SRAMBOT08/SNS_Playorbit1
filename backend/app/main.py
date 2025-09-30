# backend/app/main.py
from fastapi import FastAPI, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import SQLModel, select
from dotenv import load_dotenv
import os

load_dotenv()

# ---- app instance ----
app = FastAPI(title="SNS_Playorbit - Backend")

# ---- DB/session imports (must exist) ----
from .db import engine, get_session
from .models import User, Floor  # ensure these files exist
# optional gamify imports if you created them
from .models_gamify import PointsLog, Badge, Milestone, UserBadge
from .gamify import award_points as gamify_award_points, check_and_award_milestones

# ---- security helpers (must exist) ----
from .security import hash_password, verify_password, create_access_token, decode_access_token

# after `app = FastAPI(...)`
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version="1.0.0",
        description="SNS Playorbit API",
        routes=app.routes,
    )
    # add bearer security
    openapi_schema["components"].setdefault("securitySchemes", {})
    openapi_schema["components"]["securitySchemes"]["bearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT"
    }
    # make all endpoints use bearer by default in UI (optional)
    openapi_schema["security"] = [{"bearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# OAuth2 config
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# create tables on startup
@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

# ---- simple endpoints ----
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"msg": "SNS_Playorbit backend up. Visit /docs for API docs."}

# ---- auth endpoints (register/login) ----
@app.post("/auth/register", status_code=201)
def register(name: str = Body(...), email: str = Body(...), password: str = Body(...), role: str = Body(...), session=Depends(get_session)):
    stmt = select(User).where(User.email == email)
    existing = session.exec(stmt).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(name=name, email=email, password_hash=hash_password(password), role=role)
    session.add(user)
    session.commit()
    session.refresh(user)
    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role}

@app.post("/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), session=Depends(get_session)):
    stmt = select(User).where(User.email == form_data.username)
    user = session.exec(stmt).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if user.is_banned:
        raise HTTPException(status_code=403, detail="User is banned")
    token = create_access_token({"sub": user.id, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}

# ---- dependency: get_current_user ----
def get_current_user(token: str = Depends(oauth2_scheme), session=Depends(get_session)) -> User:
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    stmt = select(User).where(User.id == user_id)
    user = session.exec(stmt).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# ---- Gamification endpoints ----
@app.post("/points/award")
def api_award_points(
    target_user_id: str = Body(...),
    points: int = Body(...),
    reason: str = Body(None),
    activity_id: str = Body(None),
    session=Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    # permission check
    if current_user.role not in ("mentor", "floorwing", "admin"):
        raise HTTPException(status_code=403, detail="Not allowed")
    try:
        # use gamify helper which expects a session
        log = gamify_award_points(session, target_user_id, points, assigned_by=current_user.id, reason=reason, activity_id=activity_id)
        session.commit()
        session.refresh(log)
        awarded = check_and_award_milestones(session, target_user_id)
        session.commit()
        new_total = session.get(User, target_user_id).points_total
        return {"ok": True, "log_id": log.id, "new_total": new_total, "milestones": [m.id for m in awarded]}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/floors/{floor_id}/leaderboard")
def leaderboard(floor_id: str, limit: int = 10, session=Depends(get_session)):
    stmt = select(User).where(User.floor_id == floor_id).order_by(User.points_total.desc()).limit(limit)
    rows = session.exec(stmt).all()
    return [{"id": u.id, "name": u.name, "points_total": u.points_total} for u in rows]
