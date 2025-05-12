from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from typing import List
from jose import jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import time
import datetime

from ..db.database import get_db
from ..models.user import User
from ..schemas.user import UserCreate, UserUpdate, UserResponse
from ..auth import get_current_user, get_token_payload, AUTH0_DOMAIN, AUTH0_AUDIENCE, ALGORITHMS, security

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

# Create a proper async dependency for users without username requirement
async def get_user_for_onboarding(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current user without requiring username (for onboarding)"""
    return await get_current_user(credentials=credentials, db=db, require_username=False)

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    response: Response = None
):
    """Get the current user's profile"""
    print(f"Current user endpoint called at {datetime.datetime.now()}")
    print(f"Current user: {current_user.username}, id: {current_user.id}, email: {current_user.email}")
    
    # Disable caching for this endpoint
    if response:
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        # Add a unique ETag to force browser to not use cache
        response.headers["ETag"] = f"\"{int(time.time())}\""
    
    # Return the user directly - FastAPI will convert to UserResponse
    return current_user

@router.patch("/me", response_model=UserResponse)
async def update_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update the current user's profile"""
    for key, value in user_update.dict(exclude_unset=True).items():
        setattr(current_user, key, value)
    
    db.commit()
    db.refresh(current_user)
    return current_user

@router.get("/{username}", response_model=UserResponse)
async def get_user_profile(
    username: str,
    db: Session = Depends(get_db)
):
    """Get a user's public profile by username"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/complete-onboarding", response_model=UserResponse)
async def complete_onboarding(
    user_update: UserUpdate,
    current_user: User = Depends(get_user_for_onboarding),
    db: Session = Depends(get_db)
):

    # Check if username is required
    if not user_update.username:
        print("Error: Username is missing from request")
        raise HTTPException(status_code=400, detail="Username is required")
    
    # Check if username is already taken by another user
    existing_username = db.query(User).filter(
        User.username == user_update.username,
        User.id != current_user.id  # Exclude the current user
    ).first()
    
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already taken")

    # Allow changing from temporary username (starting with 'user_') to permanent one
    is_temp_username = current_user.username and current_user.username.startswith('user_')
    has_completed_onboarding = current_user.username and not is_temp_username
    
    if has_completed_onboarding:
        raise HTTPException(status_code=400, detail="User has already completed onboarding")

    # Update user profile
    for key, value in user_update.dict(exclude_unset=True).items():
        print(f"Setting {key} = {value}")
        setattr(current_user, key, value)
    
    try:
        db.commit()
        print(f"User update committed successfully")
        db.refresh(current_user)
        print(f"User refreshed: username='{current_user.username}'")
        return current_user
    except Exception as e:
        print(f"Error updating user: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")
