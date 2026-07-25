import sys, logging
sys.path.insert(0, r"K:\SentinalRAG\backend")
logging.disable(logging.CRITICAL)

# Test importing the auth module
from app.api.v1.auth import router as auth_router
sys.stdout.write(f"Auth router routes: {len(auth_router.routes)}\n")
for r in auth_router.routes:
    sys.stdout.write(f"  path={r.path}\n")

# Test importing the main router
from app.api.v1.router import api_v1_router
sys.stdout.write(f"V1 router routes: {len(api_v1_router.routes)}\n")
for r in api_v1_router.routes:
    sys.stdout.write(f"  path={r.path}\n")
sys.stdout.flush()
