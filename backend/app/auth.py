import os
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from ..models.user_model import User, UserRole
from ..models.password_utils import verify_password, hash_password
from ..models.token_utils import create_access_token, decode_access_token
from sqlmodel import select

router = APIRouter()

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginRequest(BaseModel):
    email: str
    password: str

def get_db():
    # Placeholder DB session getter; replace with actual dependency
    from sqlmodel import Session, create_engine
    engine = create_engine(os.getenv('DATABASE_URL'))
    with Session(engine) as session:
        yield session

@router.post('/login', response_model=Token)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    stmt = select(User).where(User.email == request.email)
    user = db.exec(stmt).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid credentials')
    access_token = create_access_token({sub: str(user.id), role: user.role})
    return Token(access_token=access_token)
