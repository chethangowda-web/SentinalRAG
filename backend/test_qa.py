import httpx, asyncio

async def t():
    c = httpx.AsyncClient(base_url="https://sentinalrag-production.up.railway.app", timeout=180)
    r = await c.post("/api/v1/auth/login", json={"email":"qa@test.com","password":"Test123!"})
    if r.status_code != 200:
        r = await c.post("/api/v1/auth/register", json={"name":"QA User","email":"qa@test.com","password":"Test123!"})
    tok = r.json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}

    r = await c.get("/api/v1/documents", headers=h)
    docs = r.json()
    print(f"{len(docs)} docs:")
    for d in docs:
        print(f'  [{d["status"]}] {d["filename"]} - {d.get("pages",0)}p, content={d.get("word_count",0)}w, chunks={d.get("chunk_count",0)}')
        print(f'  summary: {str(d.get("summary",""))[:200]}')

    r = await c.get("/api/v1/dashboard/stats", headers=h)
    s = r.json()
    print(f"\nDashboard: docs={s['total_documents']} chunks={s['total_chunks']} chars={s['total_chars']} words={s['total_words']} pages={s['total_pages']}")

    # Test RAG with a question that matches the PDF content
    print("\n=== RAG CHAT TEST ===")
    for q in ["What was the revenue in Q4 2025?", "What is the document about?", "Summarize the quarterly results"]:
        r = await c.post("/api/v1/chat", json={"question": q}, headers=h)
        if r.status_code == 200:
            resp = r.json()
            print(f"Q: {q}")
            print(f"A: {resp.get('answer','')[:250]}")
            print(f"   confidence={resp.get('confidence','?')} level={resp.get('confidence_level','?')}")
            print(f"   sources={len(resp.get('sources',[]))}")
        else:
            print(f"Q: {q} -> {r.status_code}: {r.text[:100]}")
        print()

    await c.aclose()

asyncio.run(t())
