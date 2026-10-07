import sys
import logging
sys.path.append(r'c:\Users\palak\.gemini\antigravity\scratch\content_factory')
from core.db import Database
from agents.visual_agent import VisualAgent

logging.basicConfig(level=logging.INFO)

print('Testing visual agent failure directly...')
agent = VisualAgent('run_2026_10_07_10_09_35', 'football')
try:
    success = agent.execute()
    print(f'VisualAgent.execute returned {success}')
except Exception as e:
    print(f'Exception: {e}')
