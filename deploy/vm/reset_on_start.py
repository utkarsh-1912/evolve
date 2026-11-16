"""One-shot demo reset for deployed stacks (VM `reset` service; also usable against Render).

Reseeds V1-V5 (POST /api/demo/reset) and pre-stages V3 so its locked records exist. SIMULATED, synthetic data.
Stdlib only.  Usage: python reset_on_start.py https://api.example.org
"""
import json
import sys
import time
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")


def call(path, body=None, token=None):
    req = urllib.request.Request(BASE + path, data=json.dumps(body or {}).encode(), method="POST",
                                 headers={"content-type": "application/json",
                                          **({"authorization": "Bearer " + token} if token else {})})
    with urllib.request.urlopen(req, timeout=90) as r:  # long timeout: a sleeping free instance wakes slowly
        return json.loads(r.read().decode())


for attempt in range(10):
    try:
        print("reset:", call("/api/demo/reset"))
        break
    except OSError as e:
        print("waiting for backend:", e)
        time.sleep(6)
else:
    sys.exit(1)

token = call("/api/session", {"partner_id": "V3A"})["token"]
call("/api/consents", {"counterpart": "V3B"}, token)
call("/api/demo/simulate-partner-consent", {"couple_id": "V3"})
res = call("/api/couples/V3/compatibility", {}, token)
print("staged V3 (SIMULATED partner consent): compatible =", res["apsi"]["compatible"])
