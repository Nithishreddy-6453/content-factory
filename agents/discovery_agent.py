import json
import os
import feedparser
from typing import List, Dict
from core.base_agent import BaseAgent
from core.db import db
from core.config import config

class DiscoveryAgent(BaseAgent):
    def __init__(self, run_id: str, niche: str):
        super().__init__(run_id)
        self.niche = niche
        # Ensure run_dir exists
        os.makedirs(os.path.join(config.system_run_dir, self.run_id), exist_ok=True)
        self.feeds_file = os.path.join("niches", self.niche, "feeds.yaml")
        self.candidates_path = os.path.join(config.system_run_dir, self.run_id, "story_candidates.json")

    def _load_feeds(self) -> List[str]:
        import yaml
        if not os.path.exists(self.feeds_file):
            self.logger.warning(f"No feeds.yaml found for niche {self.niche}")
            return []
        with open(self.feeds_file, 'r') as f:
            data = yaml.safe_load(f)
            return data.get('rss_feeds', [])

    def _is_duplicate(self, url: str) -> bool:
        cursor = db.get_connection().cursor()
        cursor.execute("SELECT url FROM feeds WHERE url = ?", (url,))
        return cursor.fetchone() is not None

    def fetch_candidates(self) -> List[Dict]:
        feeds = self._load_feeds()
        candidates = []
        for feed_url in feeds:
            self.logger.debug(f"Parsing feed: {feed_url}")
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:15]: # Check top 15 per feed
                    if not self._is_duplicate(entry.link):
                        candidates.append({
                            "title": entry.title,
                            "link": entry.link,
                            "summary": entry.get('summary', ''),
                            "published": entry.get('published', '')
                        })
            except Exception as e:
                self.logger.warning(f"Failed to parse feed {feed_url}: {str(e)}")
        return candidates

    def execute(self) -> bool:
        self.logger.info(f"Starting Discovery for run {self.run_id} in niche {self.niche}")
        candidates = self.run_with_retry(self.fetch_candidates)
        
        # Save candidates
        with open(self.candidates_path, 'w') as f:
            json.dump(candidates, f, indent=2)
            
        if not candidates:
            self.logger.warning("No new stories found during discovery.")
            return False
            
        self.logger.info(f"Discovery complete. Found {len(candidates)} new candidates.")
        return True
