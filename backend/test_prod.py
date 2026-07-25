import asyncio
import sys
from pathlib import Path

BASE = "https://sentinalrag-production.up.railway.app"

pass_count = 0
fail_count = 0

def ok(name):
    global pass_count
    pass_count += 1
    print(f"  PASS: {name}")

def fail(name, detail=""):
    global fail_count
    fail_count += 1
    msg = f"  FAIL: {name}"
    if detail:
        msg += f" - {detail}"
    print(msg)

async def main():
    global pass_count, fail_count
    import httpx
    c = httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=30.0), base_url=BASE)

    # 0. HEALTH (no auth)
    print("\n=== 0. HEALTH ===")
    r = await c.get("/api/v1/health")
    ok("Health check") if r.status_code == 200 else fail("Health check", str(r.status_code))

    # 1. REGISTER
    print("\n=== 1. REGISTER ===")
    uniq = f"test{asyncio.get_event_loop().time()}".replace(".", "")
    reg_data = {"name": "E2E Test", "email": f"{uniq}@test.com", "password": "TestPass123!"}
    r = await c.post("/api/v1/auth/register", json=reg_data)
    if r.status_code == 201:
        token = r.json()["access_token"]
        ok("Register")
    else:
        fail("Register", f"{r.status_code}: {r.text[:200]}")
        return 1

    headers = {"Authorization": f"Bearer {token}"}

    # 2. AUTH ME
    print("\n=== 2. AUTH ME ===")
    r = await c.get("/api/v1/auth/me", headers=headers)
    ok("GET /auth/me") if r.status_code == 200 else fail("GET /auth/me", str(r.status_code))

    # 3. EMPTY DASHBOARD
    print("\n=== 3. EMPTY DASHBOARD ===")
    r = await c.get("/api/v1/dashboard/stats", headers=headers)
    if r.status_code == 200:
        stats = r.json()
        ok(f"Dashboard stats: {stats['total_documents']} docs, {stats['total_chunks']} chunks")
    else:
        fail("Dashboard stats", str(r.status_code))

    # 4. LIST DOCUMENTS (empty)
    print("\n=== 4. LIST DOCUMENTS (empty) ===")
    r = await c.get("/api/v1/documents", headers=headers)
    ok("List documents") if r.status_code == 200 else fail("List documents", str(r.status_code))

    # 5. UPLOAD PDF
    print("\n=== 5. UPLOAD PDF ===")
    pdf_path = Path("K:/SentinalRAG/test_data/sample.pdf")
    if not pdf_path.exists():
        # Create a minimal PDF
        from io import BytesIO
        pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj\n4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n5 0 obj<</Length 44>>stream\nBT /F1 12 Tf 100 700 Td (Hello World - Test Document) Tj ET\nendstream\nendobj\nxref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000266 00000 n \n0000000344 00000 n \ntrailer<</Size 6/Root 1 0 R>>\nstartxref\n435\n%%EOF"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        with open(pdf_path, "wb") as f:
            f.write(pdf_content)

    with open(pdf_path, "rb") as f:
        files = {"file": ("sample.pdf", f, "application/pdf")}
        r = await c.post("/api/v1/ingest", files=files, headers=headers)
    if r.status_code in (200, 201):
        upload = r.json()
        doc_id = upload["document_id"]
        ok(f"Upload PDF: doc_id={doc_id[:12]}... status={upload.get('status','?')}")
    else:
        fail("Upload PDF", f"{r.status_code}: {r.text[:300]}")
        return 1

    # 6. LIST DOCUMENTS (after upload)
    print("\n=== 6. LIST DOCUMENTS (after upload) ===")
    r = await c.get("/api/v1/documents", headers=headers)
    if r.status_code == 200:
        docs = r.json()
        ok(f"List documents: {len(docs)} found")
        for d in docs:
            print(f"      [{d['status']}] {d['filename']} - {d.get('pages',0)}p, {d.get('word_count',0)}w")
    else:
        fail("List documents", str(r.status_code))

    # 7. WAIT FOR PROCESSING (poll)
    print("\n=== 7. WAIT FOR PROCESSING ===")
    completed = False
    for i in range(90):
        await asyncio.sleep(2)
        r = await c.get(f"/api/v1/documents/{doc_id}", headers=headers)
        if r.status_code == 200:
            dd = r.json()
            status = dd["status"]
            print(f"      attempt {i+1}: status={status}", end="\r")
            if             status in ("completed", "processed", "embedded"):
                completed = True
                print(f"\n      Completed: {dd.get('pages',0)}p, {dd.get('word_count',0)}w, {dd.get('chunk_count',0)}c, {dd.get('summary','')[:80]}...")
                ok("Processing completed")
                break
            elif status == "failed":
                fail("Processing", f"failed: {dd.get('error','')}")
                break
    if not completed:
        fail("Processing", f"timed out after 180s, last status: {dd.get('status','?')}")

    # 8. DASHBOARD AFTER
    print("\n=== 8. DASHBOARD AFTER ===")
    r = await c.get("/api/v1/dashboard/stats", headers=headers)
    if r.status_code == 200:
        stats = r.json()
        ok(f"Dashboard: {stats['total_documents']} docs, {stats['total_chunks']} chunks")
    else:
        fail("Dashboard", str(r.status_code))

    # 9. DAILY STATS
    print("\n=== 9. DAILY STATS ===")
    r = await c.get("/api/v1/dashboard/daily-stats", headers=headers)
    ok("Daily stats") if r.status_code == 200 else fail("Daily stats", str(r.status_code))

    # 10. EMBED THE DOCUMENT
    print("\n=== 10. EMBED DOCUMENT ===")
    r = await c.post(f"/api/v1/embed/{doc_id}", headers=headers)
    if r.status_code == 200:
        emb = r.json()
        ok(f"Embed: status={emb.get('status','?')} chunks={emb.get('embedded_chunks',0)}")
    else:
        fail("Embed", f"{r.status_code}: {r.text[:200]}")

    # 11. DASHBOARD AFTER EMBED
    print("\n=== 11. DASHBOARD AFTER EMBED ===")
    r = await c.get("/api/v1/dashboard/stats", headers=headers)
    if r.status_code == 200:
        stats = r.json()
        ok(f"Dashboard: {stats['total_documents']} docs, {stats['total_chunks']} chunks")
    else:
        fail("Dashboard", str(r.status_code))

    # 12. CHAT
    print("\n=== 12. CHAT ===")
    chat_data = {"question": "What is this document about?"}
    r = await c.post("/api/v1/chat", json=chat_data, headers=headers)
    if r.status_code == 200:
        resp = r.json()
        if resp.get("answer"):
            ok(f"Chat: confidence={resp.get('confidence','?')} level={resp.get('confidence_level','?')}")
            print(f"      Answer: {resp['answer'][:200]}")
        else:
            fail("Chat", "No answer in response")
    else:
        fail("Chat", f"{r.status_code}: {r.text[:300]}")

    # 13. LOGOUT
    print("\n=== 13. LOGOUT ===")
    r = await c.post("/api/v1/auth/logout", headers=headers)
    ok("Logout") if r.status_code in (200, 204) else fail("Logout", str(r.status_code))

    # 14. RE-LOGIN
    print("\n=== 14. RE-LOGIN ===")
    r = await c.post("/api/v1/auth/login", json=reg_data)
    if r.status_code == 200:
        token2 = r.json()["access_token"]
        ok("Re-login")
        # Verify data persists
        headers2 = {"Authorization": f"Bearer {token2}"}
        r = await c.get("/api/v1/dashboard/stats", headers=headers2)
        if r.status_code == 200:
            stats = r.json()
            if stats["total_documents"] > 0:
                ok(f"Data persists: {stats['total_documents']} docs after re-login")
            else:
                fail("Data persists", "0 docs found")
        else:
            fail("Data persists", str(r.status_code))
    else:
        fail("Re-login", f"{r.status_code}: {r.text[:200]}")

    # 15. WRONG PASSWORD
    print("\n=== 15. SECURITY: WRONG PASSWORD ===")
    r = await c.post("/api/v1/auth/login", json={"email": reg_data["email"], "password": "wrong"})
    ok("Wrong password rejected (401)") if r.status_code == 401 else fail("Wrong password", str(r.status_code))

    # 16. NO AUTH
    print("\n=== 16. SECURITY: NO AUTH ===")
    r = await c.get("/api/v1/documents")
    ok("No auth rejected") if r.status_code == 403 else fail("No auth", str(r.status_code))

    # SUMMARY
    print(f"\n{'='*50}")
    status = "ALL PASS" if fail_count == 0 else f"{fail_count} FAILED"
    print(f"  RESULTS: {pass_count} passed, {fail_count} failed [{status}]")
    print(f"{'='*50}")

    await c.aclose()
    return 0 if fail_count == 0 else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
