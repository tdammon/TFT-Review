from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
import uuid

class UserBase(BaseModel):
    """Base user attributes shared across schemas"""
    email: EmailStr
    auth0_id: str = Field(..., max_length=100)

class UserCreate(UserBase):
    """Schema for creating a new user from Auth0 login"""
    pass  # Just email and auth0_id from Auth0

class UserUpdate(BaseModel):
    """Schema for updating user information"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    profile_picture: Optional[str] = None
    riot_id: Optional[str] = Field(None, max_length=100)
    riot_puuid: Optional[str] = Field(None, max_length=100)
    discord_id: Optional[str] = Field(None, max_length=100)
    discord_username: Optional[str] = Field(None, max_length=100)

class UserInDB(UserBase):
    """Schema for user as stored in database"""
    id: uuid.UUID
    username: Optional[str] = None
    profile_picture: Optional[str] = None
    riot_id: Optional[str] = None
    riot_puuid: Optional[str] = None
    verified_riot_account: bool = False
    discord_id: Optional[str] = None
    discord_username: Optional[str] = None
    discord_connected: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    """Schema for user responses"""
    id: uuid.UUID
    username: Optional[str] = None
    email: str
    profile_picture: Optional[str] = None
    verified_riot_account: bool = False
    discord_connected: bool = False
    riot_puuid: Optional[str] = None
    class Config:
        from_attributes = True 