import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from config import PLAYS_PER_LEVEL

def parse_stats_folder(stats_folder: Path) -> dict:
    """
    Parses all CSVs in the specified KovaaK's stats folder.
    Returns a dictionary mapping scenario_name to aggregated stats.
    """
    if not stats_folder or not stats_folder.exists():
        return {}
        
    # Dictionary to keep track of aggregated data per scenario
    scenarios = defaultdict(lambda: {
        'play_count': 0,
        'best_score': -float('inf'),
        'last_played': '',
        'history': []
    })
    
    # Iterate through all CSVs
    for file_path in stats_folder.glob('*.csv'):
        scenario_name = _extract_scenario_name(file_path.name)
        if not scenario_name:
            continue
            
        try:
            score, date_str = _parse_csv(file_path)
            
            scenarios[scenario_name]['play_count'] += 1
            if score > scenarios[scenario_name]['best_score']:
                scenarios[scenario_name]['best_score'] = score
                
            if date_str and date_str > scenarios[scenario_name]['last_played']:
                scenarios[scenario_name]['last_played'] = date_str
                
            # Collect history
            scenarios[scenario_name]['history'].append((date_str, score))
                
        except Exception as e:
            # Defensive implementation: ignore files that fail to parse
            print(f"Skipping malformed file {file_path.name}: {e}")
            pass
            
    # Finalize results by calculating levels and handling defaults
    results = {}
    for name, data in scenarios.items():
        if data['best_score'] == -float('inf'):
            data['best_score'] = 0.0
            
        play_count = data['play_count']
        
        # Calculate level and remaining plays
        level = (play_count // PLAYS_PER_LEVEL) + 1
        remaining = PLAYS_PER_LEVEL - (play_count % PLAYS_PER_LEVEL)
        
        results[name] = {
            'scenario_name': name,
            **data,
            'level': level,
            'next_level_remaining': remaining
        }
        
    return results

def _extract_scenario_name(filename: str) -> str:
    """
    Extracts scenario name from the standard KovaaK's CSV filename.
    Format usually: "Scenario Name - Challenge - 2021.01.01-12.00.00 Stats.csv"
    We take everything before " - " as a primary guess.
    """
    parts = filename.split(" - ")
    if len(parts) > 0 and len(parts[0]) > 0:
        return parts[0].strip()
    return ""

def _parse_csv(file_path: Path):
    """
    Reads a KovaaK's CSV stat file defensively.
    Looks for the 'Score:' field generically somewhere in the file to handle format changes.
    Falls back to file modification time if timestamp isn't resolvable.
    """
    score = 0.0
    date_str = ""
    
    try:
        # Some CSVs might have different encodings, using utf-8 with fallback
        with open(file_path, mode='r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
            for line in lines:
                lower_line = line.lower()
                
                # Defensively search for score
                if lower_line.startswith("score:"):
                    try:
                        score_part = line.split(",")[1].strip()
                        score = float(score_part)
                    except (IndexError, ValueError):
                        pass
                
                # Defensively search for timestamp
                elif lower_line.startswith("timestamp:"):
                    try:
                        date_str = line.split(",")[1].strip()
                    except IndexError:
                        pass
                        
    except Exception as e:
        # If file IO fails entirely
        print(f"File IO error on {file_path}: {e}")
                    
    # If date couldn't be parsed from the file naturally, use the file metadata
    if not date_str:
        stat = file_path.stat()
        date_str = datetime.fromtimestamp(stat.st_mtime).strftime('%Y/%m/%d %H:%M:%S')
        
    return score, date_str
