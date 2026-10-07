import sys
import logging
sys.path.append(r'c:\Users\palak\.gemini\antigravity\scratch\content_factory')
from core.db import Database
from agents.manager_agent import ManagerAgent

logging.basicConfig(level=logging.INFO)

db = Database()
c = db.get_connection().cursor()
c.execute("UPDATE runs SET status = 'SCENE_PLAN_COMPLETE' WHERE run_id = 'run_2026_10_07_10_09_35'")
db.get_connection().commit()

print('Testing visual agent failure directly from SCENE_PLAN_COMPLETE...')
manager = ManagerAgent('football')
manager.execute_workflow(run_id='run_2026_10_07_10_09_35')

c.execute("SELECT status FROM runs WHERE run_id = 'run_2026_10_07_10_09_35'")
status = c.fetchone()['status']
print(f'DB status after test: {status}')
