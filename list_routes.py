import sys
sys.path.insert(0, r"K:\SentinalRAG\backend")
import logging
logging.disable(logging.CRITICAL)
from app.main import app
for r in app.routes:
    if hasattr(r, "methods") and r.path.startswith("/api"):
        sys.stdout.write(f"{sorted(r.methods)} {r.path}\n")
sys.stdout.flush()
