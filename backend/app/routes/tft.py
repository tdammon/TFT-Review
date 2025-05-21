from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
import os
import traceback

from ..db.database import get_db
from ..models.user import User
from ..auth import get_current_user
from ..services.riot_api import RiotApiService

router = APIRouter(
    prefix="/tft",
    tags=["tft"]
)

@router.get("/rating-history")
async def get_rating_history(
    match_count: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get TFT rating history for the current user"""

    if not current_user.verified_riot_account or not current_user.riot_puuid:
        raise HTTPException(
            status_code=400,
            detail="User does not have a connected Riot account"
        )
    
    riot_service = None
    try:
        api_key = os.getenv("RIOT_API_KEY")
        if not api_key:
            raise ValueError("RIOT_API_KEY environment variable is not set")
            
        riot_service = RiotApiService(api_key)
        region_game = current_user.riot_region or "na1"
        region_routing = "americas"

        if region_game.startswith("eu"):
            region_routing = "europe"
        elif region_game.startswith("kr") or region_game.startswith("jp"):
            region_routing = "asia"

        history = await riot_service.get_rating_history(
            puuid=current_user.riot_puuid,
            count=match_count,
            region_routing=region_routing
        )    
        return history
    except Exception as e:
        error_detail = f"Error fetching rating history: {str(e)}"
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

    riot_service = None
    try:
        api_key = os.getenv("RIOT_API_KEY")
        if not api_key:
            raise ValueError("RIOT_API_KEY environment variable is not set")
            
        riot_service = RiotApiService(api_key)
        region_game = current_user.riot_region or "na1"
        region_routing = "americas"

        if region_game.startswith("eu"):
            region_routing = "europe"
        elif region_game.startswith("kr") or region_game.startswith("jp"):
            region_routing = "asia"

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

    riot_service = None
    try:
        api_key = os.getenv("RIOT_API_KEY")
        if not api_key:
            raise ValueError("RIOT_API_KEY environment variable is not set")
            
        riot_service = RiotApiService(api_key)
        region_game = current_user.riot_region or "na1"
            
        rank_info = await riot_service.get_player_rank(
            puuid=current_user.riot_puuid,
            region=region_game
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
    
    
    