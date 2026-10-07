import sqlite3
import os
from core.config import config
from core.logger import logger

class Database:
    def __init__(self, db_path: str = None):
        # Allow override for testing, otherwise use config
        self.db_path = db_path or config.system_db_path
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        cursor = self.conn.cursor()
        
        # Runs table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            niche TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metrics_json TEXT
        )
        ''')
        
        # Checkpoints table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS checkpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            stage TEXT,
            status TEXT,
            data_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(run_id) REFERENCES runs(run_id)
        )
        ''')
        
        # Feeds table (Deduplication)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS feeds (
            url TEXT PRIMARY KEY,
            title TEXT,
            niche TEXT,
            discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            used_in_run_id TEXT,
            FOREIGN KEY(used_in_run_id) REFERENCES runs(run_id)
        )
        ''')
        
        self.conn.commit()
        logger.info("Database schema initialized.")

    def get_connection(self):
        return self.conn

    # --- Compatibility Layer for UI ---
    
    def get_queue(self):
        c = self.conn.cursor()
        c.execute("SELECT * FROM feeds WHERE used_in_run_id IS NULL ORDER BY discovered_at DESC")
        rows = c.fetchall()
        return [
            {
                "id": row['url'],
                "title": row['title'],
                "description": "",
                "trend_score": 0,
                "niche": row['niche']
            }
            for row in rows
        ]
        
    def update_queue_status(self, item_id: str, status: str):
        pass
        
    def get_pending_runs(self):
        c = self.conn.cursor()
        c.execute("SELECT * FROM runs WHERE status = 'SCRIPT_COMPLETE' ORDER BY updated_at DESC")
        return [dict(r) for r in c.fetchall()]
        
    def get_asset_pending_runs(self):
        c = self.conn.cursor()
        c.execute("SELECT * FROM runs WHERE status = 'SUBTITLE_COMPLETE' ORDER BY updated_at DESC")
        return [dict(r) for r in c.fetchall()]
        
    def get_all_performance(self):
        return []

    def add_to_queue(self, item, score=0, status=""):
        c = self.conn.cursor()
        c.execute("INSERT OR IGNORE INTO feeds (url, title, niche, used_in_run_id) VALUES (?, ?, ?, NULL)", 
                  (item['link'], item['title'], 'football'))
        self.conn.commit()


# Singleton instance
db = Database()
