"""
Smoke test — verifies that all endpoints of the Flask RAG app respond correctly.
Usage:  python scripts/smoke_test.py [BASE_URL]
Default BASE_URL is http://localhost:5000
"""

import sys
import json
import urllib.request
import urllib.error

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
PASS = 0
FAIL = 0


def test(name, method, path, body=None, expect_status=200, check=None):
    global PASS, FAIL
    url = BASE + path
    headers = {"Content-Type": "application/json"} if body else {}
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        resp = urllib.request.urlopen(req)
        status = resp.status
        result = json.loads(resp.read().decode()) if resp.headers.get("Content-Type", "").startswith("application/json") else resp.read().decode()
    except urllib.error.HTTPError as e:
        status = e.code
        result = json.loads(e.read().decode()) if "json" in e.headers.get("Content-Type", "") else e.read().decode()

    ok = status == expect_status
    if ok and check:
        ok = check(result)

    tag = "PASS" if ok else "FAIL"
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print(f"  [{tag}] {name}  (HTTP {status})")
    if not ok:
        print(f"         Response: {str(result)[:200]}")


print(f"\nSmoke testing {BASE}\n{'='*50}")

# 1) Health
test("GET /health", "GET", "/health",
     check=lambda r: r.get("status") == "ok")

# 2) Home page
test("GET / (HTML)", "GET", "/", expect_status=200,
     check=lambda r: "South Park" in r if isinstance(r, str) else True)

# 3) Ask — valid question (English)
test("POST /api/ask (English)", "POST", "/api/ask",
     body={"question": "Who is Cartman?"},
     check=lambda r: r.get("answer") and len(r["answer"]) > 20)

# 4) Ask — valid question (Hebrew)
test("POST /api/ask (Hebrew)", "POST", "/api/ask",
     body={"question": "מי יצר את סאות פארק?"},
     check=lambda r: r.get("answer") and len(r["answer"]) > 10)

# 5) Ask — empty question → 400
test("POST /api/ask (empty → 400)", "POST", "/api/ask",
     body={"question": ""},
     expect_status=400,
     check=lambda r: r.get("error"))

# 6) Ask — missing body → 400
test("POST /api/ask (no body → 400)", "POST", "/api/ask",
     body={},
     expect_status=400)

print(f"\n{'='*50}")
print(f"Results: {PASS} passed, {FAIL} failed out of {PASS+FAIL}")
sys.exit(1 if FAIL else 0)
