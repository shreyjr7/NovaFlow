import os
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlmodel import Session, select

from ..models.user_model import User, UserRole
from ..models.token_utils import decode_access_token

security = HTTPBearer()

def get_db():
    """Provide a DB session.
    Replace this with your actual database engine configuration.
    """
    from sqlmodel import create_engine
    engine = create_engine(os.getenv('DATABASE_URL'))
    with Session(engine) as session:
        yield session

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> User:
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get('sub')
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token payload')
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate credentials')
    stmt = select(User).where(User.id == user_id)
    user = db.exec(stmt).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User not found')
    return user

def require_role(*allowed_roles: UserRole):
    """Dependency that ensures the current user has one of the allowed_roles.
    Usage example::
        @router.get('/some-endpoint', dependencies=[Depends(require_role('SUPER_ADMIN', 'DATA_ANALYST'))])
    """
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Operation not permitted for your role',
            )
        return current_user
    return role_checker
