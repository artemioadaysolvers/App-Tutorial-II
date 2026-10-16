from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GoogleLogin(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idToken: str = Field(min_length=20, max_length=8192)


class User(BaseModel):
    id: str
    email: str
    name: str


class Session(BaseModel):
    accessToken: str
    tokenType: str = "bearer"
    expiresAt: datetime
    user: User


class MessageInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    requestId: UUID
    mensaje1: str = Field(min_length=1, max_length=2000)
    mensaje2: str = Field(min_length=1, max_length=2000)
    mensaje3: str = Field(min_length=1, max_length=2000)


class MessageDocument(BaseModel):
    id: str
    userId: str
    mensaje1: str
    mensaje2: str
    mensaje3: str
    createdAt: datetime
