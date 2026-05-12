"""
seed.py — Import your existing posts-data.js posts into the database.
Run once after first migration:  python seed.py

To also create an admin user:    python seed.py --admin
"""
import sys
import os

# Make sure we can import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env before importing settings
from dotenv import load_dotenv
load_dotenv()

from app.core.database import engine, SessionLocal, Base
# Must import ALL models so SQLAlchemy can resolve string relationships
from app.models.user import User
from app.models.post import Post
from app.models.interactions import Comment, PostLike, CommentLike, NewsletterSubscriber  # noqa
from app.models import utcnow
from app.core.security import hash_password

# ─────────────────────────────────────────────
# All posts from your posts-data.js
# ─────────────────────────────────────────────
POSTS = [
    {
        "slug": "django-select-related",
        "cat": "django",
        "date_str": "May 8, 2025",
        "read_time": "6 min read",
        "title": "How I Cut Django Query Time by 40% with select_related",
        "excerpt": "Real-world ORM optimization story from e-governance APIs. The N+1 problem was silently killing performance — here's exactly how I found and fixed it.",
        "tags": ["Django", "ORM", "PostgreSQL", "Performance"],
        "layout": "featured",
        "is_featured": True,
        "toc": ["The N+1 Problem", "Finding It with Debug Toolbar", "The Fix", "Benchmarks", "Key Takeaways"],
        "content": "At GIS Consortium, our municipal report endpoint was clocking 3.2 seconds. Django Debug Toolbar revealed 147 queries per request. The culprit was N+1 queries on nested ForeignKey lookups. Solution: replace queryset.all() with queryset.select_related('ward__zone__city').prefetch_related('complaints'). Response time dropped to 1.9s immediately.",
        "body": """
<h2>The N+1 Problem</h2>
<p>At <strong>GIS Consortium</strong>, our municipal report endpoint was clocking 3.2 seconds. Users were complaining. I opened Django Debug Toolbar and saw <strong>147 queries per request</strong>. That's the N+1 problem in action.</p>
<blockquote>For every parent object, Django was firing a separate query for each related object. 1 query + N queries = N+1.</blockquote>
<h2>Finding It with Debug Toolbar</h2>
<pre><code># WRONG — triggers N+1
wards = Ward.objects.filter(zone__city=city)
for ward in wards:
    complaints = ward.complaints.all()
    officer = ward.officer</code></pre>
<h2>The Fix</h2>
<pre><code># RIGHT — 2 queries total, not 147
wards = Ward.objects.filter(zone__city=city).select_related('officer','zone__city').prefetch_related('complaints')</code></pre>
<h2>Benchmarks</h2>
<p>After the fix: <strong>147 queries → 2 queries</strong>. Response time: <strong>3.2s → 1.9s</strong>.</p>
<h2>Key Takeaways</h2>
<ul>
  <li>select_related = ForeignKey / OneToOne → SQL JOIN</li>
  <li>prefetch_related = ManyToMany / reverse FK → separate optimised query</li>
</ul>""",
    },
    {
        "slug": "rag-pgvector",
        "cat": "ai",
        "date_str": "May 3, 2025",
        "read_time": "9 min read",
        "title": "Building a RAG Pipeline with pgvector + OpenAI",
        "excerpt": "Step-by-step walkthrough of adding semantic search and NLP Q&A to a Django app using pgvector and OpenAI embeddings. No extra infrastructure — just PostgreSQL.",
        "tags": ["RAG", "pgvector", "OpenAI", "Django"],
        "layout": "side",
        "is_featured": True,
        "toc": ["What is RAG?", "Architecture Overview", "Setting Up pgvector", "Generating Embeddings", "The Query Pipeline", "Django Integration"],
        "content": "RAG = smart search + LLM. Flow: embed the user question → cosine similarity search in pgvector → retrieve top-K chunks → pass to GPT-4o-mini → stream answer.",
        "body": "<h2>What is RAG?</h2><p>Retrieval-Augmented Generation lets you ground an LLM's answers in your actual data.</p>",
    },
    {
        "slug": "cap-theorem",
        "cat": "system-design",
        "date_str": "Apr 28, 2025",
        "read_time": "5 min read",
        "title": "CAP Theorem Explained Without the Buzzwords",
        "excerpt": "Consistency, Availability, Partition Tolerance — every distributed systems interview asks this. Here's how to actually understand it.",
        "tags": ["CAP Theorem", "Distributed Systems", "System Design"],
        "layout": "half",
        "toc": ["What the Three Letters Mean", "The Real Trade-off", "Real Database Examples", "Interview Answer"],
        "content": "CAP simplified: PostgreSQL=CP, Cassandra=AP. Network partitions ARE inevitable — the real choice is C vs A during a partition.",
        "body": "<h2>What the Three Letters Mean</h2><p>C=Consistency, A=Availability, P=Partition Tolerance. You cannot sacrifice P in production.</p>",
    },
    {
        "slug": "two-pointers",
        "cat": "dsa",
        "date_str": "Apr 22, 2025",
        "read_time": "7 min read",
        "title": "Two Pointers Pattern: Every Variant You Need",
        "excerpt": "Sliding window, fast-slow, left-right — every variant mapped with Python implementations.",
        "tags": ["DSA", "Arrays", "Python", "LeetCode"],
        "layout": "half",
        "toc": ["Opposite Ends", "Same Direction", "Sliding Window", "Fast-Slow Pointers"],
        "content": "Two pointer variants: opposite ends (sorted array), same direction (remove duplicates), sliding window, fast-slow.",
        "body": "<h2>Opposite Ends</h2><pre><code>def two_sum_sorted(nums, target):\n    l, r = 0, len(nums)-1\n    while l < r:\n        s = nums[l]+nums[r]\n        if s==target: return [l,r]\n        elif s < target: l+=1\n        else: r-=1</code></pre>",
    },
    {
        "slug": "celery-canvas",
        "cat": "django",
        "date_str": "Apr 15, 2025",
        "read_time": "8 min read",
        "title": "Celery Canvas Primitives: chains, chords, groups",
        "excerpt": "Most Django devs only use basic Celery tasks. Canvas primitives unlock powerful async workflows.",
        "tags": ["Celery", "Redis", "Django", "Async"],
        "layout": "third",
        "toc": ["chain", "group", "chord", "Real-World Example"],
        "content": "chain=sequential, group=parallel, chord=parallel+aggregate. Real example: chord(group emails, mark_archived).",
        "body": "<h2>chain</h2><pre><code>chain(fetch.s(url), process.s(), save.s()).delay()</code></pre><h2>chord</h2><pre><code>chord(group(notify.s(m) for m in members), mark_archived.s(id)).delay()</code></pre>",
    },
    {
        "slug": "docker-django",
        "cat": "devops",
        "date_str": "Apr 9, 2025",
        "read_time": "10 min read",
        "title": "Docker + Django: A Production-Ready Setup",
        "excerpt": "Multi-stage Dockerfile, docker-compose with PostgreSQL and Redis — the complete setup I use.",
        "tags": ["Docker", "Django", "DevOps", "PostgreSQL"],
        "layout": "third",
        "toc": ["Multi-Stage Dockerfile", "docker-compose", "Environment Management"],
        "content": "Multi-stage build, non-root user, health checks on db/redis, Gunicorn workers=2*CPU+1.",
        "body": "<h2>Multi-Stage Dockerfile</h2><pre><code>FROM python:3.12-slim AS builder\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install --user -r requirements.txt\n\nFROM python:3.12-slim\nCOPY --from=builder /root/.local /root/.local\nCOPY . .\nUSER appuser</code></pre>",
    },
    {
        "slug": "python-decorators",
        "cat": "python",
        "date_str": "Apr 2, 2025",
        "read_time": "6 min read",
        "title": "Python Decorators: From Zero to Functional",
        "excerpt": "Decorators are one of Python's most elegant features — here's how they work under the hood.",
        "tags": ["Python", "Decorators", "Functional"],
        "layout": "third",
        "toc": ["How Decorators Work", "functools.wraps", "Parameterised Decorators"],
        "content": "A decorator is a function that takes a function and returns a function. @my_decorator = fn = my_decorator(fn).",
        "body": "<h2>How Decorators Work</h2><pre><code>def log_calls(func):\n    @functools.wraps(func)\n    def wrapper(*args, **kwargs):\n        print(f'Calling {func.__name__}')\n        return func(*args, **kwargs)\n    return wrapper</code></pre>",
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
                    body=p["body"],
                    content=p["content"],
                    cat=p["cat"],
                    layout=p.get("layout", "half"),
                    tags=p.get("tags", []),
                    toc=p.get("toc", []),
                    date_str=p["date_str"],
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

        # Optional admin user
        if "--admin" in sys.argv:
            email = input("Admin email: ").strip()
            username = input("Admin username: ").strip()
            password = input("Admin password: ").strip()

            if db.query(User).filter(User.email == email).first():
                print("⚠️  Admin user already exists.")
            else:
                from app.core.security import hash_password
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