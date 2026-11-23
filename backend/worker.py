import os, time, json
from datetime import datetime, timezone
from src.db import init_db

init_db()
os.makedirs('/shared', exist_ok=True)
while True:
    payload = {"service":"renewal-analysis-worker", "at":datetime.now(timezone.utc).isoformat(), "queue":"renewal-review"}
    with open('/shared/worker.heartbeat','w') as fh:
        json.dump(payload, fh)
    time.sleep(5)
