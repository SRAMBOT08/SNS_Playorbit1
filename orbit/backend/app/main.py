from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import SQLModel, select
from dotenv import load_dotenv
import os

load_dotenv()

from .db import engine, get_session
from .models import User, Floor
from .security import hash_password, verify_password, create_access_token, decode_access_token

app = FastAPI(title="SNS_Playorbit - Backend")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

@app.on_event("startup")
def on_startup():
    # create tables (dev convenience). We'll move to Alembic later.
    SQLModel.metadata.create_all(engine)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"msg": "SNS_Playorbit backend up. Visit /docs for API docs."}

# ---- Auth / Users ----
@app.post("/auth/register", status_code=201)
def register(name: str, email: str, password: str, session=Depends(get_session)):
    # check exists
    stmt = select(User).where(User.email == email)
    existing = session.exec(stmt).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(name=name, email=email, password_hash=hash_password(password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role}

@app.post("/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), session=Depends(get_session)):
    stmt = select(User).where(User.email == form_data.username)
    user = session.exec(stmt).first()
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if user.is_banned:
        raise HTTPException(status_code=403, detail="User is banned")
    token = create_access_token({"sub": user.id, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}

# dependency to get current user
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

@app.get("/users/me")
def users_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "floor_id": current_user.floor_id,
        "points_total": current_user.points_total
    }
