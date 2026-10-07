import sys
sys.path.append(r'c:\Users\palak\.gemini\antigravity\scratch\content_factory')
from core.db import Database
from main import approve_script_and_generate_assets

db = Database()
c = db.get_connection().cursor()
c.execute("UPDATE runs SET status = 'SCENE_PLAN_COMPLETE' WHERE run_id = 'run_2026_10_07_10_09_35'")
db.get_connection().commit()

print('Testing visual agent failure...')
success = approve_script_and_generate_assets('run_2026_10_07_10_09_35', 'football')
print(f'approve_script_and_generate_assets returned {success}')

c.execute("SELECT status FROM runs WHERE run_id = 'run_2026_10_07_10_09_35'")
status = c.fetchone()['status']
print(f'DB status after test: {status}')
