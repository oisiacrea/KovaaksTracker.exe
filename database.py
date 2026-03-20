import sqlite3
from typing import List, Dict, Any
from config import DB_PATH

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        # Create scenarios table with local and web stats
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scenarios (
                scenario_name TEXT PRIMARY KEY,
                local_play_count INTEGER DEFAULT 0,
                best_score REAL DEFAULT 0,
                last_played TEXT,
                level INTEGER DEFAULT 1,
                next_level_remaining INTEGER DEFAULT 100,
                web_total_plays INTEGER,
                web_total_entries INTEGER,
                web_rank INTEGER,
                top_percent REAL,
                tier_rank TEXT,
                web_last_updated TEXT
            )
        ''')
        
        # Defensive schema upgrade for MVP->v2 evolution if table already exists
        try:
            cursor.execute("ALTER TABLE scenarios ADD COLUMN tier_rank TEXT")
        except sqlite3.OperationalError:
            pass # Column already exists
        
        # Create play history table for charting
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS play_history (
                scenario_name TEXT,
                timestamp TEXT,
                score REAL,
                UNIQUE(scenario_name, timestamp, score)
            )
        ''')
        
        conn.commit()

def update_scenario_local_stats(scenario_name: str, play_count: int, best_score: float, last_played: str, level: int, remaining: int, history: List[tuple] = None):
    """
    Updates or inserts the local CSV statistics for a scenario.
    Optionally batch inserts play history.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO scenarios (scenario_name, local_play_count, best_score, last_played, level, next_level_remaining)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(scenario_name) DO UPDATE SET
                local_play_count = excluded.local_play_count,
                best_score = MAX(scenarios.best_score, excluded.best_score),
                last_played = MAX(IFNULL(scenarios.last_played, ''), excluded.last_played),
                level = excluded.level,
                next_level_remaining = excluded.next_level_remaining
        ''', (scenario_name, play_count, best_score, last_played, level, remaining))
        
        # Batch insert history
        if history:
            cursor.executemany('''
                INSERT OR IGNORE INTO play_history (scenario_name, timestamp, score)
                VALUES (?, ?, ?)
            ''', [(scenario_name, ts, sc) for ts, sc in history])
            
        conn.commit()
        
def get_play_history(scenario_name: str) -> List[tuple]:
    """
    Retrieves the complete play history for a scenario.
    Returns list of (timestamp, score) ordered chronologically.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timestamp, score 
            FROM play_history 
            WHERE scenario_name = ? 
            ORDER BY timestamp ASC
        ''', (scenario_name,))
        return cursor.fetchall()
        
def get_all_scenarios() -> List[Dict[str, Any]]:
    """
    Retrieves all scenarios ordered by last played date descending.
    """
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM scenarios ORDER BY last_played DESC')
        return [dict(row) for row in cursor.fetchall()]

def update_scenario_web_stats(scenario_name: str, web_data: dict):
    """
    Updates the web scraped data for a scenario.
    """
    import logging
    
    if web_data is None:
        logging.warning(f"update_scenario_web_stats received None for '{scenario_name}'. Skipping DB update.")
        return
        
    logging.info(f"DB update_scenario_web_stats received web_data type: {type(web_data)}")
    
    with get_connection() as conn:
        cursor = conn.cursor()
            
        cursor.execute('''
            UPDATE scenarios SET
                web_total_plays = ?,
                web_total_entries = ?,
                web_rank = ?,
                top_percent = ?,
                tier_rank = ?,
                web_last_updated = ?
            WHERE scenario_name = ?
        ''', (
            web_data.get('web_total_plays'),
            web_data.get('web_total_entries'),
            web_data.get('web_rank'),
            web_data.get('top_percent'),
            web_data.get('tier_rank'),
            web_data.get('web_last_updated'),
            scenario_name
        ))
        conn.commit()
