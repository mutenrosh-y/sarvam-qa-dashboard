import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

DB_PATH = "qa_database.db"


@contextmanager
def get_db_connection():
    """Context manager for database connections with WAL mode enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode=WAL;")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Initialize database with schema for calls and scorecards tables."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Create calls table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calls (
                call_id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL UNIQUE,
                upload_time TEXT NOT NULL,
                transcript TEXT NOT NULL,
                analysis TEXT NOT NULL,
                grades TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create scorecards table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scorecards (
                version INTEGER PRIMARY KEY,
                criteria TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()


def save_call(
    filename: str,
    upload_time: str,
    transcript: str,
    analysis: str,
    grades: Dict[str, Any]
) -> Optional[int]:
    """
    Save a call record to the database.
    
    Args:
        filename: Name of the uploaded file
        upload_time: Timestamp of upload
        transcript: Call transcript text
        analysis: Analysis text
        grades: Dictionary of grades (will be stored as JSON)
    
    Returns:
        call_id of the inserted record
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        grades_json = json.dumps(grades)
        
        cursor.execute("""
            INSERT INTO calls (filename, upload_time, transcript, analysis, grades)
            VALUES (?, ?, ?, ?, ?)
        """, (filename, upload_time, transcript, analysis, grades_json))
        
        conn.commit()
        return cursor.lastrowid


def get_all_calls() -> List[Dict[str, Any]]:
    """
    Retrieve all call records from the database.
    
    Returns:
        List of dictionaries containing call data
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT call_id, filename, upload_time, created_at
            FROM calls
            ORDER BY created_at DESC
        """)
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_call_details(call_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve detailed information for a specific call.
    
    Args:
        call_id: ID of the call to retrieve
    
    Returns:
        Dictionary containing call details, or None if not found
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT call_id, filename, upload_time, transcript, analysis, grades, created_at
            FROM calls
            WHERE call_id = ?
        """, (call_id,))
        
        row = cursor.fetchone()
        if row is None:
            return None
        
        result = dict(row)
        # Parse JSON fields
        result['grades'] = json.loads(result['grades'])
        return result


def save_scorecard(version: int, criteria: Dict[str, Any]) -> None:
    """
    Save or update a scorecard version.
    
    Args:
        version: Version number of the scorecard
        criteria: Dictionary of criteria (will be stored as JSON)
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        criteria_json = json.dumps(criteria)
        
        cursor.execute("""
            INSERT OR REPLACE INTO scorecards (version, criteria)
            VALUES (?, ?)
        """, (version, criteria_json))
        
        conn.commit()


def get_scorecard(version: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific scorecard version.
    
    Args:
        version: Version number of the scorecard
    
    Returns:
        Dictionary containing scorecard data, or None if not found
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT version, criteria, created_at
            FROM scorecards
            WHERE version = ?
        """, (version,))
        
        row = cursor.fetchone()
        if row is None:
            return None
        
        result = dict(row)
        result['criteria'] = json.loads(result['criteria'])
        return result


def get_latest_scorecard() -> Optional[Dict[str, Any]]:
    """
    Retrieve the latest scorecard version.
    
    Returns:
        Dictionary containing the latest scorecard data, or None if none exist
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT version, criteria, created_at
            FROM scorecards
            ORDER BY version DESC
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        if row is None:
            return None
        
        result = dict(row)
        result['criteria'] = json.loads(result['criteria'])
        return result


def delete_call(call_id: int) -> bool:
    """
    Delete a call record from the database.
    
    Args:
        call_id: ID of the call to delete
    
    Returns:
        True if a record was deleted, False otherwise
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM calls WHERE call_id = ?", (call_id,))
        conn.commit()
        return cursor.rowcount > 0


def get_call_count() -> int:
    """Get total number of calls in the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM calls")
        return cursor.fetchone()[0]
