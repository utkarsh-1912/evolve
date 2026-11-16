"""`python -m evolve_api` (run from services/api, or with services/api on sys.path).
Binds HOST (default 0.0.0.0) and PORT (default 8000; Render and similar hosts set PORT)."""
import os

import uvicorn

from .main import app

if __name__ == "__main__":
    uvicorn.run(app, host=os.environ.get("HOST", "0.0.0.0"), port=int(os.environ.get("PORT", "8000")),
                proxy_headers=True, forwarded_allow_ips="*")
