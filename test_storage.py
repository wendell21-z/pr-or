import unittest
import os
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from storage import Storage
from db_models import Base


class TestStoragePersistence(unittest.TestCase):
    """Test storage save/load persistence using SQLite in-memory"""

    def setUp(self):
        """Create an in-memory SQLite storage instance"""
        self.db = Storage()
        self.db._engine = create_engine("sqlite:///:memory:")
        from db_models import get_session_factory, init_db
        init_db(self.db._engine)
        self.db._session_factory = get_session_factory(self.db._engine)

    def tearDown(self):
        if self.db._engine:
            self.db._engine.dispose()

    def test_save_and_load(self):
        """Test that data is correctly saved and loaded"""
        self.db.working_times = {"standard": 480}
        self.db.lines = {1: {"id": 1, "code": "L1", "description": "Line 1"}}
        self.db.dies = {1: {"id": 1, "code": "D1", "name": "Die 1", "akz": 6, "lineId": 1}}
        self.db._next_id["line"] = 5

        # Save
        self.db.save()

        # Load into same instance (overwrites)
        self.db.load()

        # Verify data (JSON converts int keys to strings)
        self.assertEqual(self.db.working_times["standard"], 480)
        self.assertIn("1", self.db.lines)
        self.assertEqual(self.db.lines["1"]["code"], "L1")
        self.assertEqual(self.db._next_id["line"], 5)

    def test_load_empty_db(self):
        """Test loading from empty DB returns empty dicts"""
        self.db.load()
        self.assertEqual(self.db.working_times, {})
        self.assertEqual(self.db._next_id["line"], 1)

    def test_clear_all(self):
        """Test that clear_all resets storage and removes DB rows"""
        self.db.working_times = {"standard": 480}
        self.db.save()

        # Verify data exists
        self.db.load()
        self.assertEqual(self.db.working_times["standard"], 480)

        # Clear
        self.db.clear_all()

        # Verify data cleared
        self.assertEqual(self.db.working_times, {})
        self.assertEqual(self.db._next_id["line"], 1)

    def test_pinned_tasks_persistence(self):
        """Test that pinned tasks are persisted"""
        self.db.pinned_tasks = [
            {"taskId": 1, "day": "2026-4-7", "dieId": "D1", "quantity": 100},
            {"taskId": 2, "day": "2026-4-8", "dieId": "D2", "quantity": 200},
        ]
        self.db.save()

        self.db.load()

        self.assertEqual(len(self.db.pinned_tasks), 2)
        self.assertEqual(self.db.pinned_tasks[0]["taskId"], 1)
        self.assertEqual(self.db.pinned_tasks[1]["quantity"], 200)

    def test_solve_results_persistence(self):
        """Test that solve results are persisted"""
        self.db.solve_results = {
            1: [
                {"day": "2026-4-7", "dieCode": "D1", "hits": 100, "seqInDay": 1},
                {"day": "2026-4-7", "dieCode": "D2", "hits": 200, "seqInDay": 2},
            ]
        }
        self.db.solve_status = {1: {"status": "COMPLETED", "score": 5000.0}}
        self.db.save()

        self.db.load()

        # JSON converts int keys to strings
        self.assertIn("1", self.db.solve_results)
        self.assertEqual(len(self.db.solve_results["1"]), 2)
        self.assertEqual(self.db.solve_status["1"]["status"], "COMPLETED")

    def test_memos_persistence(self):
        """Test that memos are persisted"""
        self.db.memos = {
            1: {"dieId": 1, "content": "Test memo 1"},
            2: {"dieId": 2, "content": "Test memo 2"},
        }
        self.db.save()

        self.db.load()

        # JSON converts int keys to strings
        self.assertEqual(len(self.db.memos), 2)
        self.assertEqual(self.db.memos["1"]["content"], "Test memo 1")

    def test_get_next_id(self):
        """Test that ID generator works correctly"""
        id1 = self.db.get_next_id("line")
        id2 = self.db.get_next_id("line")
        id3 = self.db.get_next_id("die")

        self.assertEqual(id1, 1)
        self.assertEqual(id2, 2)
        self.assertEqual(id3, 1)

        # Save and load
        self.db.save()
        self.db.load()

        # Next ID should continue from where we left off
        id4 = self.db.get_next_id("line")
        self.assertEqual(id4, 3)

    def test_session_scope_usage(self):
        """Test that save/load with explicit session works"""
        with self.db.session_scope() as s:
            self.db.working_times = {"std": 480}
            self.db.save(s)

        with self.db.session_scope() as s:
            self.db.load(s)

        self.assertEqual(self.db.working_times["std"], 480)


if __name__ == '__main__':
    unittest.main()
