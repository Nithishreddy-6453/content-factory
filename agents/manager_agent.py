import os
import time
import json
import concurrent.futures
from datetime import datetime
import shutil

from core.logger import logger
from core.db import db
from core.config import config
from core.state_machine import StateMachine

# Agents
from agents.discovery_agent import DiscoveryAgent
from agents.trend_agent import TrendAgent
from agents.script_agent import ScriptAgent
from agents.scene_agent import SceneAgent
from agents.audio_agent import AudioAgent
from agents.visual_agent import VisualAgent
from agents.subtitle_agent import SubtitleAgent
from agents.render_agent import RenderAgent
from agents.qa_agent import QA_Agent

class ManagerAgent:
    def __init__(self, niche: str):
        self.niche = niche
        self.run_id = f"run_{datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}"
        self.state_machine = StateMachine(self.run_id, self.niche)
        self.run_dir = os.path.join(config.system_run_dir, self.run_id)
        
        self.agents = {
            "DISCOVERY": DiscoveryAgent(self.run_id, self.niche),
            "TREND": TrendAgent(self.run_id, self.niche),
            "SCRIPT": ScriptAgent(self.run_id, self.niche),
            "SCENE": SceneAgent(self.run_id, self.niche),
            "AUDIO": AudioAgent(self.run_id, self.niche),
            "VISUAL": VisualAgent(self.run_id, self.niche),
            "SUBTITLE": SubtitleAgent(self.run_id, self.niche),
            "RENDER": RenderAgent(self.run_id, self.niche),
            "QA": QA_Agent(self.run_id, self.niche)
        }

    def _snapshot_configs(self):
        shutil.copy("configs/config.yaml", os.path.join(self.run_dir, "snapshot_config.yaml"))
        niche_feeds = os.path.join("niches", self.niche, "feeds.yaml")
        if os.path.exists(niche_feeds):
            shutil.copy(niche_feeds, os.path.join(self.run_dir, "snapshot_feeds.yaml"))

    def execute_workflow(self, run_id: str = None):
        if run_id:
            self.run_id = run_id
            self.state_machine.run_id = run_id
            self.run_dir = os.path.join(self.config.system_run_dir, self.run_id) if hasattr(self, 'config') else os.path.join("runs", self.run_id)
            # Re-init agents with correct run_id
            for agent in self.agents.values():
                agent.run_id = run_id
                
        current_stage = self.state_machine.get_current_stage()
        logger.info(f"--- STARTING/RESUMING RUN {self.run_id} FOR NICHE {self.niche} (Stage: {current_stage}) ---")
        
        if current_stage == "INIT":
            self._snapshot_configs()
            
        start_time = time.time()
        
        try:
            # PHASE 1: Story to Script
            if current_stage in ["INIT", "DISCOVERY_COMPLETE", "TREND_COMPLETE"]:
                if current_stage == "INIT":
                    if self.agents["DISCOVERY"].execute():
                        self.state_machine.transition("DISCOVERY_COMPLETE")
                    else:
                        return self.state_machine.fail("Discovery found no candidates.")
                        
                current_stage = self.state_machine.get_current_stage()
                if current_stage == "DISCOVERY_COMPLETE":
                    if self.agents["TREND"].execute():
                        self.state_machine.transition("TREND_COMPLETE")
                    else:
                        return self.state_machine.fail("Trend analysis failed.")
                        
                current_stage = self.state_machine.get_current_stage()
                if current_stage == "TREND_COMPLETE":
                    if self.agents["SCRIPT"].execute():
                        self.state_machine.transition("SCRIPT_COMPLETE")
                    else:
                        return self.state_machine.fail("Script generation failed.")
                
                logger.info(f"STOPPING: Script generation complete for {self.run_id}. Waiting for SCRIPT_APPROVED.")
                return True

            # PHASE 2: Script to Assets
            elif current_stage == "SCRIPT_APPROVED":
                if self.agents["SCENE"].execute():
                    self.state_machine.transition("SCENE_PLAN_COMPLETE")
                else:
                    return self.state_machine.fail("Scene planning failed.")

                logger.info("Starting Parallel Execution: Audio & Visual")
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    future_audio = executor.submit(self.agents["AUDIO"].execute)
                    future_visual = executor.submit(self.agents["VISUAL"].execute)
                    
                    audio_success = future_audio.result()
                    visual_success = future_visual.result()
                    
                if audio_success:
                    self.state_machine.transition("AUDIO_COMPLETE")
                else:
                    return self.state_machine.fail("Audio generation failed.")
                    
                if visual_success:
                    self.state_machine.transition("VISUAL_COMPLETE")
                else:
                    return self.state_machine.fail("Visual generation failed.")
                    
                if self.agents["SUBTITLE"].execute():
                    self.state_machine.transition("SUBTITLE_COMPLETE")
                else:
                    return self.state_machine.fail("Subtitle generation failed.")
                    
                logger.info(f"STOPPING: Asset generation complete for {self.run_id}. Waiting for ASSETS_APPROVED.")
                return True

            # PHASE 3: Render and QA
            elif current_stage == "ASSETS_APPROVED":
                if self.agents["RENDER"].execute():
                    self.state_machine.transition("RENDER_COMPLETE")
                else:
                    return self.state_machine.fail("Render failed.")
                    
                if self.agents["QA"].execute():
                    self.state_machine.transition("QA_COMPLETE")
                else:
                    return self.state_machine.fail("QA Validation failed.")
                    
                self.state_machine.transition("DONE")
                
                end_time = time.time()
                total_time = end_time - start_time
                logger.info(f"--- WORKFLOW COMPLETE FOR {self.run_id} in {total_time:.2f} seconds ---")
                return True
                
            else:
                logger.info(f"Run {self.run_id} is in stage {current_stage}. No action taken.")
                return True
                
        except Exception as e:
            logger.error(f"Workflow encountered an unrecoverable error: {str(e)}")
            self.state_machine.fail(str(e))
            return False
