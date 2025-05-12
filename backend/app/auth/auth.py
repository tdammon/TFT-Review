from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import os
import requests
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response, JSONResponse

from ..db.database import get_db
from ..models.user import User

security = HTTPBearer()

# Auth0 configuration
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE")
ALGORITHMS = ["RS256"]

def get_token_payload(token: str):
    """Verify and decode the JWT token or validate opaque token"""
    try:
        # First, check if this is a JWT (has 3 parts separated by dots)
        token_parts = token.split('.')
        is_jwt = len(token_parts) == 3
        
        if is_jwt:
            print("Processing token as JWT")
            # Get the key ID from the token header
            try:
                unverified_header = jwt.get_unverified_header(token)
                kid = unverified_header.get('kid')
                print(f"Token header: {unverified_header}")
                print(f"Key ID (kid): {kid}")
                
                if not kid:
                    raise ValueError("No 'kid' found in token header")
            except Exception as e:
                print(f"Error parsing token header: {str(e)}")
                raise
            
            # Fetch JWKS
            try:
                jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
                print(f"Fetching JWKS from: {jwks_url}")
                jwks_response = requests.get(jwks_url)
                print(f"JWKS response status: {jwks_response.status_code}")
                
                if jwks_response.status_code != 200:
                    raise ValueError(f"Failed to fetch JWKS: {jwks_response.status_code}")
                    
                jwks = jwks_response.json()
                print(f"JWKS keys count: {len(jwks.get('keys', []))}")
            except Exception as e:
                print(f"Error fetching JWKS: {str(e)}")
                raise
            
            # Find the signing key in the JWKS
            try:
                rsa_key = {}
                for key in jwks.get("keys", []):
                    if key.get("kid") == kid:
                        rsa_key = {
                            "kty": key.get("kty"),
                            "kid": key.get("kid"),
                            "use": key.get("use"),
                            "n": key.get("n"),
                            "e": key.get("e")
                        }
                        break
                
                print(f"Found matching key: {bool(rsa_key)}")
                
                if not rsa_key:
                    raise ValueError(f"No matching key found for kid: {kid}")
            except Exception as e:
                print(f"Error finding signing key: {str(e)}")
                raise
            
            # Verify the token
            try:
                payload = jwt.decode(
                    token,
                    rsa_key,
                    algorithms=ALGORITHMS,
                    audience=AUTH0_AUDIENCE,
                    issuer=f"https://{AUTH0_DOMAIN}/"
                )
                print("Token successfully decoded")
            except Exception as e:
                print(f"Error decoding token: {str(e)}")
                raise
            
            # If the token doesn't contain email, fetch it from Auth0 userinfo endpoint
            if "email" not in payload and "sub" in payload:
                try:
                    # Call userinfo endpoint to get additional user information
                    userinfo_url = f"https://{AUTH0_DOMAIN}/userinfo"
                    userinfo_response = requests.get(
                        userinfo_url,
                        headers={"Authorization": f"Bearer {token}"}
                    )
                    
                    if userinfo_response.status_code == 200:
                        userinfo = userinfo_response.json()
                        # Add email to payload if available
                        if "email" in userinfo:
                            payload["email"] = userinfo["email"]
                        print(f"Enhanced payload with userinfo: {userinfo}")
                except Exception as e:
                    print(f"Error fetching userinfo: {str(e)}")
                    
            return payload
        else:
            print("Processing token as opaque token")
            # For opaque tokens, we need to validate with Auth0's userinfo endpoint
            userinfo_url = f"https://{AUTH0_DOMAIN}/userinfo"
            response = requests.get(
                userinfo_url,
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=401,
                    detail=f"Invalid token: Auth0 userinfo returned {response.status_code}"
                )
                
            # Return the userinfo as payload
            return response.json()
    except Exception as e:
        print(f"Token verification failed: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}"
        )

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip auth for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
            
        # Skip auth for public endpoints
        if request.url.path in ["/docs", "/redoc", "/openapi.json", "/", "/api/v1/health"]:
            return await call_next(request)

        # Just check if token exists and has correct format
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid token format"}
            )
        
        return await call_next(request)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    require_username: bool = True
) -> User:
    """
    Get the current user from the JWT token.
    Creates a new user if they don't exist.
    Args:
        require_username: If True, raises 404 when user has no username.
                        If False, returns user even without username.
    """
    try:
        token = credentials.credentials
        print(f"Token: {token[:10]}... (truncated)")
        
        # Verify and decode the token
        try:
            payload = get_token_payload(token)
            print("Token payload successfully decoded")
        except Exception as token_error:
            print(f"Error decoding token: {str(token_error)}")
            raise
        
        # Get the Auth0 user ID from the token
        try:
            auth0_id = payload["sub"]
            email = payload.get("email")
            print(f"Extracted auth0_id: {auth0_id}")
        except KeyError as key_error:
            print(f"Missing required claim in token: {str(key_error)}")
            print(f"Available claims: {list(payload.keys())}")
            raise
        
        # Print token payload for debugging
        print(f"Token payload: {payload}")
        
        # Try to get existing user first
        try:
            user = db.query(User).filter(User.auth0_id == auth0_id).first()
            if user:
                print(f"Found existing user with auth0_id: {auth0_id}")
            else:
                print(f"No existing user found with auth0_id: {auth0_id}")
        except Exception as db_error:
            print(f"Database error when querying for user: {str(db_error)}")
            raise
        
        if not user:
            try:
                # Try to create new user
                print(f"Creating new user with auth0_id: {auth0_id} and email: {email}")
                
                # Use a placeholder email if none is provided
                if not email:
                    email = f"{auth0_id.replace('|', '-')}@placeholder.com"
                    print(f"Using placeholder email: {email}")
                
                # Generate a temporary username based on auth0_id
                temp_username = f"user_{auth0_id.split('|')[-1]}"
                print(f"Using temporary username: {temp_username}")
                
                user = User(
                    auth0_id=auth0_id,
                    email=email,
                    username=temp_username  # Add temporary username
                )
                db.add(user)
                db.commit()
                print("User successfully added to database and committed")
                db.refresh(user)
                print("User successfully refreshed")
            except IntegrityError as e:
                print(f"IntegrityError when creating user: {str(e)}")
                db.rollback()
                # Try to get the user again
                user = db.query(User).filter(User.auth0_id == auth0_id).first()
                if not user:
                    print("Failed to retrieve user after IntegrityError")
                    raise HTTPException(status_code=500, detail="Failed to create or retrieve user")
                print(f"Retrieved user after IntegrityError: {user.auth0_id}")
            except Exception as create_error:
                print(f"Unexpected error when creating user: {str(create_error)}")
                raise
        
        # Check if username is required
        if require_username and not user.username:
            print(f"Username required but not found for user: {auth0_id}")
            raise HTTPException(status_code=404, detail="User not found")
        
        print(f"Successfully returning user: {auth0_id}")
        return user
        
    except Exception as e:
        print(f"Authentication error: {str(e)}")
        import traceback
        print(f"Authentication error traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}"
        ) 