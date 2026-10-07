import json
import os
from typing import List, Dict
from core.base_agent import BaseAgent
from core.db import db
from core.config import config
from plugins.ollama_client import OllamaClient

class TrendAgent(BaseAgent):
    def __init__(self, run_id: str, niche: str):
        super().__init__(run_id)
        self.niche = niche
        self.candidates_path = os.path.join(config.system_run_dir, self.run_id, "story_candidates.json")
        self.selected_path = os.path.join(config.system_run_dir, self.run_id, "selected_story.json")
        self.trend_score_path = os.path.join(config.system_run_dir, self.run_id, "trend_score.json")
        self.llm = OllamaClient()

    def _mark_as_used(self, url: str, title: str):
        cursor = db.get_connection().cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO feeds (url, title, niche, used_in_run_id) VALUES (?, ?, ?, ?)",
            (url, title, self.niche, self.run_id)
        )
        db.get_connection().commit()

    def evaluate_candidates(self, candidates: List[Dict]) -> Dict:
        prompt = "You are a viral trend analyst. Evaluate the following story candidates and select the one with the highest viral potential based on novelty, recency, emotion, controversy, and shareability.\n\n"
        for idx, c in enumerate(candidates):
            prompt += f"Candidate {idx}:\nTitle: {c['title']}\nSummary: {c['summary']}\n\n"
            
        prompt += """
        Return ONLY a JSON object with the following schema:
        {
          "selected_index": 0,
          "trend_score": {
            "novelty": 8,
            "emotion": 9,
            "controversy": 5,
            "shareability": 9,
            "overall_score": 31
          },
          "reasoning": "Explanation here..."
        }
        """
        
        response_text = self.llm.generate(
            model=config.llm_viral_model,
            prompt=prompt,
            schema={"type": "object"}
        )
        
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            self.logger.error("Failed to parse LLM JSON response in TrendAgent")
            return {"selected_index": 0, "trend_score": {"overall_score": 0}, "reasoning": "Fallback to first due to parse error"}

    
    def transform_topic(self, story: dict) -> dict:
        prompt = f"""You are an expert viral content strategist for {self.niche}.
Analyze this raw news story:
Title: {story.get('title')}
Summary: {story.get('summary')}

Generate exactly 4 distinct viral angles to cover this story for a vertical short. 
Score each angle (0-100) on virality, and select the highest scoring one as 'best_angle'.

Output exactly according to this JSON schema:
{{
  "angles": [
    {{"angle": "Description of the angle", "score": 85}}
  ],
  "best_angle": "The exact description of the highest scoring angle",
  "reasoning": "Why this angle is best"
}}
"""
        response_text = self.llm.generate(
            model=config.llm_script_model,
            prompt=prompt,
            schema={"type": "object"}
        )
        try:
            return json.loads(response_text)
        except:
            raise ValueError("Failed to parse angle transformation JSON")

    def execute(self) -> bool:
        self.logger.info(f"Starting Trend Intelligence for run {self.run_id}")
        if not os.path.exists(self.candidates_path):
            self.logger.error("No story candidates found.")
            return False
            
        with open(self.candidates_path, 'r') as f:
            candidates = json.load(f)
            
        if not candidates:
            self.logger.warning("Candidate list is empty.")
            return False
            
        # Optimization: evaluate top 5
        candidates_to_eval = candidates[:5]
        
        evaluation = self.run_with_retry(self.evaluate_candidates, retries=3, candidates=candidates_to_eval)
        
        idx = evaluation.get("selected_index", 0)
        if idx < 0 or idx >= len(candidates_to_eval):
            idx = 0
            
        selected_story = candidates_to_eval[idx]
        transformed_story = self.run_with_retry(self.transform_topic, retries=3, story=selected_story)
        selected_story["angle"] = transformed_story.get("best_angle", "")
        selected_story["angle_reasoning"] = transformed_story.get("reasoning", "")
        evaluation["topic_transformation"] = transformed_story
        
        with open(self.trend_score_path, 'w') as f:
            json.dump(evaluation, f, indent=2)
            
        with open(self.selected_path, 'w') as f:
            json.dump(selected_story, f, indent=2)
            
        self._mark_as_used(selected_story["link"], selected_story["title"])
        
        self.logger.info(f"Trend Intelligence complete. Selected: {selected_story['title']} (Score: {evaluation.get('trend_score', {}).get('overall_score')})")
        return True
