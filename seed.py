"""
seed.py — Import your existing posts into the database.
Run once after first migration:  python seed.py
To also create an admin user:    python seed.py --admin
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.core.database import engine, SessionLocal, Base
from app.models.user import User
from app.models.post import Post
from app.models.interactions import Comment, PostLike, CommentLike, NewsletterSubscriber  # noqa
from app.core.security import hash_password


POSTS = [
    {
        "slug": "django-select-related",
        "cat": "django",
        "read_time": "6 min read",
        "title": "How I Cut Django Query Time by 40% with select_related",
        "excerpt": "Real-world ORM optimization story from e-governance APIs. The N+1 problem was silently killing performance — here's exactly how I found and fixed it.",
        "tags": ["Django", "ORM", "PostgreSQL", "Performance"],
        "layout": "featured",
        "is_featured": True,
        "toc": [
            {"title": "The N+1 Problem",              "anchor": "the-n1-problem",              "level": 2},
            {"title": "Finding It with Debug Toolbar", "anchor": "finding-it-with-debug-toolbar","level": 2},
            {"title": "The Fix",                       "anchor": "the-fix",                      "level": 2},
            {"title": "Benchmarks",                    "anchor": "benchmarks",                   "level": 2},
            {"title": "Key Takeaways",                 "anchor": "key-takeaways",                "level": 2},
        ],
        "content": "At GIS Consortium, our municipal report endpoint was clocking 3.2 seconds. Django Debug Toolbar revealed 147 queries per request. The culprit was N+1 queries on nested ForeignKey lookups. Solution: replace queryset.all() with queryset.select_related('ward__zone__city').prefetch_related('complaints'). Response time dropped to 1.9s immediately.",
    },
    {
        "slug": "rag-pgvector",
        "cat": "ai",
        "read_time": "9 min read",
        "title": "Building a RAG Pipeline with pgvector + OpenAI",
        "excerpt": "Step-by-step walkthrough of adding semantic search and NLP Q&A to a Django app using pgvector and OpenAI embeddings. No extra infrastructure — just PostgreSQL.",
        "tags": ["RAG", "pgvector", "OpenAI", "Django"],
        "layout": "side",
        "is_featured": True,
        "toc": [
            {"title": "What is RAG?",            "anchor": "what-is-rag",            "level": 2},
            {"title": "Architecture Overview",   "anchor": "architecture-overview",   "level": 2},
            {"title": "Setting Up pgvector",     "anchor": "setting-up-pgvector",     "level": 2},
            {"title": "Generating Embeddings",   "anchor": "generating-embeddings",   "level": 2},
            {"title": "The Query Pipeline",      "anchor": "the-query-pipeline",      "level": 2},
            {"title": "Django Integration",      "anchor": "django-integration",      "level": 2},
        ],
        "content": "RAG = smart search + LLM. Flow: embed the user question → cosine similarity search in pgvector → retrieve top-K chunks → pass to GPT-4o-mini → stream answer.",
    },
    {
        "slug": "cap-theorem",
        "cat": "system-design",
        "read_time": "5 min read",
        "title": "CAP Theorem Explained Without the Buzzwords",
        "excerpt": "Consistency, Availability, Partition Tolerance — every distributed systems interview asks this. Here's how to actually understand it.",
        "tags": ["CAP Theorem", "Distributed Systems", "System Design"],
        "layout": "half",
        "toc": [
            {"title": "What the Three Letters Mean", "anchor": "what-the-three-letters-mean", "level": 2},
            {"title": "The Real Trade-off",          "anchor": "the-real-trade-off",          "level": 2},
            {"title": "Real Database Examples",      "anchor": "real-database-examples",      "level": 2},
            {"title": "Interview Answer",            "anchor": "interview-answer",            "level": 2},
        ],
        "content": "CAP simplified: PostgreSQL=CP, Cassandra=AP. Network partitions ARE inevitable — the real choice is C vs A during a partition.",
    },
    {
        "slug": "two-pointers",
        "cat": "dsa",
        "read_time": "7 min read",
        "title": "Two Pointers Pattern: Every Variant You Need",
        "excerpt": "Sliding window, fast-slow, left-right — every variant mapped with Python implementations.",
        "tags": ["DSA", "Arrays", "Python", "LeetCode"],
        "layout": "half",
        "toc": [
            {"title": "Opposite Ends",      "anchor": "opposite-ends",      "level": 2},
            {"title": "Same Direction",     "anchor": "same-direction",     "level": 2},
            {"title": "Sliding Window",     "anchor": "sliding-window",     "level": 2},
            {"title": "Fast-Slow Pointers", "anchor": "fast-slow-pointers", "level": 2},
        ],
        "content": "Two pointer variants: opposite ends (sorted array), same direction (remove duplicates), sliding window, fast-slow.",
    },
    {
        "slug": "celery-canvas",
        "cat": "django",
        "read_time": "8 min read",
        "title": "Celery Canvas Primitives: chains, chords, groups",
        "excerpt": "Most Django devs only use basic Celery tasks. Canvas primitives unlock powerful async workflows.",
        "tags": ["Celery", "Redis", "Django", "Async"],
        "layout": "third",
        "toc": [
            {"title": "chain",              "anchor": "chain",              "level": 2},
            {"title": "group",              "anchor": "group",              "level": 2},
            {"title": "chord",              "anchor": "chord",              "level": 2},
            {"title": "Real-World Example", "anchor": "real-world-example", "level": 2},
        ],
        "content": "chain=sequential, group=parallel, chord=parallel+aggregate. Real example: chord(group emails, mark_archived).",
    },
    {
        "slug": "docker-django",
        "cat": "devops",
        "read_time": "10 min read",
        "title": "Docker + Django: A Production-Ready Setup",
        "excerpt": "Multi-stage Dockerfile, docker-compose with PostgreSQL and Redis — the complete setup I use.",
        "tags": ["Docker", "Django", "DevOps", "PostgreSQL"],
        "layout": "third",
        "toc": [
            {"title": "Multi-Stage Dockerfile",  "anchor": "multi-stage-dockerfile",  "level": 2},
            {"title": "docker-compose",          "anchor": "docker-compose",          "level": 2},
            {"title": "Environment Management",  "anchor": "environment-management",  "level": 2},
        ],
        "content": "Multi-stage build, non-root user, health checks on db/redis, Gunicorn workers=2*CPU+1.",
    },
    {
        "slug": "python-decorators",
        "cat": "python",
        "read_time": "6 min read",
        "title": "Python Decorators: From Zero to Functional",
        "excerpt": "Decorators are one of Python's most elegant features — here's how they work under the hood.",
        "tags": ["Python", "Decorators", "Functional"],
        "layout": "third",
        "toc": [
            {"title": "How Decorators Work",        "anchor": "how-decorators-work",        "level": 2},
            {"title": "functools.wraps",             "anchor": "functools-wraps",             "level": 2},
            {"title": "Parameterised Decorators",   "anchor": "parameterised-decorators",   "level": 2},
        ],
        "content": "A decorator is a function that takes a function and returns a function. @my_decorator = fn = my_decorator(fn).",
    },
]


def seed():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        seeded = 0
        for p in POSTS:
            exists = db.query(Post).filter(Post.slug == p["slug"]).first()
            if not exists:
                post = Post(
                    slug=p["slug"],
                    title=p["title"],
                    excerpt=p["excerpt"],
                    content=p["content"],
                    cat=p["cat"],
                    layout=p.get("layout", "half"),
                    tags=p.get("tags", []),
                    toc=p.get("toc", []),
                    read_time=p["read_time"],
                    is_featured=p.get("is_featured", False),
                    is_published=True,
                )
                db.add(post)
                seeded += 1
                print(f"  ✓ Seeded: {p['slug']}")
            else:
                print(f"  → Skipped (exists): {p['slug']}")
        db.commit()
        print(f"\n✅ {seeded} posts seeded.")

        if "--admin" in sys.argv:
            email    = input("Admin email: ").strip()
            username = input("Admin username: ").strip()
            password = input("Admin password: ").strip()

            if db.query(User).filter(User.email == email).first():
                print("⚠️  Admin user already exists.")
            else:
                admin = User(
                    username=username,
                    email=email,
                    password=hash_password(password),
                    is_admin=True,
                )
                db.add(admin)
                db.commit()
                print(f"✅ Admin user '{username}' created.")

    finally:
        db.close()


if __name__ == "__main__":
    seed()