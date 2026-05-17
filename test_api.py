"""
test_api.py — Pytest test suite for Ashwani Blog Backend
Uses FastAPI TestClient — no running server needed.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.models.user import User

# ── Test DB (in-memory SQLite) ────────────────────────────────
TEST_DB = "sqlite:///./test_ci.db"
engine = create_engine(TEST_DB, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(bind=engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    # Create admin user for tests
    db = TestSessionLocal()
    if not db.query(User).filter(User.email == "admin@test.com").first():
        db.add(User(
            username="admin",
            email="admin@test.com",
            password=hash_password("Admin@123"),
            is_admin=True,
            is_active=True,
        ))
        db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture(scope="session")
def admin_token(client):
    r = client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "Admin@123"
    })
    assert r.status_code == 200
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def user_token(client):
    client.post("/api/v1/auth/register", json={
        "username": "testuser",
        "email": "testuser@test.com",
        "password": "Test@1234"
    })
    r = client.post("/api/v1/auth/login", json={
        "email": "testuser@test.com",
        "password": "Test@1234"
    })
    assert r.status_code == 200
    return r.json()["access_token"]


# ── Health ────────────────────────────────────────────────────
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200


def test_root_serves_frontend(client):
    r = client.get("/")
    # Either serves index.html (200) or health json (200)
    assert r.status_code == 200


# ── Auth ──────────────────────────────────────────────────────
def test_register(client):
    r = client.post("/api/v1/auth/register", json={
        "username": "newuser",
        "email": "new@test.com",
        "password": "NewPass@123"
    })
    assert r.status_code in (200, 201)


def test_register_duplicate_email(client):
    r = client.post("/api/v1/auth/register", json={
        "username": "another",
        "email": "admin@test.com",
        "password": "Test@1234"
    })
    assert r.status_code == 400


def test_login_valid(client):
    r = client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "Admin@123"
    })
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_wrong_password(client):
    r = client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "wrongpassword"
    })
    assert r.status_code == 401


def test_login_unknown_email(client):
    r = client.post("/api/v1/auth/login", json={
        "email": "nobody@test.com",
        "password": "Test@1234"
    })
    assert r.status_code == 401


# ── Posts ─────────────────────────────────────────────────────
def test_get_posts(client):
    r = client.get("/api/v1/posts")
    assert r.status_code == 200


def test_get_nonexistent_post(client):
    r = client.get("/api/v1/posts/nonexistent-slug-xyz")
    assert r.status_code == 404


def test_create_post_requires_admin(client, user_token):
    r = client.post("/api/v1/posts/", headers={"Authorization": f"Bearer {user_token}"}, json={
        "slug": "test-post", "title": "Test", "excerpt": "Test",
        "content": "Content", "cat": "python"
    })
    assert r.status_code == 403


def test_create_post_admin(client, admin_token):
    r = client.post("/api/v1/posts/", headers={"Authorization": f"Bearer {admin_token}"}, json={
        "slug": "ci-test-post",
        "title": "CI Test Post",
        "excerpt": "Created in CI test.",
        "content": "<p>Content here.</p>",
        "cat": "python",
        "tags": ["ci", "test"],
        "read_time": "1 min read",
        "is_published": True,
    })
    assert r.status_code in (200, 201)


def test_get_created_post(client):
    r = client.get("/api/v1/posts/ci-test-post")
    assert r.status_code == 200
    assert r.json()["title"] == "CI Test Post"


# ── Comments ──────────────────────────────────────────────────
def test_post_comment(client):
    r = client.post("/api/v1/posts/ci-test-post/comments", json={
        "body": "Great post!",
        "guest_name": "TestReader",
        "guest_email": "reader@test.com"
    })
    assert r.status_code in (200, 201)


def test_get_comments(client):
    r = client.get("/api/v1/posts/ci-test-post/comments")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_comment_empty_body(client):
    r = client.post("/api/v1/posts/ci-test-post/comments", json={
        "body": "   ",
        "guest_name": "Reader"
    })
    assert r.status_code == 422


# ── Newsletter ────────────────────────────────────────────────
def test_newsletter_subscribe(client):
    r = client.post("/api/v1/newsletter/subscribe", json={"email": "sub@test.com"})
    assert r.status_code == 200


def test_newsletter_duplicate(client):
    r = client.post("/api/v1/newsletter/subscribe", json={"email": "sub@test.com"})
    assert r.status_code == 400


def test_newsletter_unsubscribe(client):
    r = client.post("/api/v1/newsletter/unsubscribe", json={"email": "sub@test.com"})
    assert r.status_code == 200


# ── AI Chat validation (no API key needed) ────────────────────
def test_ai_chat_empty_messages(client):
    r = client.post("/api/v1/ai/chat", json={"messages": []})
    assert r.status_code == 422


def test_ai_chat_invalid_role(client):
    r = client.post("/api/v1/ai/chat", json={
        "messages": [{"role": "admin", "content": "hello"}]
    })
    assert r.status_code == 422


def test_ai_chat_too_many_messages(client):
    r = client.post("/api/v1/ai/chat", json={
        "messages": [{"role": "user", "content": "msg"}] * 25
    })
    assert r.status_code == 422