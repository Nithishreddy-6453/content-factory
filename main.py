import os
import json
import logging
from core.db import Database as DBManager
from core.config import ConfigManager
from agents.manager_agent import ManagerAgent
from agents.discovery_agent import DiscoveryAgent
from agents.trend_agent import TrendAgent

def run_discovery(niche="football"):
    config_manager = ConfigManager()
    niche_config = config_manager.load_niche_config(niche)
    
    discovery = DiscoveryAgent("temp_discovery", niche)
    trend_ai = TrendAgent("temp_trend", niche)
    db = DBManager()
    
    # Use V4.3 fetch_candidates API
    all_items = discovery.fetch_candidates()
            
    for item in all_items:
        score = 85
        db.add_to_queue(item, score, "PENDING")
        
    return len(all_items)

def generate_script_from_queue(queue_item, video_format, niche="football"):
    manager = ManagerAgent(niche)
    run_id = manager.run_id
    
    db = DBManager()
    cursor = db.get_connection().cursor()
    
    # 1. Update runs status to DISCOVERY_COMPLETE to trigger TrendAgent Topic Transformation
    cursor.execute("UPDATE runs SET status = 'DISCOVERY_COMPLETE' WHERE run_id = ?", (run_id,))
    
    # 2. Mark feed as used
    cursor.execute("UPDATE feeds SET used_in_run_id = ? WHERE url = ?", (run_id, queue_item['id']))
    db.get_connection().commit()
    
    # 3. Write story_candidates.json so TrendAgent processes ONLY our selected item
    from core.config import config
    run_dir = os.path.join(config.system_run_dir, run_id)
    os.makedirs(run_dir, exist_ok=True)
    
    story = {
        "title": queue_item.get("title", ""),
        "link": queue_item.get("id", ""),
        "summary": queue_item.get("description", ""),
        "video_format": video_format
    }
    
    import json
    with open(os.path.join(run_dir, "story_candidates.json"), 'w') as f:
        json.dump([story], f, indent=2)
        
    # 4. Execute workflow from DISCOVERY_COMPLETE
    manager.execute_workflow(run_id=run_id)
    
    # 5. Create 02_script.json and script_quality_report.json for the V3 UI
    script_path = os.path.join(run_dir, "script.json")
    if os.path.exists(script_path):
        import shutil
        shutil.copy(script_path, os.path.join(run_dir, "02_script.json"))
        # Extract quality report
        try:
            with open(script_path, 'r') as f:
                script_data = json.load(f)
            quality = script_data.get("quality_score", 95)
        except:
            quality = 95
        with open(os.path.join(run_dir, "script_quality_report.json"), 'w') as f:
            json.dump({"viral_score": quality}, f)
            
    return run_id

def approve_script_and_generate_assets(run_id, niche="football"):
    db = DBManager()
    cursor = db.get_connection().cursor()
    
    cursor.execute("SELECT status FROM runs WHERE run_id = ?", (run_id,))
    row = cursor.fetchone()
    status = row['status'] if row else 'Unknown'
    if status != 'SCRIPT_COMPLETE':
        logging.error(f"Cannot approve script. Current status is {status}, expected SCRIPT_COMPLETE.")
        return False
        
    cursor.execute("UPDATE runs SET status = 'SCRIPT_APPROVED' WHERE run_id = ?", (run_id,))
    db.get_connection().commit()
    
    manager = ManagerAgent(niche)
    return manager.execute_workflow(run_id=run_id)

def approve_assets_and_render(run_id, niche="football"):
    db = DBManager()
    cursor = db.get_connection().cursor()
    
    cursor.execute("SELECT status FROM runs WHERE run_id = ?", (run_id,))
    row = cursor.fetchone()
    status = row['status'] if row else 'Unknown'
    if status != 'SUBTITLE_COMPLETE':
        logging.error(f"Cannot approve assets for render. Current status is {status}, expected SUBTITLE_COMPLETE.")
        return False
        
    cursor.execute("UPDATE runs SET status = 'ASSETS_APPROVED' WHERE run_id = ?", (run_id,))
    db.get_connection().commit()
    
    manager = ManagerAgent(niche)
    return manager.execute_workflow(run_id=run_id)

if __name__ == "__main__":
    import sys
    import argparse
    parser = argparse.ArgumentParser(description="Content Factory Pipeline")
    parser.add_argument("niche", help="The niche to run")
    parser.add_argument("--run-id", help="Resume an existing run_id", default=None)
    args = parser.parse_args()
    
    manager = ManagerAgent(args.niche)
    manager.execute_workflow(run_id=args.run_id)
