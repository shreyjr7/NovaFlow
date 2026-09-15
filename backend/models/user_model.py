from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4
from typing import Literal

UserRole = Literal[
    "SUPER_ADMIN",
    "TRANSPORT_AUTHORITY",
    "TRAFFIC_POLICE",
    "ROAD_MAINTENANCE",
    "DATA_ANALYST",
    "BUS_OPERATOR",
    "FIELD_ENGINEER",
    "RESEARCHER",
    "PUBLIC_USER",
]

class User(SQLModel, table=True):
 id: UUID = Field(default_factory=uuid4, primary_key=True)
 email: str = Field(index=True, unique=True)
 hashed_password: str
 role: str = Field(index=True)
