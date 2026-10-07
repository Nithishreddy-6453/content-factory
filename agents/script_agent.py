import json
import os
from core.base_agent import BaseAgent
from core.config import config
from plugins.ollama_client import OllamaClient

class ScriptAgent(BaseAgent):
    def __init__(self, run_id: str, niche: str):
        super().__init__(run_id)
        self.niche = niche
        self.selected_path = os.path.join(config.system_run_dir, self.run_id, "selected_story.json")
        self.script_path = os.path.join(config.system_run_dir, self.run_id, "script.json")
        self.llm = OllamaClient()

    def validate_script_structure(self, script: dict) -> bool:
        quality = script.get("quality_score", 0)
        if quality < 90:
            self.logger.warning(f"Script quality score {quality} is below 90 threshold.")
            return False
            
        structure = script.get("structure", {})
        required = ["pattern_interrupt", "curiosity_gap", "evidence", "reveal", "debate_trigger"]
        for req in required:
            if not structure.get(req):
                self.logger.warning(f"Script missing required structure element: {req}")
                return False
        return True

    def generate_script(self, story: dict) -> dict:
        prompt = f"""You are an expert short-form viral video scriptwriter for the {self.niche} niche.
Write a highly engaging documentary-style script for a vertical video (under 60 seconds).
Story Title: {story.get('title')}
Story Angle: {story.get('angle', story.get('summary'))}

Output exactly according to this JSON schema, and NO OTHER TEXT:
{{
  "title": "A catchy title",
  "hook": "The opening 3-second hook spoken script",
  "quality_score": 95,
  "structure": {{
    "pattern_interrupt": "...",
    "curiosity_gap": "...",
    "evidence": "...",
    "reveal": "...",
    "debate_trigger": "..."
  }},
  "duration": 50,
  "story_arc": "Brief explanation of the story arc",
  "scenes": [
    {{
      "scene_id": "scene_1",
      "duration": 5,
      "voiceover": "The spoken words for this scene",
      "onscreen_text": "Bold kinetic text to display",
      "visual_description": "Cinematic documentary style description of what is happening"
    }}
  ]
}}
Ensure scenes seamlessly transition. Focus on high retention.
"""
        response_text = self.llm.generate(
            model=config.llm_script_model,
            prompt=prompt,
            schema={"type": "object"}
        )
        
        try:
            parsed = json.loads(response_text)
            if not self.validate_script_structure(parsed):
                raise ValueError("Script failed V4.3 structure/quality validation.")
            return parsed
        except json.JSONDecodeError:
            self.logger.error("Failed to parse LLM JSON response in ScriptAgent")
            raise ValueError("Invalid JSON from LLM")

    def execute(self) -> bool:
        self.logger.info(f"Starting Script Generation for run {self.run_id}")
        if not os.path.exists(self.selected_path):
            self.logger.error("No selected story found.")
            return False
            
        with open(self.selected_path, 'r') as f:
            story = json.load(f)
            
        script = self.run_with_retry(self.generate_script, retries=3, story=story)
        
        with open(self.script_path, 'w') as f:
            json.dump(script, f, indent=2)
            
        self.logger.info(f"Script Generation complete. Output saved to {self.script_path}")
        return True
