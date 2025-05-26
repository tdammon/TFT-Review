from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
import os
import traceback
import time

from ..db.database import get_db
from ..models.user import User
from ..auth import get_current_user
from ..services.riot_api import RiotApiService

router = APIRouter(
    prefix="/tft",
    tags=["tft"]
)

def get_region_routing(user_region: str) -> tuple[str, str]:
    """
    Get the appropriate region routing and game region based on user's selected region
    
    Args:
        user_region: The region selected by user during onboarding (americas, europe, asia)
        
    Returns:
        tuple: (region_routing, region_game) for API calls
    """
    if user_region == "americas":
        return "americas", "na1"
    elif user_region == "europe":
        return "europe", "euw1"
    elif user_region == "asia":
        return "asia", "kr"
    else:
        # Default fallback
        return "americas", "na1"

@router.get("/rating-history")
async def get_rating_history(
    match_count: int = 20,
    initial_count: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get TFT rating history for the current user"""
    route_start_time = time.time()
    print(f"[ROUTE PERF] Starting rating-history endpoint for user {current_user.username}, match count: {match_count}")

    if not current_user.verified_riot_account or not current_user.riot_puuid:
        raise HTTPException(
            status_code=400,
            detail="User does not have a connected Riot account"
        )
    
    if not current_user.riot_region:
        raise HTTPException(
            status_code=400,
            detail="User region not set. Please complete onboarding."
        )
    
    riot_service = None
    try:
        # Initialize service
        init_start = time.time()
        print(f"[ROUTE PERF] Getting API key and initializing service")
        api_key = os.getenv("RIOT_API_KEY")
        if not api_key:
            raise ValueError("RIOT_API_KEY environment variable is not set")
            
        riot_service = RiotApiService(api_key)
        region_routing, region_game = get_region_routing(current_user.riot_region)
        
        print(f"[ROUTE PERF] Using region routing: {region_routing}, game region: {region_game}")
        init_end = time.time()
        print(f"[ROUTE PERF] Service initialization completed in {init_end - init_start:.2f}s")

        # Call service method
        service_call_start = time.time()
        print(f"[ROUTE PERF] Calling service.get_rating_history with puuid={current_user.riot_puuid[:8]}..., count={match_count}")
        history = await riot_service.get_rating_history(
            puuid=current_user.riot_puuid,
            count=match_count,
            initial_count=initial_count,
            region_routing=region_routing
        )   
        service_call_end = time.time()
        print(f"[ROUTE PERF] Service call completed in {service_call_end - service_call_start:.2f}s")
        
        # Finalize response
        response_time = time.time()
        print(f"[ROUTE PERF] Endpoint completed in {response_time - route_start_time:.2f}s")
        return history
    except Exception as e:
        error_time = time.time()
        error_detail = f"Error fetching rating history: {str(e)}"
        print(f"[ROUTE PERF] Error occurred after {error_time - route_start_time:.2f}s")
        print(error_detail)
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )
    finally:
        cleanup_start = time.time()
        if riot_service:
            try:
                await riot_service.close()
                cleanup_end = time.time()
                print(f"[ROUTE PERF] Service cleanup completed in {cleanup_end - cleanup_start:.2f}s")
            except Exception as e:
                print(f"Error closing riot_service: {str(e)}")
                print(f"[ROUTE PERF] Service cleanup failed after {time.time() - cleanup_start:.2f}s")
    
@router.get("/summoner-info")
async def get_summoner_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get TFT summoner info for the current user"""

    if not current_user.verified_riot_account or not current_user.riot_puuid:
        raise HTTPException(
            status_code=400,
            detail="User does not have a connected Riot account"
        )

    if not current_user.riot_region:
        raise HTTPException(
            status_code=400,
            detail="User region not set. Please complete onboarding."
        )

    riot_service = None
    try:
        api_key = os.getenv("RIOT_API_KEY")
        if not api_key:
            raise ValueError("RIOT_API_KEY environment variable is not set")
            
        riot_service = RiotApiService(api_key)
        region_routing, region_game = get_region_routing(current_user.riot_region)

        summonerInfo = await riot_service.get_summoner_by_puuid(
            puuid=current_user.riot_puuid, 
            region=region_game
        )                
        return summonerInfo
    except Exception as e:
        error_detail = f"Error fetching summoner info: {str(e)}"
        print(error_detail)
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )
    finally:
        if riot_service:
            try:
                await riot_service.close()
            except Exception as e:
                print(f"Error closing riot_service: {str(e)}")
    
@router.get("/rank")
async def get_player_rank(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current user's TFT rank information"""

    if not current_user.verified_riot_account or not current_user.riot_puuid:
        raise HTTPException(
            status_code=400,
            detail="User does not have a connected Riot account"
        )

    if not current_user.riot_region:
        raise HTTPException(
            status_code=400,
            detail="User region not set. Please complete onboarding."
        )

    riot_service = None
    try:
        api_key = os.getenv("RIOT_API_KEY")
        if not api_key:
            raise ValueError("RIOT_API_KEY environment variable is not set")
            
        riot_service = RiotApiService(api_key)
        region_routing, region_game = get_region_routing(current_user.riot_region)
            
        rank_info = await riot_service.get_player_rank(
            puuid=current_user.riot_puuid,
            region=region_routing  # Use region_routing for league endpoints
        )
                
        return rank_info
    except Exception as e:
        error_detail = f"Error fetching rank information: {str(e)}"
        print(error_detail)
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )
    finally:
        if riot_service:
            try:
                await riot_service.close()
            except Exception as e:
                print(f"Error closing riot_service: {str(e)}")
    
@router.get("/test-api-key", dependencies=[])
async def test_api_key():
    """Test if the Riot API key is set and valid"""
    try:
        api_key = os.getenv("RIOT_API_KEY")
        if not api_key:
            return {"status": "error", "message": "RIOT_API_KEY environment variable is not set"}
            
        return {"status": "success", "message": "API key is set", "key_preview": f"{api_key[:5]}...{api_key[-5:]}"}
    except Exception as e:
        return {"status": "error", "message": f"Error testing API key: {str(e)}"}
    
    