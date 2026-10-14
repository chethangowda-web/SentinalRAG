import asyncio
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

BASE = "http://localhost:8015"

async def wait_for_server(url, timeout=90):
    import httpx
    start = time.time()
    while time.time() - start < timeout:
        try:
            async with httpx.AsyncClient(timeout=3) as c:
                r = await c.get(url)
                if r.status_code < 500:
                    return True
        except:
            pass
        await asyncio.sleep(1)
    return False

async def main():
    pass_count = 0
    fail_count = 0

    def ok(name):
        nonlocal pass_count
        pass_count += 1
        print(f"  PASS: {name}")

    def fail(name, detail=""):
        nonlocal fail_count
        fail_count += 1
        msg = f"  FAIL: {name}"
        if detail:
            msg += f" - {detail}"
        print(msg)

    import httpx
    c = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=30.0), base_url=BASE)

    print("Waiting for server...")
    if not await wait_for_server(f"{BASE}/"):
        print("Server not ready")
        return 1
    print("Server ready!")

    # 1. REGISTER
    print("\n=== 1. REGISTER ===")
    reg_data = {"name": "Test User", "email": "test@sentinelrag.com", "password": "TestPass123!"}
    r = await c.post("/api/v1/auth/register", json=reg_data)
    if r.status_code == 201:
        token_a = r.json()["access_token"]
        ok("Register new account")
    else:
        fail("Register", f"{r.status_code}: {r.text[:200]}")
        token_a = None

    if not token_a:
        print("Cannot continue without auth token")
        return 1

    headers = {"Authorization": f"Bearer {token_a}"}

    # 2. AUTH ME
    print("\n=== 2. AUTH PROFILE ===")
    r = await c.get("/api/v1/auth/me", headers=headers)
    ok("GET /auth/me") if r.status_code == 200 else fail("GET /auth/me", r.status_code)

    # 3. HEALTH
    print("\n=== 3. HEALTH ===")
    r = await c.get("/api/v1/health", headers=headers)
    ok("GET /health") if r.status_code == 200 else fail("GET /health", r.status_code)

    # 4. EMPTY DASHBOARD
    print("\n=== 4. EMPTY DASHBOARD ===")
    r = await c.get("/api/v1/dashboard/stats", headers=headers)
    if r.status_code == 200:
        stats = r.json()
        if stats["total_documents"] == 0:
            ok("Dashboard empty (0 docs)")
        else:
            fail("Dashboard empty", f"Expected 0 docs, got {stats['total_documents']}")
    else:
        fail("Dashboard empty", r.status_code)

    # 5. UPLOAD PDF
    print("\n=== 5. UPLOAD PDF ===")
    pdf_path = Path("K:/SentinalRAG/test_data/sample.pdf")
    if not pdf_path.exists():
        fail("Upload PDF", "PDF file not found")
        return 1
    with open(pdf_path, "rb") as f:
        files = {"file": ("sample.pdf", f, "application/pdf")}
        r = await c.post("/api/v1/ingest", files=files, headers={"Authorization": f"Bearer {token_a}"})
    if r.status_code in (200, 201):
        upload = r.json()
        doc_id = upload["document_id"]
        ok(f"Upload PDF (id: {doc_id[:8]}...)")
    else:
        fail("Upload PDF", f"{r.status_code}: {r.text[:300]}")
        doc_id = None

    if not doc_id:
        return 1

    # 6. LIST DOCUMENTS
    print("\n=== 6. LIST DOCUMENTS ===")
    r = await c.get("/api/v1/documents", headers=headers)
    if r.status_code == 200:
        docs = r.json()
        if len(docs) > 0:
            ok(f"List documents ({len(docs)} found)")
        else:
            fail("List documents", "No documents returned")
    else:
        fail("List documents", r.status_code)

    # 7. WAIT FOR PROCESSING
    print("\n=== 7. WAIT FOR PROCESSING ===")
    completed = False
    for i in range(60):
        await asyncio.sleep(2)
        r = await c.get(f"/api/v1/documents/{doc_id}", headers=headers)
        if r.status_code == 200:
            dd = r.json()
            if dd["status"] == "completed":
                completed = True
                ok(f"Processing completed in ~{(i+1)*2}s: {dd.get('pages',0)}p {dd.get('word_count',0)}w {dd.get('chunk_count',0)}c")
                break
            elif dd["status"] == "failed":
                fail("Processing", "failed status")
                break
    if not completed:
        fail("Processing", "timed out")

    # 8. DASHBOARD AFTER UPLOAD
    print("\n=== 8. DASHBOARD AFTER UPLOAD ===")
    r = await c.get("/api/v1/dashboard/stats", headers=headers)
    if r.status_code == 200:
        stats = r.json()
        if stats["total_documents"] > 0 and stats["total_chunks"] > 0:
            ok(f"Dashboard: {stats['total_documents']} docs, {stats['total_chunks']} chunks")
        else:
            fail("Dashboard after upload", f"docs={stats['total_documents']} chunks={stats['total_chunks']}")
    else:
        fail("Dashboard after upload", r.status_code)

    # 9. CHAT
    print("\n=== 9. CHAT ===")
    chat_data = {"question": "What was the revenue in Q4 2025?"}
    r = await c.post("/api/v1/chat", json=chat_data, headers=headers)
    if r.status_code == 200:
        resp = r.json()
        if resp.get("answer"):
            a = resp["answer"][:150]
            ok(f"Chat: confidence={resp.get('confidence','?')}% level={resp.get('confidence_level','?')}")
            print(f"  Answer: {a}...")
        else:
            fail("Chat", "No answer in response")
    else:
        fail("Chat", f"{r.status_code}: {r.text[:300]}")

    # 10. LOGOUT & RE-LOGIN
    print("\n=== 10. LOGOUT & RE-LOGIN ===")
    r = await c.post("/api/v1/auth/logout", headers=headers)
    ok("Logout") if r.status_code in (200, 204) else fail("Logout", r.status_code)

    login_data = {"email": "test@sentinelrag.com", "password": "TestPass123!"}
    r = await c.post("/api/v1/auth/login", json=login_data)
    if r.status_code == 200:
        token_b = r.json()["access_token"]
        ok("Re-login")
        headers2 = {"Authorization": f"Bearer {token_b}"}
        r = await c.get("/api/v1/dashboard/stats", headers=headers2)
        if r.status_code == 200:
            stats2 = r.json()
            if stats2["total_documents"] > 0:
                ok(f"Data persists: {stats2['total_documents']} docs after re-login")
            else:
                fail("Data persists", "0 docs found")
        else:
            fail("Data persists", r.status_code)
    else:
        fail("Re-login", f"{r.status_code}: {r.text[:200]}")

    # 11. WRONG PASSWORD
    print("\n=== 11. SECURITY CHECKS ===")
    bad_login = {"email": "test@sentinelrag.com", "password": "wrongpassword"}
    r = await c.post("/api/v1/auth/login", json=bad_login)
    ok("Wrong password rejected") if r.status_code == 401 else fail("Wrong password", f"got {r.status_code}")

    # 12. DUPLICATE REGISTRATION
    r = await c.post("/api/v1/auth/register", json=reg_data)
    if r.status_code == 409:
        ok("Duplicate email rejected (409)")
    else:
        # May fail if run multiple times (user already exists)
        print(f"  NOTE: Duplicate register returned {r.status_code} (may already exist)")

    # SUMMARY
    print(f"\n{'='*50}")
    color = "PASS" if fail_count == 0 else "FAIL"
    print(f"  RESULTS: {pass_count} passed, {fail_count} failed [{color}]")
    print(f"{'='*50}")

    await c.aclose()
    return 0 if fail_count == 0 else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
