import json
import os
from core.base_agent import BaseAgent
from core.config import config
from plugins.ollama_client import OllamaClient

class SceneAgent(BaseAgent):
    def __init__(self, run_id: str, niche: str):
        super().__init__(run_id)
        self.niche = niche
        self.script_path = os.path.join(config.system_run_dir, self.run_id, "script.json")
        self.scene_plan_path = os.path.join(config.system_run_dir, self.run_id, "scene_plan.json")
        self.llm = OllamaClient()

    import time
    def generate_scene_plan(self, script: dict) -> dict:
        prompt = f"""You are a professional cinematographer and AI image generation prompt engineer.
Analyze the following video script and create a detailed scene plan.
Maintain STRICT visual consistency across all scenes (same art style, color grading, and subject appearance).

Script Title: {script.get('title')}
Scenes: {json.dumps(script.get('scenes', []), indent=2)}

Output exactly according to this JSON schema, and NO OTHER TEXT:
{{
  "global_visual_style": "Describe the consistent visual style (e.g., hyperrealistic, cinematic lighting, 8k resolution, cinematic color grading, specific color palette)",
  "scenes": [
    {{
      "scene_id": "scene_1",
      "camera_angle": "e.g., low angle, eye level, wide shot",
      "camera_movement": "e.g., slow pan right, static, zoom in",
      "subject": "Detailed description of the main subject",
      "environment": "Detailed description of the background/environment",
      "lighting": "e.g., neon synthwave lighting, soft morning light",
      "emotion": "e.g., tense, joyful, mysterious",
      "composition": "e.g., rule of thirds, center framed",
      "image_prompt": "A comma-separated stable diffusion prompt combining the above elements"
    }}
  ]
}}
"""
        model = config.llm_scene_model
        scenes_count = len(script.get('scenes', []))
        options = {"temperature": 0.1, "num_predict": 2048}
        
        self.logger.info(f"Scene Planning Request: run_id={self.run_id}, model={model}, scenes={scenes_count}, prompt_len={len(prompt)}, options={options}")
        
        import time
        start_t = time.time()
        response_text = self.llm.generate(
            model=model,
            prompt=prompt,
            schema={"type": "object"},
            options=options
        )
        elapsed = time.time() - start_t
        
        try:
            parsed = json.loads(response_text)
            self.logger.info(f"Scene Planning Response: elapsed={elapsed:.2f}s, response_len={len(response_text)}, json_parse_success=True")
            return parsed
        except json.JSONDecodeError as e:
            self.logger.error(f"Scene Planning Response: elapsed={elapsed:.2f}s, response_len={len(response_text)}, json_parse_success=False")
            raise ValueError(f"Invalid JSON from LLM: {str(e)}")

    def execute(self) -> bool:
        self.script_path = os.path.join(config.system_run_dir, self.run_id, "script.json")
        self.scene_plan_path = os.path.join(config.system_run_dir, self.run_id, "scene_plan.json")
        run_dir = os.path.dirname(self.script_path)
        
        self.logger.info(f"Starting Scene Planning for run {self.run_id}")
        if not os.path.exists(run_dir):
            self.logger.error(f"Run directory missing: {run_dir}")
            return False
            
        if not os.path.exists(self.script_path):
            self.logger.error(f"Script file missing exactly at expected canonical path: {self.script_path}")
            return False
            
        try:
            with open(self.script_path, 'r') as f:
                script = json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load script JSON from {self.script_path}: {e}")
            return False
            
        if not script or 'scenes' not in script:
            self.logger.error("Script JSON loaded but missing 'scenes' array or other expected content.")
            return False
            
        # Retry loop for Scene Planning
        retries = 2
        scene_plan = None
        last_exception = None
        for attempt in range(1, retries + 1):
            try:
                self.logger.info(f"SceneAgent generation attempt {attempt}/{retries}")
                scene_plan = self.generate_scene_plan(script)
                break
            except Exception as e:
                last_exception = e
                self.logger.warning(f"SceneAgent attempt {attempt} failed: {str(e)}")
                if attempt == retries:
                    self.logger.error(f"SceneAgent all {retries} attempts failed. Final error: {str(e)}")
                    raise e
                import time
                time.sleep(2)  # small wait before retry
        
        with open(self.scene_plan_path, 'w') as f:
            json.dump(scene_plan, f, indent=2)
            
        self.logger.info(f"Scene Planning complete. Output saved to {self.scene_plan_path}")
        return True
