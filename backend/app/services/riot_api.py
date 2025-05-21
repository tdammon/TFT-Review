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
        
        start_time = time.time()
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
                
                data = await response.json()
                end_time = time.time()
                print(f"API Request completed: {url} - {end_time - start_time:.2f}s")
                return data
        except Exception as e:
            end_time = time.time()
            print(f"API Request failed: {url} - {end_time - start_time:.2f}s - Error: {str(e)}")
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
    
    async def get_match_history(self, puuid: str, count: int = 20, start: int = 0, region: str = "americas") -> List[str]:
        """Get match history for a player"""
        start_time = time.time()
        print(f"[PERF] get_match_history: Starting request for {count} matches, puuid={puuid[:8]}...")
        url = f"https://{region}.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids"
        try:
            result = await self.get(url, params={"count": count, "start": start})
            end_time = time.time()
            print(f"[PERF] get_match_history: Completed in {end_time - start_time:.2f}s, retrieved {len(result)} matches")
            return result
        except Exception as e:
            end_time = time.time()
            print(f"[PERF] get_match_history: Failed after {end_time - start_time:.2f}s - {str(e)}")
            raise
    
    async def get_match_details(self, match_id: str, region: str = "americas") -> Dict[str, Any]:
        """Get details for a specific match"""
        start_time = time.time()
        print(f"[PERF] get_match_details: Starting request for match {match_id}")
        url = f"https://{region}.api.riotgames.com/tft/match/v1/matches/{match_id}"
        try:
            result = await self.get(url)
            end_time = time.time()
            print(f"[PERF] get_match_details: Completed in {end_time - start_time:.2f}s")
            return result
        except Exception as e:
            end_time = time.time()
            print(f"[PERF] get_match_details: Failed after {end_time - start_time:.2f}s - {str(e)}")
            raise
        
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
        
    async def get_rating_history(self, puuid: str, count: int = 20, initial_count: int = 0, region_routing: str = "americas") -> Dict[str, Any]:
        """
        Calculate rating history based on match history
        
        Args:
            puuid: Player UUID
            count: Number of matches to analyze
            region_routing: Routing region for API calls (e.g., americas, europe)
            
        Returns:
            Dictionary with rating history and summary statistics
        """
        total_start_time = time.time()
        print(f"[PERF] Starting get_rating_history for {count} matches")
        
        try:
            # Get match history
            match_history_start = time.time()
            print(f"[PERF] Fetching match history...")
            match_ids = await self.get_match_history(puuid, count, initial_count, region_routing)
            match_history_end = time.time()
            print(f"[PERF] Match history fetched: {len(match_ids)} matches - {match_history_end - match_history_start:.2f}s")
            
            # Process matches in parallel with controlled concurrency
            player_data = []
            match_details_start = time.time()
            print(f"[PERF] Starting parallel match details fetching")
            
            # Function to process a single match
            async def process_match(match_id, index):
                match_start = time.time()
                print(f"[PERF] Processing match {index+1}/{len(match_ids)}: {match_id}")
                try:
                    match = await self.get_match_details(match_id, region_routing)
                    
                    # Find the player in the match
                    for participant in match.get('info', {}).get('participants', []):
                        if participant.get('puuid') == puuid:
                            placement = participant.get('placement')
                            timestamp = match.get('info', {}).get('game_datetime', 0) / 1000
                            lp_change = self.estimate_lp_change(placement)
                            
                            match_data = {
                                'match_id': match_id,
                                'timestamp': timestamp,
                                'date': datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'),
                                'placement': placement,
                                'estimated_lp_change': lp_change
                            }
                            
                            match_end = time.time()
                            print(f"[PERF] Match {index+1} processed in {match_end - match_start:.2f}s")
                            return match_data
                except Exception as e:
                    match_end = time.time()
                    print(f"[PERF] Error processing match {match_id}: {str(e)} - took {match_end - match_start:.2f}s")
                    return None
            
            # Use a semaphore to limit concurrency to 3 concurrent requests
            # This balances speed with respect for rate limits
            semaphore = asyncio.Semaphore(3)
            
            async def process_with_semaphore(match_id, index):
                async with semaphore:
                    # Add a small delay between requests to avoid rate limit issues
                    if index > 0:
                        delay = 0.25  # 250ms between requests
                        await asyncio.sleep(delay)
                    return await process_match(match_id, index)
            
            # Create tasks for all matches
            tasks = [process_with_semaphore(match_id, i) for i, match_id in enumerate(match_ids)]
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks)
            
            # Filter out any None results (failed matches)
            player_data = [result for result in results if result is not None]
            
            match_details_end = time.time()
            match_details_total_time = match_details_end - match_details_start
            print(f"[PERF] All matches processed in parallel. Total processing time: {match_details_total_time:.2f}s")
            
            # Sort by timestamp
            sorting_start = time.time()
            player_data.sort(key=lambda x: x['timestamp'])
            sorting_end = time.time()
            print(f"[PERF] Sorting completed in {sorting_end - sorting_start:.2f}s")
            
            # Calculate cumulative LP
            calculation_start = time.time()
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
            
            # Calculate summary stats
            summary = {
                "average_placement": sum(game['placement'] for game in player_data) / len(player_data) if player_data else 0,
                "total_estimated_lp_change": sum(game['estimated_lp_change'] for game in player_data),
                "first_places": sum(1 for game in player_data if game['placement'] == 1),
                "top4_rate": sum(1 for game in player_data if game['placement'] <= 4) / len(player_data) if player_data else 0
            }
            calculation_end = time.time()
            print(f"[PERF] Calculations completed in {calculation_end - calculation_start:.2f}s")
            
            total_end_time = time.time()
            total_time = total_end_time - total_start_time
            print(f"[PERF] get_rating_history completed in {total_time:.2f}s")
            
            return {
                "rating_history": player_data,
                "matches_analyzed": len(player_data),
                "summary": summary,
                "performance_metrics": {
                    "total_time_seconds": total_time,
                    "match_history_fetch_time": match_history_end - match_history_start,
                    "match_details_fetch_time": match_details_total_time,
                    "sorting_time": sorting_end - sorting_start,
                    "calculation_time": calculation_end - calculation_start
                }
            }
        except Exception as e:
            # Log error but return a minimal response to prevent hanging
            total_end_time = time.time()
            print(f"[PERF] Error in get_rating_history: {str(e)} - Total time: {total_end_time - total_start_time:.2f}s")
            return {
                "rating_history": [],
                "matches_analyzed": 0,
                "summary": {
                    "average_placement": 0,
                    "total_estimated_lp_change": 0,
                    "first_places": 0,
                    "top4_rate": 0
                },
                "error": str(e),
                "performance_metrics": {
                    "total_time_seconds": total_end_time - total_start_time,
                    "error": True
                }
            }

    async def close(self):
        """Close the session when done"""
        if self.session and not self.session.closed:
            try:
                await self.session.close()
            except Exception as e:
                print(f"Error closing session: {str(e)}")
                # Don't re-raise - we're in cleanup code        