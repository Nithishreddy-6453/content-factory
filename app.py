import streamlit as st
import json
import os
import sys
import sqlite3
import shutil

# Ensure core imports work
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from core.db import Database as DBManager
from core.config import ConfigManager
from agents.manager_agent import ManagerAgent
from agents.discovery_agent import DiscoveryAgent

st.set_page_config(page_title="Content Factory V3 Dashboard", layout="wide")

db = DBManager()
config_manager = ConfigManager()


st.sidebar.title("Navigation")
page = st.sidebar.radio("Workflow Stages", [
    "1. Home Dashboard", 
    "2. Story Queue", 
    "3. Prompt Inspector", 
    "4. Asset Preview", 
    "5. Runs & Cleanup", 
    "6. Learning Engine", 
    "Settings"
])

def load_json(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

if page == "1. Home Dashboard":
    st.title("Content Factory V3 - System Dashboard")
    st.write("Welcome to the Growth-First Autonomous Football Media System.")
    
    col1, col2, col3 = st.columns(3)
    
    q = db.get_queue()
    pending = db.get_pending_runs()
    assets_pending = db.get_asset_pending_runs()
    
    col1.metric("Stories in Queue", len(q))
    col2.metric("Scripts Pending Approval", len(pending))
    col3.metric("Assets Pending Preview", len(assets_pending))
    
    st.subheader("Recent Video Performance")
    videos = db.get_all_performance()
    if videos:
        st.dataframe(videos[:5])
    else:
        st.info("No video performance data yet.")

elif page == "2. Story Queue":
    st.title("Story Queue")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Gather News & Analyze Trends"):
            with st.spinner("Gathering news..."):
                from main import run_discovery
                count = run_discovery("football")
                if count and count > 0:
                    st.success(f"{count} stories gathered.")
                else:
                    st.success("No stories found.")
    
    queue_items = db.get_queue()
    if not queue_items:
        st.info("Queue is empty.")
    else:
        for item in queue_items:
            with st.expander(f"{item['title']} (Score: {item.get('trend_score', 0)})"):
                st.write(item.get('description', ''))
                
                video_format = st.selectbox("Format", ["Shorts (9:16)", "Longform (16:9)"], key=f"fmt_{item['id']}")
                
                if st.button("Generate Script", key=f"gen_{item['id']}"):
                    with st.spinner("Generating script..."):
                        from main import generate_script_from_queue
                        run_id = generate_script_from_queue(item, video_format, "football")
                        st.success(f"Script generated! Run ID: {run_id}")

elif page == "3. Prompt Inspector":
    st.title("Prompt Inspector (Script Review)")
    
    pending = db.get_pending_runs()
    if not pending:
        st.info("No scripts pending approval.")
    else:
        for run in pending:
            run_id = run['run_id']
            st.subheader(f"Run: {run_id}")
            
            script_path = os.path.join(config_manager.system_run_dir, run_id, "02_script.json")
            if os.path.exists(script_path):
                script_data = load_json(script_path)
                st.json(script_data)
                
                score_data = load_json(os.path.join(config_manager.system_run_dir, run_id, "script_quality_report.json"))
                viral_score = score_data.get("viral_score", 0)
                if isinstance(viral_score, dict):
                    viral_score = viral_score.get("score", 0)
                st.metric("Viral Score", viral_score)
                
                if st.button("Approve Script & Generate Assets", key=f"app_{run_id}"):
                    with st.spinner("Generating assets..."):
                        from main import approve_script_and_generate_assets
                        success = approve_script_and_generate_assets(run_id, "football")
                        if success:
                            st.success("Assets generated!")
                        else:
                            st.error("Asset generation failed. Check logs.")

elif page == "4. Asset Preview":
    st.title("Asset Preview")
    
    pending = db.get_asset_pending_runs()
    if not pending:
        st.info("No assets pending preview.")
    else:
        for run in pending:
            run_id = run['run_id']
            st.subheader(f"Run: {run_id}")
            
            images_dir = os.path.join(config_manager.system_run_dir, run_id, "images")
            if os.path.exists(images_dir):
                images = [f for f in os.listdir(images_dir) if f.endswith(".png")]
                if images:
                    cols = st.columns(min(len(images), 3) or 1)
                    for i, img in enumerate(images):
                        cols[i % 3].image(os.path.join(images_dir, img), caption=img, use_container_width=True)
            
            if st.button("Approve Assets & Render Video", key=f"rend_{run_id}"):
                with st.spinner("Rendering video..."):
                    from main import approve_assets_and_render
                    approve_assets_and_render(run_id, "football")
                    st.success("Video rendered!")

elif page == "5. Runs & Cleanup":
    st.title("Runs & Cleanup")
    
    runs = os.listdir(config_manager.system_run_dir)
    for run in runs:
        st.write(run)
        if st.button("Delete", key=f"del_{run}"):
            shutil.rmtree(os.path.join(config_manager.system_run_dir, run))
            st.success("Deleted!")

elif page == "6. Learning Engine":
    st.title("Learning Engine")
    
    analysis_path = "configs/learning_analysis.json"
    analysis = load_json(analysis_path)
    
    if analysis.get("status") != "success":
        st.warning("Insufficient performance data or learning failed.")
    else:
        st.json(analysis)

elif page == "Settings":
    st.title("Settings")
    st.write("Configuration options...")
    config = config_manager.system_config
    st.json(config)
