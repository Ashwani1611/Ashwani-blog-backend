"""
test_api.py — Full API test for Ashwani Blog Backend
Usage:
    python test_api.py                  # runs all tests against localhost:8000
    python test_api.py --url http://... # custom base URL
"""
import sys
import httpx
import json

BASE_URL = "http://localhost:8000"
for arg in sys.argv[1:]:
    if arg.startswith("--url="):
        BASE_URL = arg.split("=", 1)[1]

# ── Helpers ───────────────────────────────────────────────────

PASS  = "✅"
FAIL  = "❌"
SKIP  = "⚠️ "

passed = 0
failed = 0
token  = None
admin_token = None


def check(label: str, response: httpx.Response, expected_status: int, show_body: bool = False):
    global passed, failed
    ok = response.status_code == expected_status
    icon = PASS if ok else FAIL
    if ok:
        passed += 1
    else:
        failed += 1
    print(f"  {icon} [{response.status_code}] {label}")
    if not ok or show_body:
        try:
            body = response.json()
            print(f"      {json.dumps(body, indent=2)[:300]}")
        except Exception:
            print(f"      {response.text[:200]}")
    return response


def section(title: str):
    print(f"\n{'─'*50}")
    print(f"  {title}")
    print(f"{'─'*50}")


client = httpx.Client(base_url=BASE_URL, timeout=10)


# ── 1. Health ─────────────────────────────────────────────────
section("1. Health Checks")

check("GET /", client.get("/"), 200)
check("GET /health", client.get("/health"), 200)


# ── 2. Auth — Register ────────────────────────────────────────
section("2. Auth — Register")

r = check("POST /auth/register (new user)", client.post("/api/v1/auth/register", json={
    "username": "testuser",
    "email": "testuser@example.com",
    "password": "testpass123"
}), 201)

check("POST /auth/register (duplicate email)", client.post("/api/v1/auth/register", json={
    "username": "testuser2",
    "email": "testuser@example.com",
    "password": "testpass123"
}), 400)

check("POST /auth/register (duplicate username)", client.post("/api/v1/auth/register", json={
    "username": "testuser",
    "email": "other@example.com",
    "password": "testpass123"
}), 400)

check("POST /auth/register (short password)", client.post("/api/v1/auth/register", json={
    "username": "newuser",
    "email": "new@example.com",
    "password": "short"
}), 422)

check("POST /auth/register (invalid username chars)", client.post("/api/v1/auth/register", json={
    "username": "bad user!",
    "email": "bad@example.com",
    "password": "password123"
}), 422)


# ── 3. Auth — Login ───────────────────────────────────────────
section("3. Auth — Login")

r = check("POST /auth/login (valid)", client.post("/api/v1/auth/login", json={
    "email": "testuser@example.com",
    "password": "testpass123"
}), 200, show_body=True)

if r.status_code == 200:
    token = r.json()["access_token"]
    refresh_token = r.json()["refresh_token"]
    print(f"      → Got access token: {token[:30]}...")

check("POST /auth/login (wrong password)", client.post("/api/v1/auth/login", json={
    "email": "testuser@example.com",
    "password": "wrongpassword"
}), 401)

check("POST /auth/login (unknown email)", client.post("/api/v1/auth/login", json={
    "email": "nobody@example.com",
    "password": "testpass123"
}), 401)


# ── 4. Auth — /me and Refresh ─────────────────────────────────
section("4. Auth — /me and Token Refresh")

if token:
    check("GET /auth/me (authenticated)", client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    ), 200, show_body=True)

check("GET /auth/me (no token)", client.get("/api/v1/auth/me"), 401)

if token:
    r = check("POST /auth/refresh (valid)", client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token
    }), 200)
    if r.status_code == 200:
        print(f"      → New access token: {r.json()['access_token'][:30]}...")

check("POST /auth/refresh (garbage token)", client.post("/api/v1/auth/refresh", json={
    "refresh_token": "not.a.real.token"
}), 401)


# ── 5. Admin Login ────────────────────────────────────────────
section("5. Admin Login (requires seed.py --admin first)")

admin_email = input("\n  Enter admin email (or press Enter to skip admin tests): ").strip()
if admin_email:
    admin_password = input("  Enter admin password: ").strip()
    r = client.post("/api/v1/auth/login", json={
        "email": admin_email,
        "password": admin_password
    })
    if r.status_code == 200:
        admin_token = r.json()["access_token"]
        print(f"  {PASS} Admin login successful")
    else:
        print(f"  {FAIL} Admin login failed: {r.json()}")
else:
    print(f"  {SKIP} Skipping admin tests")


# ── 6. Posts — Public ─────────────────────────────────────────
section("6. Posts — Public Endpoints")

r = check("GET /posts/ (list all)", client.get("/api/v1/posts/"), 200, show_body=True)
slugs = []
if r.status_code == 200:
    posts = r.json()
    slugs = [p["slug"] for p in posts]
    print(f"      → Found {len(posts)} posts: {slugs}")

check("GET /posts/?cat=django (filter by category)", client.get("/api/v1/posts/?cat=django"), 200)
check("GET /posts/?search=N+1 (search)", client.get("/api/v1/posts/?search=N+1"), 200)
check("GET /posts/?cat=invalid (invalid category)", client.get("/api/v1/posts/?cat=invalid"), 200)  # returns empty list

if slugs:
    slug = slugs[0]
    check(f"GET /posts/{slug} (single post)", client.get(f"/api/v1/posts/{slug}"), 200, show_body=True)

check("GET /posts/nonexistent-slug (404)", client.get("/api/v1/posts/nonexistent-slug-xyz"), 404)


# ── 7. Posts — Admin CRUD ─────────────────────────────────────
section("7. Posts — Admin CRUD")

if admin_token:
    r = check("POST /posts/ (create, admin)", client.post(
        "/api/v1/posts/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "slug": "test-post-api",
            "title": "Test Post from API",
            "excerpt": "Testing the create endpoint.",
            "content": "Full content of the test post.",
            "cat": "python",
            "layout": "half",
            "tags": ["test", "api"],
            "toc": [{"title": "Intro", "anchor": "intro", "level": 2}],
            "read_time": "1 min read",
            "is_featured": False,
            "is_published": True,
        }
    ), 201, show_body=True)

    check("POST /posts/ (duplicate slug)", client.post(
        "/api/v1/posts/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "slug": "test-post-api",
            "title": "Duplicate",
            "excerpt": "...",
            "content": "...",
            "cat": "python",
        }
    ), 400)

    check("PATCH /posts/test-post-api (update)", client.patch(
        "/api/v1/posts/test-post-api",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"title": "Updated Test Post"}
    ), 200)

    check("POST /posts/ (non-admin token)", client.post(
        "/api/v1/posts/",
        headers={"Authorization": f"Bearer {token}"},
        json={"slug": "should-fail", "title": "...", "excerpt": "...", "content": "...", "cat": "python"}
    ), 403)

else:
    print(f"  {SKIP} Skipping admin CRUD (no admin token)")


# ── 8. Likes ──────────────────────────────────────────────────
section("8. Post Likes")

if slugs:
    slug = slugs[0]

    r = check(f"GET /posts/{slug}/like (status)", client.get(f"/api/v1/posts/{slug}/like"), 200, show_body=True)

    r = check(f"POST /posts/{slug}/like (toggle on)", client.post(f"/api/v1/posts/{slug}/like"), 200, show_body=True)
    if r.status_code == 200:
        print(f"      → liked={r.json()['liked']}, like_count={r.json()['like_count']}")

    r = check(f"POST /posts/{slug}/like (toggle off)", client.post(f"/api/v1/posts/{slug}/like"), 200, show_body=True)
    if r.status_code == 200:
        print(f"      → liked={r.json()['liked']}, like_count={r.json()['like_count']}")


# ── 9. Comments ───────────────────────────────────────────────
section("9. Comments")

comment_id = None
if slugs:
    slug = slugs[0]

    check(f"GET /posts/{slug}/comments (list)", client.get(f"/api/v1/posts/{slug}/comments"), 200)

    r = check(f"POST /posts/{slug}/comments (guest)", client.post(
        f"/api/v1/posts/{slug}/comments",
        json={
            "body": "Great post! Very helpful.",
            "guest_name": "TestReader",
            "guest_email": "reader@example.com"
        }
    ), 201, show_body=True)
    if r.status_code == 201:
        comment_id = r.json()["id"]
        print(f"      → Comment ID: {comment_id}")

    check(f"POST /posts/{slug}/comments (no guest_name)", client.post(
        f"/api/v1/posts/{slug}/comments",
        json={"body": "No name given"}
    ), 422)

    check(f"POST /posts/{slug}/comments (empty body)", client.post(
        f"/api/v1/posts/{slug}/comments",
        json={"body": "   ", "guest_name": "Reader"}
    ), 422)

    if token:
        r = check(f"POST /posts/{slug}/comments (authenticated)", client.post(
            f"/api/v1/posts/{slug}/comments",
            headers={"Authorization": f"Bearer {token}"},
            json={"body": "Logged-in user comment."}
        ), 201)
        if r.status_code == 201:
            print(f"      → display_name={r.json()['display_name']}")


# ── 10. Comment Likes ─────────────────────────────────────────
section("10. Comment Likes")

if comment_id:
    r = check(f"POST /comments/{comment_id}/like (toggle on)", client.post(
        f"/api/v1/comments/{comment_id}/like"
    ), 200, show_body=True)
    if r.status_code == 200:
        print(f"      → liked={r.json()['liked']}, like_count={r.json()['like_count']}")

    r = check(f"POST /comments/{comment_id}/like (toggle off)", client.post(
        f"/api/v1/comments/{comment_id}/like"
    ), 200, show_body=True)
    if r.status_code == 200:
        print(f"      → liked={r.json()['liked']}, like_count={r.json()['like_count']}")

    if admin_token:
        check(f"DELETE /comments/{comment_id} (admin)", client.delete(
            f"/api/v1/comments/{comment_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        ), 204)
    else:
        print(f"  {SKIP} Skipping comment delete (no admin token)")


# ── 11. Newsletter ────────────────────────────────────────────
section("11. Newsletter")

check("POST /newsletter/subscribe (new)", client.post(
    "/api/v1/newsletter/subscribe",
    json={"email": "subscriber@example.com"}
), 200, show_body=True)

check("POST /newsletter/subscribe (duplicate active)", client.post(
    "/api/v1/newsletter/subscribe",
    json={"email": "subscriber@example.com"}
), 400)

check("POST /newsletter/unsubscribe", client.post(
    "/api/v1/newsletter/unsubscribe",
    json={"email": "subscriber@example.com"}
), 200)

check("POST /newsletter/subscribe (re-subscribe)", client.post(
    "/api/v1/newsletter/subscribe",
    json={"email": "subscriber@example.com"}
), 200, show_body=True)

check("POST /newsletter/unsubscribe (unknown email)", client.post(
    "/api/v1/newsletter/unsubscribe",
    json={"email": "nobody@example.com"}
), 404)

if admin_token:
    check("GET /newsletter/subscribers (admin)", client.get(
        "/api/v1/newsletter/subscribers",
        headers={"Authorization": f"Bearer {admin_token}"}
    ), 200, show_body=True)
else:
    check("GET /newsletter/subscribers (no auth)", client.get(
        "/api/v1/newsletter/subscribers"
    ), 401)


# ── 12. AI Chat ───────────────────────────────────────────────
section("12. AI Chat (skipped if GEMINI_API_KEY not set)")

r = client.post("/api/v1/ai/chat", json={
    "messages": [{"role": "user", "content": "What topics does this blog cover?"}]
}, timeout=30)

if r.status_code == 503:
    print(f"  {SKIP} AI service not configured (expected if GEMINI_API_KEY not set)")
elif r.status_code == 200:
    passed += 1
    print(f"  {PASS} [200] POST /ai/chat")
    print(f"      → reply: {r.json()['reply'][:100]}...")
else:
    failed += 1
    print(f"  {FAIL} [{r.status_code}] POST /ai/chat")
    print(f"      {r.text[:200]}")

check("POST /ai/chat (empty messages)", client.post("/api/v1/ai/chat", json={
    "messages": []
}), 422)

check("POST /ai/chat (too many messages)", client.post("/api/v1/ai/chat", json={
    "messages": [{"role": "user", "content": "msg"}] * 25
}), 422)

check("POST /ai/chat (invalid role)", client.post("/api/v1/ai/chat", json={
    "messages": [{"role": "admin", "content": "hello"}]
}), 422)


# ── Admin cleanup ─────────────────────────────────────────────
if admin_token:
    section("Cleanup — delete test post")
    check("DELETE /posts/test-post-api", client.delete(
        "/api/v1/posts/test-post-api",
        headers={"Authorization": f"Bearer {admin_token}"}
    ), 204)


# ── Summary ───────────────────────────────────────────────────
total = passed + failed
print(f"\n{'═'*50}")
print(f"  RESULTS: {passed}/{total} passed  |  {failed} failed")
print(f"{'═'*50}\n")

client.close()