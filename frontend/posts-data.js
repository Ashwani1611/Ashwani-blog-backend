/* ═══════════════════════════════════════
   ASHWANI KUMAR — BLOG POSTS DATA
   posts-data.js — Single source of truth
   
   HOW TO ADD A NEW POST:
   1. Copy the template object below
   2. Fill in all fields
   3. Push it to the POSTS array
   4. Done — both blog.html and blog-post.html
      pick it up automatically.
   
   FIELDS:
   id          → unique URL slug (no spaces, use hyphens)
   title       → full post title
   excerpt     → 1-2 sentence summary shown on grid card
   cat         → one of: django | dsa | system-design | ai | devops | python
   tags        → array of tag strings
   date        → display date e.g. 'May 12, 2025'
   read        → reading time e.g. '6 min read'
   likes       → starting like count (integer)
   comments    → number of seeded comments shown
   layout      → featured | side | half | third
                 featured = full-width big card (use once, for top post)
                 side     = narrow card beside featured
                 half     = half-width card
                 third    = one-third width card
   featured    → true only for the big featured card
   toc         → array of section heading strings for Table of Contents
   body        → full HTML string (h2, h3, p, pre>code, blockquote, ul, .callout)
   content     → plain-text summary used by the AI sidebar chat
═══════════════════════════════════════ */

const POSTS = [
  {
    id: 'django-select-related',
    cat: 'django',
    date: 'May 8, 2025',
    read: '6 min read',
    likes: 24,
    comments: 3,
    title: 'How I Cut Django Query Time by 40% with select_related',
    excerpt: 'Real-world ORM optimization story from e-governance APIs. The N+1 problem was silently killing performance — here\'s exactly how I found and fixed it.',
    tags: ['Django', 'ORM', 'PostgreSQL', 'Performance'],
    layout: 'featured',
    featured: true,
    toc: ['The N+1 Problem', 'Finding It with Debug Toolbar', 'The Fix', 'Benchmarks', 'Key Takeaways'],
    content: 'At GIS Consortium, our municipal report endpoint was clocking 3.2 seconds. Django Debug Toolbar revealed 147 queries per request. The culprit was N+1 queries on nested ForeignKey lookups. Solution: replace queryset.all() with queryset.select_related(\'ward__zone__city\').prefetch_related(\'complaints\'). Response time dropped to 1.9s immediately.',
    body: `
<h2>The N+1 Problem</h2>
<p>At <strong>GIS Consortium</strong>, our municipal report endpoint was clocking 3.2 seconds. Users were complaining. I opened Django Debug Toolbar and saw <strong>147 queries per request</strong>. That's the N+1 problem in action.</p>
<blockquote>For every parent object, Django was firing a separate query for each related object. 1 query + N queries = N+1.</blockquote>
<h2>Finding It with Debug Toolbar</h2>
<p>The offending code looked innocent:</p>
<pre><code># WRONG — triggers N+1
wards = Ward.objects.filter(zone__city=city)
for ward in wards:
    complaints = ward.complaints.all()  # new query per ward!
    officer = ward.officer              # another query per ward!</code></pre>
<div class="callout"><span class="callout-icon">⚡</span><div class="callout-text">Django's ORM is lazy — it fetches related data on access unless you tell it to prefetch everything up front.</div></div>
<h2>The Fix</h2>
<p>Two tools solve this completely: <code>select_related()</code> for ForeignKey/OneToOne (SQL JOIN), and <code>prefetch_related()</code> for ManyToMany/reverse FK (separate optimised query).</p>
<pre><code># RIGHT — 2 queries total, not 147
wards = Ward.objects.filter(
    zone__city=city
).select_related(
    'officer',        # ForeignKey → JOIN
    'zone__city'      # Nested FK → single JOIN
).prefetch_related(
    'complaints'      # Reverse FK → 1 extra query
)</code></pre>
<h2>Benchmarks</h2>
<p>After the fix: <strong>147 queries → 2 queries</strong>. Response time: <strong>3.2s → 1.9s</strong>. That's a 40% reduction without touching the database schema, adding caches, or changing any business logic.</p>
<h2>Key Takeaways</h2>
<ul>
  <li>Always check Django Debug Toolbar in development — never guess.</li>
  <li><code>select_related</code> = ForeignKey / OneToOne → uses SQL JOIN</li>
  <li><code>prefetch_related</code> = ManyToMany / reverse FK → separate optimised query</li>
  <li>You can chain them: <code>.select_related('a').prefetch_related('b__c')</code></li>
  <li>Use <code>only()</code> and <code>defer()</code> to avoid loading unused columns.</li>
</ul>`
  },
  {
    id: 'rag-pgvector',
    cat: 'ai',
    date: 'May 3, 2025',
    read: '9 min read',
    likes: 41,
    comments: 5,
    title: 'Building a RAG Pipeline with pgvector + OpenAI',
    excerpt: 'Step-by-step walkthrough of adding semantic search and NLP Q&A to a Django app using pgvector and OpenAI embeddings. No extra infrastructure — just PostgreSQL.',
    tags: ['RAG', 'pgvector', 'OpenAI', 'Django'],
    layout: 'side',
    featured: true,
    toc: ['What is RAG?', 'Architecture Overview', 'Setting Up pgvector', 'Generating Embeddings', 'The Query Pipeline', 'Django Integration'],
    content: 'RAG = smart search + LLM. Flow: embed the user question → cosine similarity search in pgvector → retrieve top-K chunks → pass to GPT-4o-mini → stream answer. For Skyline Wheels, this means: user asks about best bike under 1L → semantic search over bike specs → grounded answer from real inventory data.',
    body: `
<h2>What is RAG?</h2>
<p><strong>Retrieval-Augmented Generation</strong> lets you ground an LLM's answers in your actual data. Instead of relying on the model's training knowledge, you: retrieve relevant chunks from your database → augment the prompt → generate a grounded answer.</p>
<blockquote>RAG = smart search + LLM. It's the most practical way to add AI to an existing product without fine-tuning.</blockquote>
<h2>Architecture Overview</h2>
<p>For Skyline Wheels, the flow is: user asks "Which Bajaj bike has the best mileage under ₹1L?" → embed the question → vector similarity search in pgvector → retrieve top 5 bike spec chunks → pass to GPT-4o-mini → stream the answer.</p>
<h2>Setting Up pgvector</h2>
<pre><code># In your Django migration
from pgvector.django import VectorField

class BikeChunk(models.Model):
    bike = models.ForeignKey(Bike, on_delete=models.CASCADE)
    content = models.TextField()
    embedding = VectorField(dimensions=1536)  # text-embedding-3-small</code></pre>
<h2>Generating Embeddings</h2>
<pre><code>import openai

def embed(text):
    res = openai.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return res.data[0].embedding

# On bike save:
chunk.embedding = embed(chunk.content)
chunk.save()</code></pre>
<h2>The Query Pipeline</h2>
<pre><code>from pgvector.django import CosineDistance

def search(query, top_k=5):
    q_vec = embed(query)
    return BikeChunk.objects.annotate(
        dist=CosineDistance('embedding', q_vec)
    ).order_by('dist')[:top_k]</code></pre>
<div class="callout"><span class="callout-icon">💡</span><div class="callout-text">Use cosine distance for semantic similarity — it's direction-based, not magnitude-based, which works better for text embeddings.</div></div>
<h2>Django Integration</h2>
<p>A streaming Django view sends the GPT response token-by-token using <code>StreamingHttpResponse</code>, giving a typewriter UX. The system prompt includes the retrieved chunks as context, so the model answers only from real bike data.</p>`
  },
  {
    id: 'cap-theorem',
    cat: 'system-design',
    date: 'Apr 28, 2025',
    read: '5 min read',
    likes: 33,
    comments: 2,
    title: 'CAP Theorem Explained Without the Buzzwords',
    excerpt: 'Consistency, Availability, Partition Tolerance — every distributed systems interview asks this. Here\'s how to actually understand it.',
    tags: ['CAP Theorem', 'Distributed Systems', 'System Design'],
    layout: 'half',
    toc: ['What the Three Letters Mean', 'The Real Trade-off', 'Real Database Examples', 'Interview Answer'],
    content: 'CAP simplified: you cannot guarantee all 3. PostgreSQL: CP. Cassandra: AP. The real insight: network partitions ARE inevitable in production — so the real choice is C vs A during a partition. Banking = CP, social media feed = AP.',
    body: `
<h2>What the Three Letters Mean</h2>
<p><strong>C</strong> — Consistency: every read gets the most recent write (or an error). <strong>A</strong> — Availability: every request gets a response (not necessarily the latest data). <strong>P</strong> — Partition Tolerance: the system keeps working when network communication between nodes fails.</p>
<blockquote>You CANNOT sacrifice P in production. Network partitions happen. The real choice is C vs A.</blockquote>
<h2>The Real Trade-off</h2>
<p>During a network partition, you must choose: return potentially stale data (AP) or return an error (CP). Neither is wrong — it depends on your use case.</p>
<h2>Real Database Examples</h2>
<ul>
  <li><strong>PostgreSQL</strong>: CP — strong consistency, rejects writes during partition</li>
  <li><strong>Cassandra</strong>: AP — always available, eventual consistency</li>
  <li><strong>Redis</strong>: CP (single node) / AP (cluster with async replication)</li>
  <li><strong>MongoDB</strong>: CP by default (tunable)</li>
</ul>
<h2>Interview Answer</h2>
<p>For a banking system → CP (never show wrong balance). For a social media feed → AP (showing a 2-second-old post is fine). For a dealership inventory → depends on whether double-booking is acceptable.</p>`
  },
  {
    id: 'two-pointers',
    cat: 'dsa',
    date: 'Apr 22, 2025',
    read: '7 min read',
    likes: 19,
    comments: 1,
    title: 'Two Pointers Pattern: Every Variant You Need',
    excerpt: 'Sliding window, fast-slow, left-right — every variant mapped with Python implementations and the exact problem types each one solves.',
    tags: ['DSA', 'Arrays', 'Python', 'LeetCode'],
    layout: 'half',
    toc: ['Opposite Ends', 'Same Direction', 'Sliding Window', 'Fast-Slow Pointers', 'When to Use Each'],
    content: 'Variants: 1) Opposite ends (sorted array, target sum). 2) Same direction (remove duplicates, fast-slow). 3) Sliding window (fixed and variable size). Golden rule: two pointers only work when the array has a property that tells you WHICH pointer to move.',
    body: `
<h2>Opposite Ends</h2>
<p>Start one pointer at index 0, one at n-1. Move them toward each other based on a condition. Works on <strong>sorted arrays</strong>.</p>
<pre><code>def two_sum_sorted(nums, target):
    l, r = 0, len(nums) - 1
    while l < r:
        s = nums[l] + nums[r]
        if s == target: return [l, r]
        elif s < target: l += 1
        else: r -= 1</code></pre>
<h2>Same Direction</h2>
<p>Both pointers start at 0, move right, one faster. Used for removing duplicates, partitioning arrays.</p>
<pre><code>def remove_duplicates(nums):
    k = 1
    for i in range(1, len(nums)):
        if nums[i] != nums[i-1]:
            nums[k] = nums[i]; k += 1
    return k</code></pre>
<h2>Sliding Window</h2>
<p>Variable-size window: expand right until condition breaks, shrink from left.</p>
<pre><code>def longest_unique_substr(s):
    seen = {}; l = res = 0
    for r, c in enumerate(s):
        if c in seen: l = max(l, seen[c] + 1)
        seen[c] = r; res = max(res, r - l + 1)
    return res</code></pre>
<div class="callout"><span class="callout-icon">🎯</span><div class="callout-text">Golden rule: two pointers only work when a property (sortedness, distinctness) tells you WHICH pointer to move.</div></div>`
  },
  {
    id: 'celery-canvas',
    cat: 'django',
    date: 'Apr 15, 2025',
    read: '8 min read',
    likes: 28,
    comments: 4,
    title: 'Celery Canvas Primitives: chains, chords, groups',
    excerpt: 'Most Django devs only use basic Celery tasks. Canvas primitives unlock powerful async workflows — here\'s a real use case from FlowBoard.',
    tags: ['Celery', 'Redis', 'Django', 'Async'],
    layout: 'third',
    toc: ['chain', 'group', 'chord', 'starmap', 'Real-World Example'],
    content: 'chain(task1, task2) = sequential. group(t1, t2) = parallel. chord(group, callback) = parallel then aggregate. Real example: chord(group(send_email.s(u) for u in users), mark_notified.s()) — all emails in parallel, board marked archived only after all succeed.',
    body: `
<h2>chain</h2>
<p>Execute tasks sequentially. Output of task N becomes input of task N+1.</p>
<pre><code>from celery import chain
result = chain(fetch_data.s(url), process.s(), save.s()).delay()</code></pre>
<h2>group</h2>
<p>Execute tasks in parallel. All tasks run simultaneously.</p>
<pre><code>from celery import group
result = group(send_email.s(user) for user in users).delay()</code></pre>
<h2>chord</h2>
<p>Run a group in parallel, then call a callback with all results.</p>
<pre><code>from celery import chord
result = chord(
    group(process_file.s(f) for f in files),
    aggregate_results.s()
).delay()</code></pre>
<h2>Real-World Example</h2>
<p>In FlowBoard, when a board is archived: <code>chord(group(notify_member.s(m) for m in members), mark_archived.s(board_id))</code> — all members notified in parallel, board marked archived only after all notifications succeed.</p>`
  },
  {
    id: 'docker-django',
    cat: 'devops',
    date: 'Apr 9, 2025',
    read: '10 min read',
    likes: 36,
    comments: 14,
    title: 'Docker + Django: A Production-Ready Setup',
    excerpt: 'Multi-stage Dockerfile, docker-compose with PostgreSQL and Redis, environment management — the complete setup I use for every Django project.',
    tags: ['Docker', 'Django', 'DevOps', 'PostgreSQL'],
    layout: 'third',
    toc: ['Multi-Stage Dockerfile', 'docker-compose', 'Environment Management', 'Static Files', 'Health Checks'],
    content: 'Key decisions: multi-stage build (keeps image small), non-root user inside container, health checks on db and redis before web starts, .env.example committed/.env gitignored, Gunicorn with workers = 2*CPU+1, volume for static/media not baked into image.',
    body: `
<h2>Multi-Stage Dockerfile</h2>
<p>Multi-stage builds keep the final image lean — install build tools in the builder stage, copy only the compiled output to the production stage.</p>
<pre><code>FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS production
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
RUN useradd -m appuser && chown -R appuser /app
USER appuser
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]</code></pre>
<h2>docker-compose</h2>
<pre><code>services:
  db:
    image: postgres:16
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
  redis:
    image: redis:7-alpine
  web:
    build: .
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_started }</code></pre>
<div class="callout"><span class="callout-icon">🐋</span><div class="callout-text">Always use health checks on db and redis. Without them, web starts before Postgres is ready and crashes on the first DB call.</div></div>
<h2>Environment Management</h2>
<p>Commit <code>.env.example</code> with all variable names but no values. Add <code>.env</code> to <code>.gitignore</code>. Use <code>python-decouple</code> to read env vars with type casting and defaults.</p>`
  },
  {
    id: 'python-decorators',
    cat: 'python',
    date: 'Apr 2, 2025',
    read: '6 min read',
    likes: 22,
    comments: 6,
    title: 'Python Decorators: From Zero to Functional',
    excerpt: 'Decorators are one of Python\'s most elegant features — here\'s how they work under the hood, with practical production examples.',
    tags: ['Python', 'Decorators', 'Functional', 'IIT Mandi'],
    layout: 'third',
    toc: ['How Decorators Work', 'functools.wraps', 'Parameterised Decorators', 'Real-World Uses'],
    content: 'A decorator is a function that takes a function and returns a function. @my_decorator = fn = my_decorator(fn). functools.wraps preserves __name__ and __doc__. Practical uses: logging, auth checks, caching, rate limiting, retry logic.',
    body: `
<h2>How Decorators Work</h2>
<p>A decorator is just a function that takes a function and returns a function. The <code>@</code> syntax is pure sugar.</p>
<pre><code># These two are identical:
@my_decorator
def fn(): pass

def fn(): pass
fn = my_decorator(fn)</code></pre>
<h2>functools.wraps</h2>
<p>Always use <code>@functools.wraps(func)</code> on your wrapper — it preserves <code>__name__</code>, <code>__doc__</code>, and other metadata.</p>
<pre><code>import functools

def log_calls(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper</code></pre>
<h2>Parameterised Decorators</h2>
<pre><code>def retry(times=3):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(times):
                try: return func(*args, **kwargs)
                except Exception as e:
                    if attempt == times - 1: raise
        return wrapper
    return decorator

@retry(times=5)
def fetch_data(url): ...</code></pre>
<div class="callout"><span class="callout-icon">✨</span><div class="callout-text">Parameterised decorators are just factories — a function that returns a decorator that returns a wrapper. Three levels of nesting.</div></div>`
  },
];