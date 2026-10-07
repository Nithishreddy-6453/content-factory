import yaml
import os
from dataclasses import dataclass

@dataclass
class Config:
    system_run_dir: str
    system_log_dir: str
    system_asset_library_dir: str
    system_db_path: str
    llm_script_model: str
    llm_research_model: str
    llm_viral_model: str
    llm_scene_model: str
    audio_primary: str
    audio_fallback: str
    render_resolution: str
    max_concurrent_gpu_tasks: int

def load_config(path: str = "configs/config.yaml") -> Config:
    # If the file doesn't exist, try resolving relative to this script for testing
    if not os.path.exists(path):
        alt_path = os.path.join(os.path.dirname(__file__), '..', path)
        if os.path.exists(alt_path):
            path = alt_path
        else:
            raise FileNotFoundError(f"Config file not found at {path}")
            
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
        
    return Config(
        system_run_dir=data.get('system', {}).get('run_dir', 'runs'),
        system_log_dir=data.get('system', {}).get('log_dir', 'logs'),
        system_asset_library_dir=data.get('system', {}).get('asset_library_dir', 'asset_library'),
        system_db_path=data.get('system', {}).get('db_path', 'core/state.db'),
        llm_script_model=data.get('llm_routing', {}).get('script_generation_model', 'llama3:latest'),
        llm_research_model=data.get('llm_routing', {}).get('research_model', 'mistral:latest'),
        llm_viral_model=data.get('llm_routing', {}).get('viral_analysis_model', 'llama3:latest'),
        llm_scene_model=data.get('llm_routing', {}).get('scene_planning_model', 'llama3:latest'),
        audio_primary=data.get('audio', {}).get('primary_provider', 'kokoro'),
        audio_fallback=data.get('audio', {}).get('fallback_provider', 'edge-tts'),
        render_resolution=data.get('render', {}).get('resolution', '1080x1920'),
        max_concurrent_gpu_tasks=data.get('render', {}).get('max_concurrent_gpu_tasks', 1)
    )

config = load_config()


import json

class ConfigManager:
    def __init__(self, base_dir=None):
        self.base_dir = base_dir or os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        # Expose current V4.3 paths via historical interface
        self.system_run_dir = config.system_run_dir
        self.system_log_dir = config.system_log_dir
        self.system_db_path = config.system_db_path
        
        self.system_config_path = os.path.join(self.base_dir, "configs", "system_config.json")
        self.system_config = self._load_system_config()

    def _load_system_config(self):
        if not os.path.exists(self.system_config_path):
            os.makedirs(os.path.dirname(self.system_config_path), exist_ok=True)
            default_config = {
                "max_concurrent_gpu_tasks": config.max_concurrent_gpu_tasks,
                "retry_attempts": 3,
                "asset_library_enabled": True
            }
            with open(self.system_config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            return default_config
            
        with open(self.system_config_path, 'r') as f:
            return json.load(f)

    def load_niche_config(self, niche_name):
        niche_config_path = os.path.join(self.base_dir, "niches", niche_name, "config.json")
        if not os.path.exists(niche_config_path):
            raise FileNotFoundError(f"Configuration for niche '{niche_name}' not found at {niche_config_path}")
        with open(niche_config_path, 'r') as f:
            return json.load(f)
