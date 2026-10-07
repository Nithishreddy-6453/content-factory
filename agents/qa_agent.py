import json
import os
from moviepy import VideoFileClip
from core.base_agent import BaseAgent
from core.config import config

class QA_Agent(BaseAgent):
    def __init__(self, run_id: str, niche: str):
        super().__init__(run_id)
        self.niche = niche
        self.script_path = os.path.join(config.system_run_dir, self.run_id, "script.json")
        self.visual_manifest_path = os.path.join(config.system_run_dir, self.run_id, "visual_manifest.json")
        self.audio_path = os.path.join(config.system_run_dir, self.run_id, "final_audio.mp3")
        self.final_video_path = os.path.join(config.system_run_dir, self.run_id, "final_video.mp4")
        self.qa_report_path = os.path.join(config.system_run_dir, self.run_id, "qa_report.json")

    def execute(self) -> bool:
        self.logger.info(f"Starting Quality Assurance Engine for run {self.run_id}")
        report = {
            "passed": True,
            "errors": [],
            "warnings": [],
            "metrics": {}
        }

        # 1. Check Missing Files
        required_files = [self.script_path, self.visual_manifest_path, self.audio_path, self.final_video_path]
        for f in required_files:
            if not os.path.exists(f):
                report["errors"].append(f"Missing critical file: {f}")
                report["passed"] = False
                
        if not report["passed"]:
            self._save_report(report)
            return False
            
        # 2. Scene Count Consistency
        try:
            with open(self.script_path, 'r') as f:
                script = json.load(f)
            with open(self.visual_manifest_path, 'r') as f:
                manifest = json.load(f)
                
            script_scenes = len(script.get("scenes", []))
            manifest_scenes = len(manifest)
            if script_scenes != manifest_scenes:
                report["errors"].append(f"Scene count mismatch: Script ({script_scenes}) vs Manifest ({manifest_scenes})")
                report["passed"] = False
        except Exception as e:
            report["errors"].append(f"JSON validation failed: {str(e)}")
            report["passed"] = False

        # 3. Video Metrics & Corruption
        try:
            clip = VideoFileClip(self.final_video_path)
            report["metrics"]["duration"] = clip.duration
            report["metrics"]["resolution"] = clip.size
            report["metrics"]["fps"] = clip.fps
            
            # 4. Duration constraints (e.g. vertical shorts < 60s)
            if clip.duration > 60:
                report["warnings"].append(f"Video duration is over 60 seconds ({clip.duration}s)")
                
            # 5. Resolution check (e.g. 1080x1920)
            target_res = tuple(map(int, config.render_resolution.split('x')))
            if tuple(clip.size) != target_res:
                report["warnings"].append(f"Resolution {clip.size} does not match target {target_res}")
                
            clip.close()
        except Exception as e:
            report["errors"].append(f"Video file corruption or unreadable: {str(e)}")
            report["passed"] = False

        self._save_report(report)
        
        if report["passed"]:
            self.logger.info("QA Passed successfully.")
            return True
        else:
            self.logger.error("QA Failed.")
            for err in report["errors"]:
                self.logger.error(f"QA Error: {err}")
            return False

    def _save_report(self, report: dict):
        with open(self.qa_report_path, 'w') as f:
            json.dump(report, f, indent=2)
