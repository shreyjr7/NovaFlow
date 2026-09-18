from __future__ import annotations
import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from .database.session import get_session
from .models.entities import UserModel

router = APIRouter(tags=["Authentication and RBAC"])

JWT_SECRET = os.getenv("JWT_SECRET", "novaflow-secret-super-secure-key-2026-sih")
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRE_SECONDS = 3600 * 24

ROLE_PERMISSIONS: Dict[str, List[str]] = {
    "ADMIN": ["*"],
    "TRAFFIC POLICE": ["incidents", "anpr", "congestion", "alerts", "evidence", "fleet"],
    "ROAD ENGINEER": ["road_defects", "potholes", "waterlogging", "maintenance", "infrastructure"],
    "ANALYST": ["analytics", "heatmaps", "route_delay", "od_matrix", "reports", "fleet_summary"],
}

DEFAULT_USERS = [
    {
        "username": "admin_user",
        "email": "admin@novaflow.gov.in",
        "password": "admin123",
        "role": "ADMIN",
        "department": "City Transit Command Authority",
    },
    {
        "username": "traffic_officer",
        "email": "police@novaflow.gov.in",
        "password": "police123",
        "role": "TRAFFIC POLICE",
        "department": "Traffic Police Division and Quick Response",
    },
    {
        "username": "road_inspector",
        "email": "engineer@novaflow.gov.in",
        "password": "engineer123",
        "role": "ROAD ENGINEER",
        "department": "Public Works and Infrastructure Engineering",
    },
    {
        "username": "transit_analyst",
        "email": "analyst@novaflow.gov.in",
        "password": "analyst123",
        "role": "ANALYST",
        "department": "Urban Transport Analytics and Planning",
    },
]

def hash_password(password: str) -> str:
    salt = "novaflow_salt_2026"
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hmac.compare_digest(hash_password(plain_password), hashed_password)

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

def _b64url_decode(s: str) -> bytes:
    padding = "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s + padding)

def create_access_token(payload: Dict[str, Any], expires_in: int = TOKEN_EXPIRE_SECONDS) -> str:
    now = int(time.time())
    data = dict(payload)
    data["iat"] = now
    data["exp"] = now + expires_in
    data["iss"] = "novaflow-auth"
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    h_enc = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    p_enc = _b64url_encode(json.dumps(data, separators=(",", ":")).encode("utf-8"))
    sig = hmac.new(JWT_SECRET.encode("utf-8"), f"{h_enc}.{p_enc}".encode("utf-8"), hashlib.sha256).digest()
    return f"{h_enc}.{p_enc}.{_b64url_encode(sig)}"

def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")
        h_enc, p_enc, sig_enc = parts
        exp_sig = hmac.new(JWT_SECRET.encode("utf-8"), f"{h_enc}.{p_enc}".encode("utf-8"), hashlib.sha256).digest()
        if not hmac.compare_digest(exp_sig, _b64url_decode(sig_enc)):
            raise ValueError("Invalid token signature")
        payload = json.loads(_b64url_decode(p_enc).decode("utf-8"))
        if payload.get("exp", 0) < int(time.time()):
            raise ValueError("Token has expired")
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication token invalid or expired: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

def seed_default_users_if_needed(session: Session) -> None:
    try:
        existing = session.exec(select(UserModel)).first()
        if not existing:
            for u in DEFAULT_USERS:
                user = UserModel(
                    username=u["username"],
                    email=u["email"],
                    hashed_password=hash_password(u["password"]),
                    role=u["role"],
                    department=u["department"],
                    is_active=True,
                )
                session.add(user)
            session.commit()
    except Exception:
        session.rollback()

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]
    permissions: List[str]

@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, session: Session = Depends(get_session)):
    seed_default_users_if_needed(session)
    user = session.exec(select(UserModel).where(UserModel.email == request.email.strip())).first()
    if not user:
        for u in DEFAULT_USERS:
            if u["email"].lower() == request.email.strip().lower() and u["password"] == request.password:
                user = UserModel(
                    username=u["username"],
                    email=u["email"],
                    hashed_password=hash_password(u["password"]),
                    role=u["role"],
                    department=u["department"],
                    is_active=True,
                )
                session.add(user)
                try:
                    session.commit()
                except Exception:
                    session.rollback()
                break
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )
    perms = ROLE_PERMISSIONS.get(user.role, [])
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "department": user.department,
    }
    return TokenResponse(
        access_token=create_access_token(payload),
        token_type="bearer",
        user=user.to_dict(),
        permissions=perms,
    )

def get_current_user(
    authorization: Optional[str] = Header(None),
    session: Session = Depends(get_session),
) -> Dict[str, Any]:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
        )
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization format. Expected 'Bearer <token>'",
        )
    return decode_access_token(parts[1])

def require_role(allowed_roles: List[str]):
    def role_checker(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = user.get("role", "")
        if "ADMIN" == user_role:
            return user
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Role '{user_role}' lacks required permissions: {allowed_roles}",
            )
        return user
    return role_checker

@router.get("/me")
def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    role = current_user.get("role", "ANALYST")
    return {"user": current_user, "permissions": ROLE_PERMISSIONS.get(role, [])}

@router.get("/roles")
def list_roles():
    return {
        "roles": [
            {"role": "ADMIN", "description": "Full governance, system control and user admin", "permissions": ROLE_PERMISSIONS["ADMIN"]},
            {"role": "TRAFFIC POLICE", "description": "Incident dispatch, ANPR hits, real-time alerts and evidence lock", "permissions": ROLE_PERMISSIONS["TRAFFIC POLICE"]},
            {"role": "ROAD ENGINEER", "description": "Potholes, waterlogging, pavement degradation and repair scheduling", "permissions": ROLE_PERMISSIONS["ROAD ENGINEER"]},
            {"role": "ANALYST", "description": "Urban heatmaps, route delay modeling, OD matrices and mobility trends", "permissions": ROLE_PERMISSIONS["ANALYST"]},
        ]
    }

@router.get("/users")
def list_system_users(session: Session = Depends(get_session)):
    seed_default_users_if_needed(session)
    users = session.exec(select(UserModel)).all()
    return {"total": len(users), "users": [u.to_dict() for u in users]}
