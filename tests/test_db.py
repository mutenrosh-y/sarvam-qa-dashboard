import unittest
import json
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import (
    init_db,
    save_call,
    get_all_calls,
    get_call_details,
    save_scorecard,
    get_scorecard,
    get_latest_scorecard,
    delete_call,
    get_call_count,
    DB_PATH
)


class TestDatabase(unittest.TestCase):
    """Test suite for database CRUD operations."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database before running tests."""
        # Use a test database
        global DB_PATH
        DB_PATH = "test_qa_database.db"
        
    def setUp(self):
        """Initialize database before each test."""
        # Remove test database if it exists
        if os.path.exists("test_qa_database.db"):
            os.remove("test_qa_database.db")
        
        # Patch DB_PATH in the database module
        import database
        database.DB_PATH = "test_qa_database.db"
        
        init_db()
    
    def tearDown(self):
        """Clean up test database after each test."""
        if os.path.exists("test_qa_database.db"):
            os.remove("test_qa_database.db")
    
    def test_init_db(self):
        """Test database initialization creates tables."""
        import sqlite3
        conn = sqlite3.connect("test_qa_database.db")
        cursor = conn.cursor()
        
        # Check calls table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='calls'")
        self.assertIsNotNone(cursor.fetchone())
        
        # Check scorecards table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scorecards'")
        self.assertIsNotNone(cursor.fetchone())
        
        conn.close()
    
    def test_save_call(self):
        """Test saving a call record."""
        grades = {"quality": 8.5, "clarity": 9.0, "professionalism": 8.0}
        
        call_id = save_call(
            filename="test_call.wav",
            upload_time="2024-01-15T10:30:00",
            transcript="This is a test transcript.",
            analysis="This is test analysis.",
            grades=grades
        )
        
        self.assertIsNotNone(call_id)
        self.assertGreater(call_id, 0)
    
    def test_get_all_calls(self):
        """Test retrieving all calls."""
        for i in range(3):
            save_call(
                filename=f"test_call_{i}.wav",
                upload_time=f"2024-01-15T10:{i}0:00",
                transcript=f"Transcript {i}",
                analysis=f"Analysis {i}",
                grades={"quality": 8.0 + i}
            )
        
        calls = get_all_calls()
        self.assertEqual(len(calls), 3)
        
        filenames = [call['filename'] for call in calls]
        self.assertIn("test_call_0.wav", filenames)
        self.assertIn("test_call_1.wav", filenames)
        self.assertIn("test_call_2.wav", filenames)
    
    def test_get_call_details(self):
        """Test retrieving detailed call information."""
        grades = {"quality": 8.5, "clarity": 9.0}
        
        call_id = save_call(
            filename="detail_test.wav",
            upload_time="2024-01-15T10:30:00",
            transcript="Test transcript content",
            analysis="Test analysis content",
            grades=grades
        )
        
        details = get_call_details(call_id)
        
        self.assertIsNotNone(details)
        self.assertEqual(details['filename'], "detail_test.wav")
        self.assertEqual(details['transcript'], "Test transcript content")
        self.assertEqual(details['analysis'], "Test analysis content")
        self.assertEqual(details['grades'], grades)
    
    def test_get_call_details_not_found(self):
        """Test retrieving non-existent call returns None."""
        details = get_call_details(9999)
        self.assertIsNone(details)
    
    def test_save_scorecard(self):
        """Test saving a scorecard."""
        criteria = {
            "communication": {"weight": 0.3, "description": "Communication skills"},
            "technical": {"weight": 0.4, "description": "Technical knowledge"},
            "professionalism": {"weight": 0.3, "description": "Professional behavior"}
        }
        
        save_scorecard(version=1, criteria=criteria)
        
        # Verify it was saved
        scorecard = get_scorecard(version=1)
        self.assertIsNotNone(scorecard)
        self.assertEqual(scorecard['criteria'], criteria)
    
    def test_get_scorecard(self):
        """Test retrieving a specific scorecard."""
        criteria = {"test": "data"}
        save_scorecard(version=1, criteria=criteria)
        
        scorecard = get_scorecard(version=1)
        self.assertIsNotNone(scorecard)
        self.assertEqual(scorecard['version'], 1)
        self.assertEqual(scorecard['criteria'], criteria)
    
    def test_get_latest_scorecard(self):
        """Test retrieving the latest scorecard version."""
        # Save multiple versions
        save_scorecard(version=1, criteria={"v": 1})
        save_scorecard(version=2, criteria={"v": 2})
        save_scorecard(version=3, criteria={"v": 3})
        
        latest = get_latest_scorecard()
        self.assertIsNotNone(latest)
        self.assertEqual(latest['version'], 3)
        self.assertEqual(latest['criteria'], {"v": 3})
    
    def test_delete_call(self):
        """Test deleting a call record."""
        call_id = save_call(
            filename="delete_test.wav",
            upload_time="2024-01-15T10:30:00",
            transcript="Test",
            analysis="Test",
            grades={}
        )
        
        # Verify it exists
        self.assertIsNotNone(get_call_details(call_id))
        
        # Delete it
        result = delete_call(call_id)
        self.assertTrue(result)
        
        # Verify it's gone
        self.assertIsNone(get_call_details(call_id))
    
    def test_delete_nonexistent_call(self):
        """Test deleting non-existent call returns False."""
        result = delete_call(9999)
        self.assertFalse(result)
    
    def test_get_call_count(self):
        """Test getting total call count."""
        # Initially empty
        self.assertEqual(get_call_count(), 0)
        
        # Add calls
        for i in range(5):
            save_call(
                filename=f"count_test_{i}.wav",
                upload_time="2024-01-15T10:30:00",
                transcript="Test",
                analysis="Test",
                grades={}
            )
        
        self.assertEqual(get_call_count(), 5)
    
    def test_json_serialization(self):
        """Test that complex data types are properly serialized/deserialized."""
        complex_grades = {
            "overall": 8.5,
            "categories": {
                "communication": 9.0,
                "technical": 8.0,
                "professionalism": 8.5
            },
            "tags": ["excellent", "professional"],
            "notes": "Very good performance"
        }
        
        call_id = save_call(
            filename="json_test.wav",
            upload_time="2024-01-15T10:30:00",
            transcript="Test",
            analysis="Test",
            grades=complex_grades
        )
        
        details = get_call_details(call_id)
        self.assertEqual(details['grades'], complex_grades)
    
    def test_unique_filename_constraint(self):
        """Test that duplicate filenames are rejected."""
        save_call(
            filename="unique_test.wav",
            upload_time="2024-01-15T10:30:00",
            transcript="Test",
            analysis="Test",
            grades={}
        )
        
        # Try to save with same filename
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):
            save_call(
                filename="unique_test.wav",
                upload_time="2024-01-15T10:31:00",
                transcript="Test 2",
                analysis="Test 2",
                grades={}
            )


if __name__ == '__main__':
    unittest.main()
