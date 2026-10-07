import unittest
import os
from core.db import db
from core.state_machine import StateMachine

class TestCoreEngine(unittest.TestCase):
    def test_database_initialization(self):
        """Test that the database is created and schemas exist."""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        self.assertIn('runs', tables)
        self.assertIn('checkpoints', tables)
        self.assertIn('feeds', tables)

    def test_state_machine(self):
        """Test that the state machine records transitions properly."""
        sm = StateMachine("test_run_001", "tech_news")
        self.assertEqual(sm.get_current_stage(), "INIT")
        
        sm.transition("DISCOVERY_COMPLETE")
        self.assertEqual(sm.get_current_stage(), "DISCOVERY_COMPLETE")
        
        # Verify checkpoint was recorded
        cursor = db.get_connection().cursor()
        cursor.execute("SELECT stage FROM checkpoints WHERE run_id = ?", ("test_run_001",))
        stages = [row['stage'] for row in cursor.fetchall()]
        self.assertIn("DISCOVERY_COMPLETE", stages)

if __name__ == '__main__':
    unittest.main()
