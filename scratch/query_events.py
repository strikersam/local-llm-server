import sqlite3
import json

db_path = ".data/workflow/workflow.db"
run_id = "wf_8d26a12c54c9e233"

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT * FROM workflow_events WHERE run_id = ? ORDER BY position", (run_id,)).fetchall()

for r in rows:
    print(f"[{r['timestamp']}] {r['event_type']}")
    print(json.dumps(json.loads(r['payload']), indent=2))
    print("-" * 40)
