"""User, Role, and UserRole models for NovaFlow backend."""

from typing import List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

class Role(SQLModel, table=True):
    __tablename__ = "roles"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True, nullable=False, unique=True)

    users: List["User"] = Relationship(back_populates="roles", link_model="UserRole")

class UserRole(SQLModel, table=True):
    __tablename__ = "user_roles"
    user_id: UUID = Field(foreign_key="users.id", primary_key=True)
    role_id: UUID = Field(foreign_key="roles.id", primary_key=True)

class User(SQLModel, table=True):
    __tablename__ = "users"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(index=True, nullable=False, unique=True)
    full_name: Optional[str] = Field(default=None)
    password_hash: str = Field(nullable=False)
    is_active: bool = Field(default=True, nullable=False)

    roles: List[Role] = Relationship(back_populates="users", link_model=UserRole)
