import os
import aiohttp
import asyncio
import time
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

class RiotApiService:
    """Service for Riot API interactions and functionality"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("RIOT_API_KEY")
        if not self.api_key:
            raise ValueError("Riot API key is required")
        self.session = None
        
    async def get_session(self):
        """Get or create an aiohttp client session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session        

    async def _request(self, method: str, url: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make a request to the Riot API"""
        headers = {"X-Riot-Token": self.api_key}

        try:
            session = await self.get_session()
            
            async with session.request(
                method=method,
                url=url,
                headers=headers,
                params=params
            ) as response:        
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Riot API error: {response.status} - {error_text}")
                
                return await response.json()
        except Exception as e:
            # Re-raise the exception but ensure we don't lose the original error
            raise Exception(f"Request failed: {str(e)}") from e
        
    async def get(self, url: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make a GET request to the Riot API"""
        return await self._request("GET", url, params)
        
    async def get_summoner_by_name(self, summoner_name: str, region: str = "na1") -> Dict[str, Any]:
        """Get summoner info by summoner name"""
        url = f"https://{region}.api.riotgames.com/tft/summoner/v1/summoners/by-name/{summoner_name}"
        return await self.get(url)
    
    async def get_summoner_by_puuid(self, puuid: str, region: str = "na1") -> Dict[str, Any]:
        """Get summoner info by puuid"""
        url = f"https://{region}.api.riotgames.com/tft/summoner/v1/summoners/by-puuid/{puuid}"
        return await self.get(url)
    
    async def get_match_history(self, puuid: str, count: int = 20, region: str = "americas") -> List[str]:
        """Get match history for a player"""
        url = f"https://{region}.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids"
        return await self.get(url, params={"count": count})
    
    async def get_match_details(self, match_id: str, region: str = "americas") -> Dict[str, Any]:
        """Get details for a specific match"""
        url = f"https://{region}.api.riotgames.com/tft/match/v1/matches/{match_id}"
        return await self.get(url)
        
    # League/Ranked Methods
    async def get_league_entries(self, puuid: str, region: str = "americas") -> List[Dict[str, Any]]:
        """Get ranked/league entries for a summoner"""
        url = f"https://{region}.api.riotgames.com/tft/league/v1/by-puuid/{puuid}"
        return await self.get(url)
    
    async def get_player_rank(self, puuid: str, region: str = "americas") -> Dict[str, Any]:
        """
        Get a player's TFT rank information in a formatted way
        
        Returns:
            Dictionary with rank information including:
            - tier: The tier (IRON, BRONZE, SILVER, etc.)
            - rank: The rank within the tier (I, II, III, IV)
            - lp: League points
            - formatted_rank: A formatted string (e.g., "GOLD II 75 LP")
            - wins: Number of wins
            - losses: Number of losses
            - win_rate: Win rate percentage
            - is_ranked: Whether the player has a ranked entry
        """
        try:
            
            if not puuid:
                return {
                    "tier": None,
                    "rank": None,
                    "lp": 0,
                    "formatted_rank": "Unranked",
                    "wins": 0,
                    "losses": 0,
                    "win_rate": 0,
                    "is_ranked": False
                }
            
            # Now we can fetch the league entries using the summoner ID
            entries = await self.get_league_entries(puuid, region)
            
            # Find the standard ranked entry
            ranked_entry = None
            for entry in entries:
                if entry.get('queueType') == 'RANKED_TFT':
                    ranked_entry = entry
                    break
            
            # If no ranked entry found, return default values
            if not ranked_entry:
                return {
                    "tier": None,
                    "rank": None,
                    "lp": 0,
                    "formatted_rank": "Unranked",
                    "wins": 0,
                    "losses": 0,
                    "win_rate": 0,
                    "is_ranked": False
                }
            
            # Extract rank information
            tier = ranked_entry.get('tier', '')
            rank = ranked_entry.get('rank', '')
            lp = ranked_entry.get('leaguePoints', 0)
            wins = ranked_entry.get('wins', 0)
            losses = ranked_entry.get('losses', 0)
            
            # Calculate win rate
            total_games = wins + losses
            win_rate = (wins / total_games * 100) if total_games > 0 else 0
            
            # Format the rank string
            formatted_rank = f"{tier} {rank} {lp} LP" if tier and rank else "Unranked"
            
            return {
                "tier": tier,
                "rank": rank,
                "lp": lp,
                "formatted_rank": formatted_rank,
                "wins": wins,
                "losses": losses,
                "win_rate": round(win_rate, 1),
                "is_ranked": True
            }
        except Exception as e:
            # Log error but return a default response to prevent hanging
            print(f"Error fetching player rank: {str(e)}")
            return {
                "tier": None,
                "rank": None,
                "lp": 0,
                "formatted_rank": "Error fetching rank",
                "wins": 0,
                "losses": 0, 
                "win_rate": 0,
                "is_ranked": False,
                "error": str(e)
            }
    
    @staticmethod
    def estimate_lp_change(placement: int) -> int:
        """Estimate LP change based on placement and tier"""
        if placement == 1:
            return 40 
        elif placement == 2:
            return 30 
        elif placement == 3:
            return 20 
        elif placement == 4:
            return 10 
        elif placement == 5:
            return -10
        elif placement == 6:
            return -20
        elif placement == 7:
            return -30
        else:  # placement == 8
            return -40            
        
    async def get_rating_history(self, puuid: str, count: int = 20, region_routing: str = "americas") -> Dict[str, Any]:
        """
        Calculate rating history based on match history
        
        Args:
            puuid: Player UUID
            count: Number of matches to analyze
            region_routing: Routing region for API calls (e.g., americas, europe)
            
        Returns:
            Dictionary with rating history and summary statistics
        """
        try:
            # Get match history
            match_ids = await self.get_match_history(puuid, count, region_routing)
            # Process each match
            player_data = []
            for match_id in match_ids:
                try:
                    match = await self.get_match_details(match_id, region_routing)
                    
                    # Find the player in the match
                    for participant in match.get('info', {}).get('participants', []):
                        if participant.get('puuid') == puuid:
                            placement = participant.get('placement')
                            timestamp = match.get('info', {}).get('game_datetime', 0) / 1000
                            lp_change = self.estimate_lp_change(placement)
                            
                            player_data.append({
                                'match_id': match_id,
                                'timestamp': timestamp,
                                'date': datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'),
                                'placement': placement,
                                'estimated_lp_change': lp_change
                            })
                            break
                    
                    # Respect rate limits with async sleep
                    await asyncio.sleep(1.2)
                    
                except Exception as e:
                    # Log error but continue processing other matches
                    print(f"Error processing match {match_id}: {str(e)}")
            
            # Sort by timestamp
            player_data.sort(key=lambda x: x['timestamp'])
            
            # Calculate cumulative LP
            base_lp = 50  # Assume starting at 50 LP
            for game in player_data:
                game['lp_after_game'] = base_lp + game['estimated_lp_change']
                base_lp = game['lp_after_game']
                
                # Handle promotions/demotions roughly
                if base_lp > 100:
                    game['promotion'] = True
                    base_lp = 0
                elif base_lp < 0:
                    game['demotion'] = True
                    base_lp = 75
                else:
                    game['promotion'] = False
                    game['demotion'] = False
            
            return {
                "rating_history": player_data,
                "matches_analyzed": len(player_data),
                "summary": {
                    "average_placement": sum(game['placement'] for game in player_data) / len(player_data) if player_data else 0,
                    "total_estimated_lp_change": sum(game['estimated_lp_change'] for game in player_data),
                    "first_places": sum(1 for game in player_data if game['placement'] == 1),
                    "top4_rate": sum(1 for game in player_data if game['placement'] <= 4) / len(player_data) if player_data else 0
                }
            }
        except Exception as e:
            # Log error but return a minimal response to prevent hanging
            print(f"Error in get_rating_history: {str(e)}")
            return {
                "rating_history": [],
                "matches_analyzed": 0,
                "summary": {
                    "average_placement": 0,
                    "total_estimated_lp_change": 0,
                    "first_places": 0,
                    "top4_rate": 0
                },
                "error": str(e)
            }

    async def close(self):
        """Close the session when done"""
        if self.session and not self.session.closed:
            try:
                await self.session.close()
            except Exception as e:
                print(f"Error closing session: {str(e)}")
                # Don't re-raise - we're in cleanup code        