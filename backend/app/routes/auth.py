from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
import os
import requests
import uuid
import secrets
from fastapi.responses import RedirectResponse
from typing import Optional

from ..db.database import get_db
from ..models.user import User
from ..auth import get_current_user

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

# Riot API configuration (replace with your actual values in .env)
RIOT_CLIENT_ID = os.getenv("RIOT_CLIENT_ID", "your-riot-client-id")
RIOT_CLIENT_SECRET = os.getenv("RIOT_CLIENT_SECRET", "your-riot-client-secret")
REDIRECT_URI = os.getenv("RIOT_REDIRECT_URI", "http://localhost:3000/auth/riot/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Store state parameters to prevent CSRF attacks
state_store = {}

@router.get("/riot/connect")
async def riot_connect(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initiate the Riot Games account connection process
    
    This endpoint generates the authorization URL for Riot Games authentication
    but unlike the login endpoint, it returns the URL for the frontend to redirect.
    """
    # Generate a random state parameter to prevent CSRF attacks
    state = secrets.token_urlsafe(32)
    
    # Store the state parameter and user ID
    state_store[state] = {
        "user_id": current_user.id,
        "redirect_after": "/onboarding"
    }
    
    # Construct the Riot authorization URL
    auth_url = (
        f"https://auth.riotgames.com/authorize"
        f"?client_id={RIOT_CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=openid+offline_access+riot_identity"
        f"&state={state}"
    )
    
    # Return the URL for the frontend to handle the redirect
    return {"auth_url": auth_url}

@router.get("/riot/login")
async def riot_login(
    request: Request,
    response: Response,
    redirect_after: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initiate the Riot Games login flow
    
    This endpoint redirects the user to the Riot Games authentication page.
    After successful authentication, Riot will redirect back to our callback endpoint.
    """
    # Generate a random state parameter to prevent CSRF attacks
    state = secrets.token_urlsafe(32)
    
    # Store the state parameter and user ID
    state_store[state] = {
        "user_id": current_user.id,
        "redirect_after": redirect_after or "/profile"
    }
    
    # Construct the Riot authorization URL
    auth_url = (
        f"https://auth.riotgames.com/authorize"
        f"?client_id={RIOT_CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=openid+offline_access+riot_identity"
        f"&state={state}"
    )
    
    # Redirect to Riot's authorization page
    return RedirectResponse(url=auth_url)

@router.get("/riot/callback")
async def riot_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Handle the callback from Riot Games after authentication
    
    This endpoint exchanges the authorization code for an access token,
    retrieves the user's Riot account information, and updates the database.
    """
    # Check for errors
    if error:
        return RedirectResponse(url=f"{FRONTEND_URL}/onboarding?error=riot_auth_failed&reason={error}")
    
    # Validate state parameter
    if not state or state not in state_store:
        return RedirectResponse(url=f"{FRONTEND_URL}/onboarding?error=invalid_state")
    
    # Get stored information
    stored_data = state_store.pop(state)
    user_id = stored_data["user_id"]
    redirect_after = stored_data["redirect_after"]
    
    # Validate code
    if not code:
        return RedirectResponse(url=f"{FRONTEND_URL}/{redirect_after}?error=missing_code")
    
    # Exchange authorization code for tokens
    try:
        token_response = requests.post(
            "https://auth.riotgames.com/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "client_id": RIOT_CLIENT_ID,
                "client_secret": RIOT_CLIENT_SECRET
            }
        )
        
        token_data = token_response.json()
        
        if token_response.status_code != 200:
            error_detail = token_data.get("error_description", "Unknown error")
            return RedirectResponse(url=f"{FRONTEND_URL}/{redirect_after}?error=token_exchange_failed&reason={error_detail}")
            
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        id_token = token_data.get("id_token")
        
        # Get user information from Riot
        user_info_response = requests.get(
            "https://auth.riotgames.com/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if user_info_response.status_code != 200:
            return RedirectResponse(url=f"{FRONTEND_URL}/{redirect_after}?error=user_info_failed")
            
        riot_user_info = user_info_response.json()
        
        # Get the user from the database
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return RedirectResponse(url=f"{FRONTEND_URL}/{redirect_after}?error=user_not_found")
        
        # Update user with Riot account information
        user.riot_id = riot_user_info.get("sub")
        user.riot_puuid = riot_user_info.get("puuid")
        user.riot_account_name = riot_user_info.get("riot_account", {}).get("game_name")
        user.riot_account_tag = riot_user_info.get("riot_account", {}).get("tag_line")
        user.riot_region = riot_user_info.get("riot_region", {}).get("tag")
        user.riot_access_token = access_token
        user.riot_refresh_token = refresh_token
        user.verified_riot_account = True
        
        # Update the database
        db.commit()
        
        # Redirect back to the frontend with success message
        return RedirectResponse(url=f"{FRONTEND_URL}/{redirect_after}?success=riot_connected")
        
    except Exception as e:
        # Handle any exceptions
        return RedirectResponse(url=f"{FRONTEND_URL}/{redirect_after}?error=server_error&reason={str(e)}")

@router.post("/riot/disconnect")
async def disconnect_riot_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove the Riot account association from the user's profile"""
    current_user.riot_id = None
    current_user.riot_puuid = None
    current_user.riot_account_name = None
    current_user.riot_account_tag = None
    current_user.riot_region = None
    current_user.riot_access_token = None
    current_user.riot_refresh_token = None
    current_user.verified_riot_account = False
    
    db.commit()
    
    return {"message": "Riot account disconnected successfully"} 