import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import urllib.parse
import re

# Setup logging for web fetcher
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def calculate_tier(top_percent: float) -> str:
    """
    Calculates the Tier based on top_percent.
    Legend: <= 0.01%
    Mythic: <= 0.05%
    Celestial: <= 0.1%
    Grandmaster: <= 1%
    Master: <= 5%
    Diamond: <= 10%
    Platinum: <= 20%
    Gold: <= 35%
    Silver: <= 60%
    Bronze: > 60%
    """
    if top_percent is None:
        return '-'
        
    if top_percent <= 0.01: return "Legend"
    if top_percent <= 0.05: return "Mythic"
    if top_percent <= 0.1: return "Celestial"
    if top_percent <= 1.0: return "Grandmaster"
    if top_percent <= 5.0: return "Master"
    if top_percent <= 10.0: return "Diamond"
    if top_percent <= 20.0: return "Platinum"
    if top_percent <= 35.0: return "Gold"
    if top_percent <= 60.0: return "Silver"
    return "Bronze"

def fetch_scenario_data(scenario_name: str, local_best_score: float = None) -> dict:
    """
    Fetches scenario info from kovaaks.com using their internal backend API.
    Returns '-' or None for unobtainable items.
    """
    encoded_name = urllib.parse.quote_plus(scenario_name)
    # Search for the scenario using the webapp backend API
    target_url = f"https://kovaaks.com/webapp-backend/scenario/popular?page=0&max=20&scenarioNameSearch={encoded_name}"
    
    logging.info(f"========== Web Fetcher ==========")
    logging.info(f"Target Scenario: {scenario_name}")
    logging.info(f"Fetching API URL: {target_url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/114.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    
    # Initialize defaults
    result = {
        'web_total_plays': None,
        'web_total_entries': None,
        'web_rank': None,
        'top_percent': None,
        'tier_rank': '-',
        'web_last_updated': datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    }
    
    try:
        response = requests.get(target_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        scenarios = data.get('data', [])
        
        # Look for an exact match (case-insensitive) to be safe
        target_lower = scenario_name.lower().strip()
        matched_scenario = None
        
        for sc in scenarios:
            api_scenario_name = sc.get('scenarioName', '')
            if api_scenario_name.lower().strip() == target_lower:
                matched_scenario = sc
                break
                
        # Fallback to the first result if it loosely matches or is the only one
        if not matched_scenario and len(scenarios) > 0:
            matched_scenario = scenarios[0]
            logging.info(f"Exact match not found. Using best match: '{matched_scenario.get('scenarioName')}'")
            
        if matched_scenario:
            api_name = matched_scenario.get('scenarioName')
            counts = matched_scenario.get('counts', {})
            total_entries = counts.get('entries')
            total_plays = counts.get('plays')
            
            logging.info(f"API Matched Scenario: '{api_name}'")
            logging.info(f"Extracted API Data - Entries: {total_entries}, Plays: {total_plays}")
            
            result['web_total_entries'] = total_entries
            result['web_total_plays'] = total_plays
            
            # Use binary search to find rank if local_best_score is provided
            if local_best_score is not None and local_best_score > 0 and total_entries and total_entries > 0:
                leaderboard_id = matched_scenario.get('leaderboardId')
                if leaderboard_id:
                    logging.info(f"Leaderboard ID found: {leaderboard_id}. Attempting to fetch Rank via binary search for score: {local_best_score}")
                    found_rank = _binary_search_rank(leaderboard_id, local_best_score, total_entries)
                    result['web_rank'] = found_rank
                else:
                    logging.warning("No leaderboardId returned by API.")
            else:
                logging.info(f"Skipping Rank fetch. (best_score={local_best_score}, total_entries={total_entries})")
            
        else:
            logging.warning(f"Scenario '{scenario_name}' not found in API response.")
            
        # Logging final extraction results
        logging.info(f"Final Validated - Total Entries: {result['web_total_entries']}, Rank: {result['web_rank']}")
        
        # Note: If we don't have rank, we can't calculate Top % or Tier
        if result['web_total_entries'] is not None and result['web_rank'] is not None:
            if result['web_total_entries'] > 0:
                top_percent = (result['web_rank'] / result['web_total_entries']) * 100
                result['top_percent'] = round(top_percent, 3)
                result['tier_rank'] = calculate_tier(top_percent)
                
                logging.info(f"Calculated Top %: {result['top_percent']}%")
                logging.info(f"Calculated Tier: {result['tier_rank']}")
            else:
                logging.warning("Total entries is 0, cannot calculate top_percent.")
        else:
            logging.info("Could not calculate Top % and Tier due to missing Rank.")
            
    except requests.RequestException as e:
        logging.warning(f"Network error fetching from API for {scenario_name}: {e}")
    except ValueError as e:
        logging.error(f"Failed to parse JSON for {scenario_name}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error processing API data for {scenario_name}: {e}")
        
    logging.info(f"Returning web_data: {result}")
    logging.info(f"=================================")
    return result

def _binary_search_rank(leaderboard_id: int, target_score: float, total_entries: int) -> int:
    """
    Binary searches the kovaaks leaderboard paginated API to find the rank for a local score.
    Because KovaaK's leaderboard is sorted descending by score:
    - Page 0 has the highest scores (Rank 1...)
    - Page N has the lowest scores (Rank X...)
    Uses max 5 API calls to prevent rate limiting, finding an approximate or exact rank.
    """
    if total_entries <= 0: return None
    
    API_URL = "https://kovaaks.com/webapp-backend/leaderboard/scores/global"
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/114.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*'
    })
    
    page_size = 50
    total_pages = (total_entries // page_size) + 1
    
    low_page = 0
    high_page = total_pages - 1
    
    # log2(380,000 / 50) is ~13, so 15 requests is a safe upper bound
    max_requests = 15 
    req_count = 0
    
    best_match_rank = None
    best_diff = float('inf')
    
    logging.info(f"Starting Binary Search for Score {target_score} across {total_pages} pages.")
    
    while low_page <= high_page and req_count < max_requests:
        mid_page = (low_page + high_page) // 2
        req_params = {
            'leaderboardId': leaderboard_id,
            'page': mid_page,
            'max': page_size
        }
        
        try:
            r = session.get(API_URL, params=req_params, timeout=5)
            r.raise_for_status()
            req_count += 1
            
            data = r.json()
            board = data.get('data', [])
            
            if not board:
                logging.warning(f"Empty page {mid_page} encountered during binary search.")
                high_page = mid_page - 1
                continue
                
            first_score = board[0].get('score', 0)
            last_score = board[-1].get('score', 0)
            
            logging.info(f"[Search {req_count}/{max_requests}] Page {mid_page}: Range {first_score:.1f} -> {last_score:.1f}")
            
            # Note: Leaderboard is sorted DESCENDING
            if target_score <= first_score and target_score >= last_score:
                logging.info(f"Target score {target_score} is within Page {mid_page} bounds. Scanning page...")
                for entry in board:
                    current_score = entry.get('score', 0)
                    current_rank = entry.get('rank')
                    diff = abs(current_score - target_score)
                    
                    if diff < best_diff:
                        best_diff = diff
                        best_match_rank = current_rank
                    
                    # Since it's descending, the first score we see that is <= our target is our theoretical rank position
                    if current_score <= target_score:
                        return current_rank
                        
                return best_match_rank # In case it's exactly the last one or precision issues
                
            elif target_score > first_score:
                # Target score is higher, meaning we need to go to LOWER page numbers (closer to 0)
                high_page = mid_page - 1
                
                # Check for closest match even if we're not inside the exact window
                for entry in board:
                    diff = abs(entry.get('score', 0) - target_score)
                    if diff < best_diff:
                        best_diff = diff
                        best_match_rank = entry.get('rank')
                        
            elif target_score < last_score:
                # Target score is lower, meaning we need to go to HIGHER page numbers
                low_page = mid_page + 1
                
                for entry in board:
                    diff = abs(entry.get('score', 0) - target_score)
                    if diff < best_diff:
                        best_diff = diff
                        best_match_rank = entry.get('rank')
                        
        except Exception as e:
            logging.error(f"Error during binary search at page {mid_page}: {e}")
            break
            
    logging.info(f"Binary search ended. Best estimated rank: {best_match_rank} (Score diff: {best_diff:.2f})")
    
    # If the search failed to find it perfectly but got fairly close (e.g. within 5% diff), accept it.
    if best_match_rank and (best_diff / max(target_score, 1)) < 0.05:
        return best_match_rank
        
    logging.warning("Failed to find a reasonably close score. Returning None.")
    return None
