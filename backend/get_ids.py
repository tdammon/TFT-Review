import os
import requests
import argparse
from dotenv import load_dotenv

# Load environment variables (if you have a .env file)
try:
    load_dotenv()
except:
    pass

def get_account_by_riot_id(game_name, tag_line, api_key, region="americas"):
    """Get account info by Riot ID (game name and tagline)"""
    url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    headers = {"X-Riot-Token": api_key}
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return None
        
    return response.json()

def get_summoner_by_puuid(puuid, api_key, region="na1"):
    """Get summoner info by PUUID"""
    url = f"https://{region}.api.riotgames.com/tft/summoner/v1/summoners/by-puuid/{puuid}"
    headers = {"X-Riot-Token": api_key}
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return None
        
    return response.json()

def main():
    parser = argparse.ArgumentParser(description="Get account and summoner IDs by Riot ID")
    parser.add_argument("game_name", help="Your Riot game name (without the tag)")
    parser.add_argument("tag_line", help="Your Riot tag line (the part after the #)")
    parser.add_argument("api_key", help="Your Riot API key")
    parser.add_argument("--region", default="na1", help="Your game region (default: na1)")
    parser.add_argument("--routing", default="americas", help="Routing region (default: americas)")
    
    args = parser.parse_args()
    
    # Get account info
    print(f"Looking up Riot ID: {args.game_name}#{args.tag_line}...")
    account = get_account_by_riot_id(args.game_name, args.tag_line, args.api_key, args.routing)
    
    if not account:
        print("Account not found")
        return
        
    print("\n=== Riot Account Info ===")
    print(f"PUUID: {account.get('puuid')}")
    print(f"Game Name: {account.get('gameName')}")
    print(f"Tag Line: {account.get('tagLine')}")
    
    # Get summoner info
    print("\nFetching summoner details...")
    summoner = get_summoner_by_puuid(account.get('puuid'), args.api_key, args.region)
    
    if not summoner:
        print("Summoner not found")
        return
        
    print("\n=== Summoner Info ===")
    print(f"Summoner ID: {summoner.get('id')}")
    print(f"Account ID: {summoner.get('accountId')}")
    print(f"Name: {summoner.get('name')}")
    print(f"Level: {summoner.get('summonerLevel')}")
    print(f"Profile Icon ID: {summoner.get('profileIconId')}")
    
    print("\nThese IDs can be used for testing Riot API endpoints.")
    print("\nUsage examples for TFT:")
    print(f"1. Get TFT ranked stats: https://{args.region}.api.riotgames.com/tft/league/v1/entries/by-summoner/{summoner.get('id')}?api_key={args.api_key}")
    print(f"2. Get TFT match history: https://{args.routing}.api.riotgames.com/tft/match/v1/matches/by-puuid/{account.get('puuid')}/ids?api_key={args.api_key}")

if __name__ == "__main__":
    main()