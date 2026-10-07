import json
import os
from core.db import db
from core.logger import logger
from core.config import config

class StateMachine:
    STAGES = [
        "INIT",
        "DISCOVERY_COMPLETE",
        "TREND_COMPLETE",
        "SCRIPT_COMPLETE",
        "SCRIPT_APPROVED",
        "SCENE_PLAN_COMPLETE",
        "AUDIO_COMPLETE",
        "VISUAL_COMPLETE",
        "SUBTITLE_COMPLETE",
        "ASSETS_APPROVED",
        "RENDER_COMPLETE",
        "QA_COMPLETE",
        "DONE",
        "FAILED"
    ]

    def __init__(self, run_id: str, niche: str):
        self.run_id = run_id
        self.niche = niche
        self.run_dir = os.path.join(config.system_run_dir, run_id)
        os.makedirs(self.run_dir, exist_ok=True)
        self._initialize_run()

    def _initialize_run(self):
        cursor = db.get_connection().cursor()
        cursor.execute("SELECT run_id FROM runs WHERE run_id = ?", (self.run_id,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO runs (run_id, niche, status) VALUES (?, ?, ?)",
                (self.run_id, self.niche, "INIT")
            )
            db.get_connection().commit()
            logger.info(f"Initialized new run {self.run_id} for niche {self.niche}")

    def transition(self, new_stage: str, data: dict = None):
        if new_stage not in self.STAGES:
            logger.error(f"Invalid stage transition: {new_stage}")
            raise ValueError(f"Invalid stage: {new_stage}")
            
        current_stage = self.get_current_stage()
        if current_stage == "FAILED" and new_stage != "FAILED":
            logger.error(f"Cannot transition run {self.run_id} from FAILED to {new_stage}")
            raise RuntimeError(f"Cannot transition run {self.run_id} from FAILED to {new_stage}")

        cursor = db.get_connection().cursor()
        
        # Record checkpoint
        data_json = json.dumps(data) if data else "{}"
        cursor.execute(
            "INSERT INTO checkpoints (run_id, stage, status, data_json) VALUES (?, ?, ?, ?)",
            (self.run_id, new_stage, "COMPLETED", data_json)
        )
        
        # Update run status
        cursor.execute(
            "UPDATE runs SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE run_id = ?",
            (new_stage, self.run_id)
        )
        
        db.get_connection().commit()
        logger.info(f"Run {self.run_id} transitioned to {new_stage}")
        
    def fail(self, error_msg: str):
        self.transition("FAILED", {"error": error_msg})
        
    def get_current_stage(self) -> str:
        cursor = db.get_connection().cursor()
        cursor.execute("SELECT status FROM runs WHERE run_id = ?", (self.run_id,))
        row = cursor.fetchone()
        return row['status'] if row else None
