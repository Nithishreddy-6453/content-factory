import urllib.request
import urllib.error
import json
import os
import sqlite3

def run_diagnostics():
    status = {
        "sqlite": False,
        "ollama": False,
        "available_models": [],
        "comfyui": False
    }
    
    # Check SQLite
    try:
        # Just check if we can connect to a generic database path, 
        # or since the prompt doesn't strictly dictate which DB to check, we can check core/state.db
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'core', 'state.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        cursor.fetchall()
        conn.close()
        status["sqlite"] = True
    except Exception as e:
        status["sqlite"] = False
        
    # Check Ollama
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=3) as response:
            if response.getcode() == 200:
                status["ollama"] = True
                data = json.loads(response.read().decode())
                status["available_models"] = [m.get("name") for m in data.get("models", [])]
    except Exception as e:
        status["ollama"] = False
        status["available_models"] = []
        
    # Check ComfyUI
    try:
        req = urllib.request.Request("http://localhost:8188/system_stats")
        with urllib.request.urlopen(req, timeout=3) as response:
            if response.getcode() == 200:
                status["comfyui"] = True
    except Exception as e:
        status["comfyui"] = False
        
    return status
