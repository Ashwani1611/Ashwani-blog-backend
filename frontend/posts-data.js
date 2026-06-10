/* ═══════════════════════════════════════════════════════════════════
   posts-data.js — Static blog post data for Ashwani Kumar's portfolio
   8 posts drawn directly from real project problems & solutions
   ═══════════════════════════════════════════════════════════════════ */

const POSTS = [

  /* ─────────────────────────────────────────────────────────────
     01 — FEATURED
     ───────────────────────────────────────────────────────────── */
  {
    id:        'django-orm-n-plus-one',
    slug:      'django-orm-n-plus-one',
    cat:       'django',
    layout:    'featured',
    featured:  true,
    title:     'How I Cut Django Query Count from 847 to 11 on a Government API',
    excerpt:   'The property tax endpoint that served 5 municipal corporations was making 847 database queries per request. Here\'s exactly how I found it, fixed it, and got the number down to 11 — with a 40% latency drop.',
    date:      'June 3, 2026',
    read:      '9 min read',
    likes:     38,
    comments:  4,
    tags:      ['Django ORM', 'N+1 Query', 'select_related', 'prefetch_related', 'Performance'],
    toc:       ['The Problem Discovery', 'Why N+1 Queries Happen', 'Django Debug Toolbar Setup', 'The Fix: select_related', 'The Fix: prefetch_related', 'Before vs After Numbers', 'What I\'d Do Differently'],
    body: `
<h2>The Problem Discovery</h2>
<p>It started with a complaint from a municipal administrator: the property list endpoint was "too slow." Not crashing. Not returning errors. Just slow. Slow enough that field supervisors were closing the app before the list loaded.</p>
<p>I'd been working on the <strong>GIS Consortium property tax system</strong> for several months at that point, and the endpoint in question served bulk property records across 5+ municipal corporations — including tax calculations, zone data, and owner details. It worked fine in development. On the server, with real data, it was a different story.</p>
<div class="callout">
  <div class="callout-icon">🔍</div>
  <div class="callout-text">The endpoint: <code>GET /api/properties/?zone=23&status=active</code> — returns a paginated list of properties with their tax dues, zone info, and owner records. 847 database queries. Per request.</div>
</div>
<p>I found out the real number only after installing Django Debug Toolbar on the staging environment. Before that I had no idea how bad it was.</p>

<h2>Why N+1 Queries Happen</h2>
<p>The N+1 problem is specific to ORM-driven code and it's invisible until you look at SQL logs. Here's the mental model:</p>
<p>You fetch 100 properties — that's 1 query. Then your serializer touches <code>property.zone.name</code> on each one — that's 100 more queries. Then it touches <code>property.owner.full_name</code> — another 100. And so on. By the time a serializer with 4-5 related fields processes a page of 100 records, you're making 400+ queries for what could be 3.</p>
<p>The Django ORM is lazy by default. It doesn't fetch related objects until you access them. That's great for memory when you only need the base model. It's catastrophic when you need related data for every record in a queryset.</p>
<pre><code># What the serializer was doing (simplified)
class PropertySerializer(serializers.ModelSerializer):
    zone_name  = serializers.CharField(source='zone.name')      # +1 per record
    owner_name = serializers.CharField(source='owner.full_name') # +1 per record
    rate_code  = serializers.CharField(source='tax_rate.code')   # +1 per record
    ward_ref   = serializers.CharField(source='ward.reference')  # +1 per record

# Each access = 1 SQL query × N records = N+1 total
</code></pre>
<p>With 100 records per page and 4 foreign keys: <strong>1 + 100 + 100 + 100 + 100 = 401 queries</strong>. Our pages had ~200 records. Hence 847.</p>

<h2>Django Debug Toolbar Setup</h2>
<p>If you're not already running this on staging, stop reading and install it right now. It's the single most useful tool for Django query debugging.</p>
<pre><code># settings/staging.py
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
INTERNAL_IPS = ['127.0.0.1', '10.0.2.2']  # adjust for your staging IP

# urls.py
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
</code></pre>
<p>The SQL panel shows you every query, its execution time, and — critically — duplicate queries. When you see the same query repeated 200 times with different primary key values, that's your N+1.</p>

<h2>The Fix: select_related</h2>
<p><code>select_related</code> follows ForeignKey and OneToOne relationships and performs a SQL JOIN — fetching everything in a single query instead of N+1.</p>
<pre><code># BEFORE — 847 queries
queryset = Property.objects.filter(zone=zone, status='active')

# AFTER — select_related for ForeignKey fields
queryset = Property.objects.filter(
    zone=zone, status='active'
).select_related(
    'zone',        # ForeignKey → JOIN properties + zones
    'owner',       # ForeignKey → JOIN + owners
    'tax_rate',    # ForeignKey → JOIN + tax_rates
    'ward',        # ForeignKey → JOIN + wards
)
</code></pre>
<p>This collapsed four separate queries-per-row into a single JOIN. Query count dropped from 847 → 11 immediately. The remaining 10 were legitimate lookups for pagination metadata and user permissions.</p>
<div class="callout">
  <div class="callout-icon">⚠️</div>
  <div class="callout-text"><strong>Important:</strong> Don't blindly select_related everything. If a related model has 40 columns and you only need 2, you're over-fetching. Use <code>only()</code> or <code>defer()</code> to limit columns on heavy models.</div>
</div>

<h2>The Fix: prefetch_related</h2>
<p><code>prefetch_related</code> is for ManyToMany and reverse ForeignKey relationships. It runs a separate query and does the join in Python — which sounds worse but is actually correct because SQL JOINs on M2M multiply rows in ways that break aggregation.</p>
<pre><code># Property has many survey_records (reverse FK)
# and many compliance_flags (M2M)
queryset = Property.objects.filter(...).select_related(
    'zone', 'owner', 'tax_rate', 'ward'
).prefetch_related(
    'survey_records',     # reverse FK — separate query, Python join
    'compliance_flags',   # M2M — separate query, Python join
)

# You can also limit what gets prefetched with Prefetch()
from django.db.models import Prefetch
queryset = Property.objects.prefetch_related(
    Prefetch(
        'survey_records',
        queryset=SurveyRecord.objects.filter(status='complete').only('id', 'completed_at'),
        to_attr='completed_surveys'  # accessible as property.completed_surveys
    )
)
</code></pre>

<h2>Before vs After Numbers</h2>
<p>Measured on staging with 200 records per page, Django Debug Toolbar SQL panel:</p>
<pre><code>BEFORE:
  Total queries:     847
  Duplicate queries: 800 (N+1 pattern)
  Avg response time: 3.2s

AFTER select_related + prefetch_related:
  Total queries:     11
  Duplicate queries: 0
  Avg response time: 0.19s

Improvement: 98.7% fewer queries, ~40% faster wall-clock time
(wall-clock includes network, serialization — query time itself dropped ~94%)
</code></pre>

<h2>What I'd Do Differently</h2>
<p>Annotate querysets at the model manager level, not ad-hoc in views. A <code>PropertyManager.with_display_fields()</code> method that always adds the right select_related/prefetch_related is better than remembering to add it in every viewset. I added this after the fix — the view code got much cleaner:</p>
<pre><code">class PropertyManager(models.Manager):
    def with_display_fields(self):
        return self.select_related(
            'zone', 'owner', 'tax_rate', 'ward'
        ).prefetch_related(
            'survey_records', 'compliance_flags'
        )

# View
class PropertyListView(generics.ListAPIView):
    def get_queryset(self):
        return Property.objects.with_display_fields().filter(
            zone=self.kwargs['zone']
        )
</code></pre>
<p>This makes the optimization reusable and hard to accidentally bypass. The manager becomes the contract: "whenever you need a property with its display fields, use this."</p>
    `
  },

  /* ─────────────────────────────────────────────────────────────
     02 — SIDE
     ───────────────────────────────────────────────────────────── */
  {
    id:        'redis-caching-django',
    slug:      'redis-caching-django',
    cat:       'django',
    layout:    'side',
    title:     'Redis Caching in Django: How I Got ~40% Load Improvement on Skyline Wheels',
    excerpt:   'The bike inventory page was rebuilding the same queryset on every visitor request. Adding Redis cache with the right TTL and invalidation strategy cut server load by 40% — here\'s the exact implementation.',
    date:      'May 28, 2026',
    read:      '7 min read',
    likes:     24,
    comments:  3,
    tags:      ['Redis', 'Django Cache', 'Performance', 'Skyline Wheels'],
    toc:       ['The Problem', 'Cache Setup', 'What to Cache vs Not', 'Cache Invalidation on Save', 'TTL Strategy', 'Measuring the Improvement'],
    body: `
<h2>The Problem</h2>
<p>On <strong>Skyline Wheels</strong> (a live Bajaj dealership platform), the bike inventory page was the most-visited page on the site. Visitors — people walking past the showroom and scanning the QR code — hit it constantly. The page load pulled a queryset of ~80 bikes with their models, variants, colours, and availability status from PostgreSQL every single time.</p>
<p>The inventory didn't change often. Maybe once or twice a day when a new bike arrived or one sold. But we were rebuilding the same queryset hundreds of times between those changes. Pure waste.</p>

<h2>Cache Setup</h2>
<p>Railway (our host) supports Redis as an add-on. I added it to the project and configured Django's cache framework:</p>
<pre><code># requirements.txt
django-redis==5.4.0
redis==5.0.1

# settings/production.py
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 20},
            "IGNORE_EXCEPTIONS": True,   # degrade gracefully if Redis is down
        },
        "TIMEOUT": 300,  # 5 min default TTL
    }
}
</code></pre>
<p><code>IGNORE_EXCEPTIONS: True</code> is important for production. If Redis goes down, Django falls back to the database instead of returning 500 errors. Your site gets slower, not broken.</p>

<h2>What to Cache vs Not</h2>
<p>Not everything is worth caching. The rule I follow: cache data that is read frequently, changes infrequently, and can tolerate being slightly stale for a defined period.</p>
<pre><code">GOOD CANDIDATES (Skyline Wheels):
  - Bike inventory list (changes 1-2x/day, read 200x/day)
  - Showroom details (changes rarely, read constantly)
  - Service station info (changes rarely)
  - Homepage featured bikes (curated, changes weekly)

BAD CANDIDATES:
  - Enquiry counts (changes on every form submit)
  - User-specific data (personalised, can't share cache key)
  - Stock availability on checkout (must be real-time)
  - Admin dashboard stats (needs to be current)
</code></pre>

<h2>Cache Invalidation on Save</h2>
<p>The hardest part of caching isn't adding it — it's invalidating it correctly. I used Django signals to clear the cache whenever an admin updates inventory:</p>
<pre><code">from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Bike, Showroom

INVENTORY_CACHE_KEY = 'bike_inventory_all'

@receiver(post_save, sender=Bike)
@receiver(post_delete, sender=Bike)
def invalidate_inventory_cache(sender, **kwargs):
    cache.delete(INVENTORY_CACHE_KEY)
    # Also clear any variant-specific cache keys
    cache.delete_pattern('bike_inventory_*')   # requires django-redis

# In the view
class BikeInventoryView(generics.ListAPIView):
    def get_queryset(self):
        cached = cache.get(INVENTORY_CACHE_KEY)
        if cached is not None:
            return cached
        qs = Bike.objects.select_related(
            'model', 'variant', 'showroom'
        ).filter(is_active=True).order_by('-created_at')
        cache.set(INVENTORY_CACHE_KEY, qs, timeout=300)
        return qs
</code></pre>
<div class="callout">
  <div class="callout-icon">⚠️</div>
  <div class="callout-text"><code>cache.delete_pattern()</code> only works with django-redis — not with the default LocMemCache or DatabaseCache backends. If you're not using django-redis, store related cache keys in a set and delete them manually.</div>
</div>

<h2>TTL Strategy</h2>
<p>Different data ages at different rates. I settled on these TTLs for Skyline Wheels:</p>
<pre><code">Bike inventory list:    300s  (5 min) — changes 1-2x/day max
Showroom details:       3600s (1 hr)  — near-static
Featured bikes:         1800s (30 min) — curated weekly
Service station list:   7200s (2 hr)  — changes rarely
Homepage stats:          120s (2 min)  — can be slightly stale
</code></pre>

<h2>Measuring the Improvement</h2>
<p>I measured with Railway's built-in metrics (CPU and memory) before and after enabling Redis across peak hours (11am–2pm, when showroom visitors are active).</p>
<pre><code">BEFORE Redis:
  Avg PostgreSQL query time: 28ms per inventory request
  DB connection pool usage:  ~65% at peak
  Server CPU at peak:        ~72%

AFTER Redis (cache hit rate ~87%):
  Avg response time for cached requests: 3ms (served from memory)
  DB connection pool usage: ~38% at peak
  Server CPU at peak:       ~43%

Overall server load reduction: ~40%
</code></pre>
<p>The 87% cache hit rate means 87 out of 100 inventory requests never touch the database. The remaining 13% are either cache misses (first request after TTL expiry) or cache invalidations (admin saved a bike record). Both of those hit the database and re-populate the cache for the next 87.</p>
    `
  },

  /* ─────────────────────────────────────────────────────────────
     03 — HALF
     ───────────────────────────────────────────────────────────── */
  {
    id:        'tally-to-postgres-sync',
    slug:      'tally-to-postgres-sync',
    cat:       'python',
    layout:    'half',
    title:     'Building a Tally → PostgreSQL Sync Pipeline That Cut Reporting from 12 Hours to 1 Minute',
    excerpt:   'The Bajaj Analytics client spent 12 hours every month manually building P&L reports. I built an automated pipeline that syncs Tally accounting data into PostgreSQL and generates reports on demand. Here\'s how.',
    date:      'May 20, 2026',
    read:      '10 min read',
    likes:     31,
    comments:  5,
    tags:      ['Python', 'Tally API', 'PostgreSQL', 'Pandas', 'Automation', 'Bajaj Analytics'],
    toc:       ['The Manual Process That Took 12 Hours', 'How Tally\'s HTTP API Works', 'Building the Sync Pipeline', 'Excel Expense Import', 'P&L Report Generation', 'The Result'],
    body: `
<h2>The Manual Process That Took 12 Hours</h2>
<p>The finance team at our Bajaj dealership client had a monthly ritual. On the last working day of each month, someone sat down and spent an entire working day building the P&L report. The process:</p>
<ol>
  <li>Export Tally ledgers as PDFs (Tally doesn't have a great CSV export)</li>
  <li>Manually re-key the totals into a master Excel spreadsheet</li>
  <li>Pull expense records from a separate Excel file kept by the operations team</li>
  <li>Cross-reference the two, categorize entries, calculate P&L per category</li>
  <li>Format the final report with charts and print it for the owner</li>
</ol>
<p>12 hours. Once a month. Every month. And if the owner wanted to see numbers mid-month, it was another half-day. I built a system that does all of this in under a minute, on demand.</p>

<h2>How Tally's HTTP API Works</h2>
<p>Most people don't know Tally has a built-in HTTP server. No plugin needed. Tally ERP 9 and TallyPrime both expose an XML-based API on <code>localhost:9000</code> when running on the same machine.</p>
<p>You send it an XML request describing what data you want, it returns XML. That's it. No OAuth, no tokens — it just responds to HTTP POST on the local network.</p>
<pre><code">import requests
from xml.etree import ElementTree as ET

TALLY_URL = "http://localhost:9000"

def fetch_ledger_entries(from_date: str, to_date: str) -> list[dict]:
    """
    from_date, to_date: format "YYYYMMDD" e.g. "20260501"
    Returns list of ledger entry dicts
    """
    xml_request = f"""
    <ENVELOPE>
      <HEADER>
        <VERSION>1</VERSION>
        <TALLYREQUEST>Export</TALLYREQUEST>
        <TYPE>Data</TYPE>
        <ID>Daybook</ID>
      </HEADER>
      <BODY>
        <DESC>
          <STATICVARIABLES>
            <SVFROMDATE>{from_date}</SVFROMDATE>
            <SVTODATE>{to_date}</SVTODATE>
            <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
          </STATICVARIABLES>
        </DESC>
      </BODY>
    </ENVELOPE>
    """
    response = requests.post(
        TALLY_URL,
        data=xml_request.encode('utf-8'),
        headers={'Content-Type': 'text/xml'},
        timeout=30
    )
    response.raise_for_status()
    return parse_tally_xml(response.text)
</code></pre>

<h2>Building the Sync Pipeline</h2>
<p>Parsing Tally XML is messy — the schema is inconsistent across Tally versions. I built a normalizer that handles the common variance:</p>
<pre><code">def parse_tally_xml(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    entries = []
    for voucher in root.iter('VOUCHER'):
        date_raw = voucher.findtext('DATE', '')
        amount_raw = voucher.findtext('AMOUNT', '0')
        entries.append({
            'voucher_number': voucher.findtext('VOUCHERNUMBER', ''),
            'date':           parse_tally_date(date_raw),  # YYYYMMDD → date
            'ledger':         voucher.findtext('LEDGERNAME', ''),
            'voucher_type':   voucher.findtext('VOUCHERTYPE', ''),
            'amount':         abs(float(amount_raw)),  # Tally uses negative for credits
            'is_credit':      float(amount_raw) < 0,
            'narration':      voucher.findtext('NARRATION', ''),
        })
    return entries

# Upsert into PostgreSQL — idempotent, safe to run repeatedly
def sync_to_postgres(entries: list[dict]):
    from .models import TallyEntry
    for e in entries:
        TallyEntry.objects.update_or_create(
            voucher_number=e['voucher_number'],
            date=e['date'],
            defaults={
                'ledger':       e['ledger'],
                'voucher_type': e['voucher_type'],
                'amount':       e['amount'],
                'is_credit':    e['is_credit'],
                'narration':    e['narration'],
            }
        )
</code></pre>
<p>The <code>update_or_create</code> pattern is key. The sync runs daily via Celery Beat. If a voucher was already imported, it updates the record. If it's new, it creates it. Running the sync twice never creates duplicates.</p>

<h2>Excel Expense Import</h2>
<p>The operations team kept a separate Excel file for expenses (petrol, office supplies, staff tea — things that never went through Tally). Pandas handles the import with validation:</p>
<pre><code">import pandas as pd
from decimal import Decimal

REQUIRED_COLUMNS = {'Date', 'Category', 'Description', 'Amount'}

def import_expense_excel(file_path: str) -> tuple[list, list]:
    """Returns (valid_rows, error_rows)"""
    df = pd.read_excel(file_path, engine='openpyxl')

    # Validate required columns exist
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    valid, errors = [], []
    for idx, row in df.iterrows():
        row_errors = []
        # Type validation
        try:
            amount = Decimal(str(row['Amount'])).quantize(Decimal('0.01'))
        except Exception:
            row_errors.append(f"Row {idx+2}: Invalid amount '{row['Amount']}'")
        # Date validation
        try:
            date = pd.to_datetime(row['Date']).date()
        except Exception:
            row_errors.append(f"Row {idx+2}: Invalid date '{row['Date']}'")

        if row_errors:
            errors.extend(row_errors)
        else:
            valid.append({'date': date, 'category': str(row['Category']).strip(), 'description': str(row['Description']).strip(), 'amount': amount})
    return valid, errors
</code></pre>
<p>The admin sees row-level error messages before anything is committed. They can fix the Excel and re-upload. Nothing is saved until the whole file validates.</p>

<h2>P&L Report Generation</h2>
<p>With Tally data and expense data both in PostgreSQL, the P&L report is a Django ORM aggregation — no spreadsheet work involved:</p>
<pre><code">from django.db.models import Sum, Q
from .models import TallyEntry, Expense

def generate_pl_report(from_date, to_date):
    # Revenue from Tally (sales vouchers)
    revenue = TallyEntry.objects.filter(
        date__range=(from_date, to_date),
        voucher_type__in=['Sales', 'Receipt'],
        is_credit=True
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Expenses from Tally (purchase vouchers)
    tally_expenses = TallyEntry.objects.filter(
        date__range=(from_date, to_date),
        voucher_type='Payment',
        is_credit=False
    ).values('ledger').annotate(total=Sum('amount'))

    # Direct expenses from Excel import
    direct_expenses = Expense.objects.filter(
        date__range=(from_date, to_date)
    ).values('category').annotate(total=Sum('amount'))

    return {
        'revenue': revenue,
        'tally_expenses': list(tally_expenses),
        'direct_expenses': list(direct_expenses),
        'net_profit': revenue - sum(e['total'] for e in tally_expenses) - sum(e['total'] for e in direct_expenses),
        'generated_at': datetime.now().isoformat(),
    }
</code></pre>
<p>The PDF output uses ReportLab. The Excel export uses openpyxl. Both read from the same aggregation function — the report format is just a presentation layer over the same data.</p>

<h2>The Result</h2>
<p>The first time I showed the client the "Generate Report" button, they clicked it without believing it would work. It produced a formatted, accurate P&L in 48 seconds. They'd been spending 12 hours on the same thing every month for years. That's the kind of improvement that makes a client's day.</p>
    `
  },

  /* ─────────────────────────────────────────────────────────────
     04 — HALF
     ───────────────────────────────────────────────────────────── */
  {
    id:        'vapid-web-push-django',
    slug:      'vapid-web-push-django',
    cat:       'django',
    layout:    'half',
    title:     'Implementing VAPID Web Push Notifications in Django — Without a Mobile App',
    excerpt:   'How I added real-time browser push notifications to Skyline Wheels so the sales team gets alerted the second a customer submits an enquiry — no app, no polling, just the web.',
    date:      'May 12, 2026',
    read:      '8 min read',
    likes:     19,
    comments:  2,
    tags:      ['Django', 'VAPID', 'Web Push', 'Service Worker', 'Skyline Wheels'],
    toc:       ['Why Web Push Instead of SMS/WhatsApp', 'How VAPID Works', 'Service Worker Setup', 'Django Backend (pywebpush)', 'Storing Subscriptions', 'Sending the Notification', 'Gotchas I Hit'],
    body: `
<h2>Why Web Push Instead of SMS/WhatsApp</h2>
<p>On <strong>Skyline Wheels</strong>, the sales team needed to know immediately when a customer submitted an enquiry. I had WhatsApp Business API already integrated for customer follow-ups, but using it for internal sales alerts felt wrong — WhatsApp isn't a work tool in the same way, notifications get lost in personal chats, and there's a per-message cost.</p>
<p>SMS has latency and also costs per message. Email is too slow for "a customer is on the floor right now." Browser push notifications are free, instant, and work even when the browser tab is closed — perfect for a dealership admin sitting at a desktop all day.</p>

<h2>How VAPID Works</h2>
<p>VAPID (Voluntary Application Server Identification) is the authentication layer for web push. Without it, anyone could send push notifications to your users' browsers by guessing their subscription endpoint. VAPID adds a cryptographic signature that proves the push came from your server.</p>
<p>The flow: you generate a VAPID key pair (public + private). The browser uses your public key when creating a push subscription. When you send a push, you sign it with your private key. The browser verifies the signature before delivering the notification.</p>
<pre><code"># Generate VAPID keys once (save these to environment variables)
# pip install pywebpush

from py_vapid import Vapid
vapid = Vapid()
vapid.generate_keys()
# Prints your base64-encoded keys — store in .env, never in code
print("Public:", vapid.public_key.public_bytes(...).decode())
print("Private:", vapid.private_key.private_bytes(...).decode())
</code></pre>

<h2>Service Worker Setup</h2>
<p>The service worker lives at <code>/static/js/sw.js</code>. It handles incoming push events and displays the notification even when the page is not active:</p>
<pre><code">// static/js/sw.js
self.addEventListener('push', function(event) {
  const data = event.data ? event.data.json() : {};
  const options = {
    body:    data.body    || 'New activity on Skyline Wheels',
    icon:    data.icon    || '/static/img/logo-192.png',
    badge:   data.badge   || '/static/img/badge-72.png',
    data:    { url: data.url || '/admin/' },
    actions: [
      { action: 'view', title: 'View Enquiry' },
      { action: 'dismiss', title: 'Dismiss' }
    ]
  };
  event.waitUntil(
    self.registration.showNotification(data.title || 'Skyline Wheels', options)
  );
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  if (event.action === 'view') {
    event.waitUntil(clients.openWindow(event.notification.data.url));
  }
});
</code></pre>
<p>Register the service worker in your main JS. The subscription object (containing the browser's push endpoint) gets POSTed to your Django API and stored in the database:</p>
<pre><code">// main.js — registration
async function subscribeToPush() {
  const reg = await navigator.serviceWorker.register('/static/js/sw.js');
  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY)
  });
  // Send subscription to Django
  await fetch('/api/push/subscribe/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
    body: JSON.stringify(sub.toJSON())
  });
}
</code></pre>

<h2>Django Backend (pywebpush)</h2>
<pre><code"># models.py
class PushSubscription(models.Model):
    user        = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    endpoint    = models.TextField(unique=True)
    p256dh      = models.TextField()
    auth        = models.TextField()
    created_at  = models.DateTimeField(auto_now_add=True)

# views.py — store subscription
class PushSubscribeView(APIView):
    def post(self, request):
        data = request.data
        PushSubscription.objects.update_or_create(
            endpoint=data['endpoint'],
            defaults={
                'user':   request.user if request.user.is_authenticated else None,
                'p256dh': data['keys']['p256dh'],
                'auth':   data['keys']['auth'],
            }
        )
        return Response({'status': 'subscribed'})
</code></pre>

<h2>Sending the Notification</h2>
<pre><code">from pywebpush import webpush, WebPushException
import json, os

def send_push_notification(subscription: PushSubscription, title: str, body: str, url: str = '/admin/'):
    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": { "p256dh": subscription.p256dh, "auth": subscription.auth }
            },
            data=json.dumps({"title": title, "body": body, "url": url}),
            vapid_private_key=os.environ['VAPID_PRIVATE_KEY'],
            vapid_claims={"sub": "mailto:admin@skylinewheels.in"}
        )
    except WebPushException as e:
        if e.response and e.response.status_code == 410:
            # Subscription expired — clean up
            subscription.delete()
        else:
            logger.error(f"Push failed: {e}")

# In the enquiry view — fire after saving
class EnquiryCreateView(CreateAPIView):
    def perform_create(self, serializer):
        enquiry = serializer.save()
        # Notify all staff subscriptions
        for sub in PushSubscription.objects.filter(user__is_staff=True):
            send_push_notification(
                sub,
                title=f"New Enquiry — {enquiry.bike_model}",
                body=f"{enquiry.customer_name} wants to know about {enquiry.bike_model}",
                url=f"/admin/enquiries/{enquiry.id}/"
            )
</code></pre>

<h2>Gotchas I Hit</h2>
<p><strong>1. HTTPS required.</strong> Service workers and push subscriptions only work on HTTPS. On Railway, this is automatic. On development, use a self-signed cert or ngrok.</p>
<p><strong>2. Safari on iOS.</strong> iOS Safari only supports Web Push from iOS 16.4+, and only if the user has added the site to their home screen. For a dealership admin on desktop Chrome, this wasn't an issue, but it's a real constraint to know.</p>
<p><strong>3. 410 Gone responses.</strong> When a user unsubscribes or clears browser data, the push endpoint returns 410. You must handle this by deleting the subscription record — otherwise your send loop will keep failing on dead endpoints and slow down notification delivery.</p>
<p><strong>4. The subscription is per-browser-per-device.</strong> If a staff member uses Chrome on their laptop and Chrome on their phone, you get two separate subscriptions for the same user. Both get notified. This is usually what you want.</p>
    `
  },

  /* ─────────────────────────────────────────────────────────────
     05 — THIRD
     ───────────────────────────────────────────────────────────── */
  {
    id:        'docker-5-service-flowboard',
    slug:      'docker-5-service-flowboard',
    cat:       'devops',
    layout:    'third',
    title:     'What I Learned Setting Up a 5-Service Docker Compose Stack',
    excerpt:   'FlowBoard runs Django, Celery worker, Celery Beat, Redis, and PostgreSQL in Docker Compose. Getting service ordering, health checks, and volume persistence right took several iterations.',
    date:      'May 5, 2026',
    read:      '6 min read',
    likes:     15,
    comments:  2,
    tags:      ['Docker', 'Docker Compose', 'Celery', 'Redis', 'DevOps'],
    toc:       ['The 5 Services', 'Service Ordering with depends_on', 'Health Checks', 'Volume Persistence', 'The Final Compose File'],
    body: `
<h2>The 5 Services</h2>
<p>FlowBoard — my real-time Kanban project management tool — runs across five containers:</p>
<ul>
  <li><strong>web</strong> — Django + Gunicorn, serves the API and WebSocket connections via Daphne</li>
  <li><strong>worker</strong> — Celery worker, processes async tasks (email, report generation)</li>
  <li><strong>beat</strong> — Celery Beat, runs scheduled tasks (daily digest emails, cleanup jobs)</li>
  <li><strong>redis</strong> — Celery broker + Django Channels channel layer + cache</li>
  <li><strong>postgres</strong> — PostgreSQL database</li>
</ul>
<p>Getting five services to start in the right order, stay healthy, and share data correctly is where most Docker Compose setups go wrong.</p>

<h2>Service Ordering with depends_on</h2>
<p><code>depends_on</code> alone isn't enough. By default it only waits for the container to start, not for the service inside it to be ready. PostgreSQL takes a few seconds to initialize after the container starts. If Django's <code>migrate</code> runs before Postgres is actually accepting connections, you get a connection refused error and a failed startup.</p>
<pre><code">services:
  web:
    build: .
    depends_on:
      postgres:
        condition: service_healthy   # ← wait for health check, not just start
      redis:
        condition: service_healthy
    command: >
      sh -c "python manage.py migrate &&
             daphne -b 0.0.0.0 -p 8000 flowboard.asgi:application"
</code></pre>

<h2>Health Checks</h2>
<pre><code">  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB:       flowboard
      POSTGRES_USER:     flowboard
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U flowboard"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
</code></pre>
<p>The health check for Postgres uses <code>pg_isready</code> — it pings the Postgres server and returns 0 only when it's accepting connections. Redis uses <code>redis-cli ping</code> which returns PONG when ready.</p>

<h2>Volume Persistence</h2>
<p>Named volumes keep your data when you restart containers. Without them, every <code>docker-compose down</code> wipes your database. Beginner mistake I made on the first iteration:</p>
<pre><code">volumes:
  postgres_data:    # persists across container restarts and rebuilds
  redis_data:       # persists Redis AOF log if you enable persistence

# Mount in service
  postgres:
    volumes:
      - postgres_data:/var/lib/postgresql/data
  redis:
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes  # enable AOF persistence
</code></pre>
<div class="callout">
  <div class="callout-icon">⚠️</div>
  <div class="callout-text"><code>docker-compose down -v</code> deletes named volumes. <code>docker-compose down</code> (without -v) keeps them. Know the difference before you run it on a server with real data.</div>
</div>

<h2>The Final Compose File</h2>
<p>The complete working docker-compose.yml is in the <a href="https://github.com/Ashwani1611/flowboard" target="_blank" rel="noopener" style="color:var(--cyan)">FlowBoard GitHub repo</a>. The key lesson: Docker Compose is straightforward once you understand that service ordering requires health checks, not just <code>depends_on</code>. That one thing blocked me for about two hours on the first setup.</p>
    `
  },

  /* ─────────────────────────────────────────────────────────────
     06 — THIRD
     ───────────────────────────────────────────────────────────── */
  {
    id:        'dsa-in-real-django-code',
    slug:      'dsa-in-real-django-code',
    cat:       'dsa',
    layout:    'third',
    title:     'DSA Isn\'t Just for Interviews — I Used Min-Heap and Sliding Window in Production',
    excerpt:   'FlowBoard uses a Min-Heap for task prioritization and a Sliding Window algorithm for rolling analytics. Here\'s the actual code and why a sorted queryset wasn\'t the right tool.',
    date:      'Apr 28, 2026',
    read:      '7 min read',
    likes:     27,
    comments:  6,
    tags:      ['DSA', 'Python', 'Algorithms', 'Django', 'FlowBoard'],
    toc:       ['Why I Embedded DSA in Application Code', 'Min-Heap for Task Priority', 'Binary Search for Filtered Lookup', 'Sliding Window for Analytics'],
    body: `
<h2>Why I Embedded DSA in Application Code</h2>
<p>Most developers treat DSA as interview preparation — something you study, pass the test with, and then forget. I wanted to prove (to myself, mostly) that these algorithms have genuine application in real software. So when building FlowBoard, I deliberately found use cases for them instead of defaulting to database queries for everything.</p>
<p>The result: three places in the codebase where a classical algorithm is the right tool, not a query, not a library function — the actual algorithm implemented in Python.</p>

<h2>Min-Heap for Task Priority</h2>
<p>FlowBoard tasks have priority levels (1-5). When a user opens a board, the highest-priority incomplete tasks should appear at the top of each column. The naive approach: <code>Task.objects.filter(board=board).order_by('-priority', 'created_at')</code>. That works. But it re-queries the database every time the sort is needed, and it's O(n log n) for the full sort when you often only need the top-k tasks.</p>
<p>A Min-Heap gives you the highest-priority item in O(1) and inserting a new task is O(log n). If the board has 500 tasks but you only display the top 20, you don't need to sort all 500:</p>
<pre><code">import heapq

class TaskPriorityQueue:
    """
    Min-heap for task prioritization.
    Uses negative priority so highest priority (5) is popped first.
    Tie-break on created_at for FIFO within same priority.
    """
    def __init__(self):
        self._heap = []

    def push(self, task):
        # (neg_priority, created_at_ts, task_id) — tuple comparison for heap
        heapq.heappush(
            self._heap,
            (-task.priority, task.created_at.timestamp(), task.id, task)
        )

    def pop_highest(self):
        """O(log n) — remove and return highest priority task"""
        if self._heap:
            return heapq.heappop(self._heap)[-1]  # last element is the task
        return None

    def peek(self):
        """O(1) — view highest priority without removing"""
        if self._heap:
            return self._heap[0][-1]
        return None

    def top_k(self, k: int) -> list:
        """Return top-k tasks without modifying the heap — O(k log n)"""
        return [heapq.heappop(self._heap)[-1] for _ in range(min(k, len(self._heap)))]

# Usage in the board view
def get_prioritized_tasks(board_id: int, column_id: int, limit: int = 20):
    tasks = Task.objects.filter(board_id=board_id, column_id=column_id, status='active')
    pq = TaskPriorityQueue()
    for task in tasks:
        pq.push(task)
    return pq.top_k(limit)
</code></pre>

<h2>Binary Search for Filtered Lookup</h2>
<p>FlowBoard has a task search with autocomplete. The tag filter allows users to find tasks by exact tag match across a sorted tag index. Binary search on a sorted list is O(log n) vs O(n) for a linear scan:</p>
<pre><code">import bisect

class SortedTagIndex:
    """Maintains a sorted list of (tag, task_id) tuples for O(log n) lookup"""
    def __init__(self):
        self._index = []  # sorted list of (tag_lowercase, task_id)

    def add(self, tag: str, task_id: int):
        bisect.insort(self._index, (tag.lower(), task_id))

    def find_exact(self, tag: str) -> list[int]:
        """Binary search for exact tag — O(log n) to find, O(k) to collect matches"""
        tag = tag.lower()
        lo = bisect.bisect_left(self._index, (tag, 0))
        hi = bisect.bisect_right(self._index, (tag, float('inf')))
        return [task_id for _, task_id in self._index[lo:hi]]

    def find_prefix(self, prefix: str) -> list[int]:
        """Find all tasks with tags starting with prefix — for autocomplete"""
        prefix = prefix.lower()
        lo = bisect.bisect_left(self._index, (prefix, 0))
        results = []
        while lo < len(self._index) and self._index[lo][0].startswith(prefix):
            results.append(self._index[lo][1])
            lo += 1
        return results
</code></pre>

<h2>Sliding Window for Analytics</h2>
<p>The analytics panel shows task completion rate over a rolling 7-day window. The naive approach recalculates the full window from scratch on every request. A sliding window algorithm maintains a running count — as new data enters from the right, old data exits from the left:</p>
<pre><code">from collections import deque
from datetime import date, timedelta

def rolling_completion_rate(
    completions: list[tuple[date, int]],  # (date, completed_count) sorted by date
    window_days: int = 7
) -> list[dict]:
    """
    O(n) — single pass through completions list.
    Returns daily rolling average completion rate.
    """
    window = deque()
    window_total = 0
    results = []

    for current_date, count in completions:
        # Add current day to window
        window.append((current_date, count))
        window_total += count

        # Remove days outside the window (slide left boundary)
        cutoff = current_date - timedelta(days=window_days - 1)
        while window and window[0][0] < cutoff:
            _, old_count = window.popleft()
            window_total -= old_count

        results.append({
            'date':            current_date.isoformat(),
            'rolling_avg':     round(window_total / len(window), 2),
            'window_size':     len(window),
            'tasks_completed': count,
        })

    return results
</code></pre>
<p>The deque makes left-removal O(1). The whole function is O(n) — one pass through the data. The same result from a SQL window function would work too, but this gives you the algorithm in Python where you can inspect, test, and extend it easily.</p>
    `
  },

  /* ─────────────────────────────────────────────────────────────
     07 — THIRD
     ───────────────────────────────────────────────────────────── */
  {
    id:        'postgresql-schema-design-government',
    slug:      'postgresql-schema-design-government',
    cat:       'system-design',
    layout:    'third',
    title:     'Schema Design Lessons from a Government Property Tax System',
    excerpt:   'Designing the database for a system that 5+ municipal corporations depend on — where getting it wrong costs citizens\' records — taught me schema design principles no tutorial covers.',
    date:      'Apr 15, 2026',
    read:      '8 min read',
    likes:     22,
    comments:  3,
    tags:      ['PostgreSQL', 'Schema Design', 'DBMS', 'Government', 'Normalization'],
    toc:       ['Design Under Real Constraints', 'Normalization for Multi-City Tax Rates', 'Audit Columns on Every Table', 'Soft Delete vs Hard Delete', 'Index Strategy', 'What I\'d Do Differently'],
    body: `
<h2>Design Under Real Constraints</h2>
<p>When I was Database Developer at GIS Consortium India, the system I designed would store property records for 5+ municipal corporations — real citizens, real addresses, real tax liability. If I made a schema decision that caused data loss or corrupted records, the consequences weren't a rollback in a staging environment. They were people's government records.</p>
<p>That constraint shapes how you think about every design decision. This post covers the schema patterns I learned that go beyond what normalization theory teaches you.</p>

<h2>Normalization for Multi-City Tax Rates</h2>
<p>The hardest design challenge: each of 10+ cities had different tax rate configurations. Residential, commercial, and industrial properties each had different rates. Rates changed annually. How do you model this without duplicating logic?</p>
<pre><code">-- Cities (each municipal corporation)
CREATE TABLE municipality (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(10) UNIQUE NOT NULL,  -- 'LKO', 'AGR', 'VNS'
    name        VARCHAR(100) NOT NULL,
    state       VARCHAR(50)  NOT NULL
);

-- Tax rate configurations — versioned by year
CREATE TABLE tax_rate_config (
    id              SERIAL PRIMARY KEY,
    municipality_id INTEGER REFERENCES municipality(id),
    property_type   VARCHAR(20) NOT NULL,  -- 'residential','commercial','industrial'
    zone_category   VARCHAR(10) NOT NULL,  -- 'A','B','C','D'
    effective_from  DATE NOT NULL,
    effective_to    DATE,                   -- NULL = currently active
    rate_per_sqft   DECIMAL(8,4) NOT NULL,
    rebate_pct      DECIMAL(5,2) DEFAULT 0,
    CONSTRAINT no_rate_overlap EXCLUDE USING gist (
        municipality_id WITH =,
        property_type   WITH =,
        zone_category   WITH =,
        daterange(effective_from, COALESCE(effective_to, 'infinity')) WITH &&
    )
);

-- Properties reference the config — tax is computed, never stored
CREATE TABLE property (
    id              SERIAL PRIMARY KEY,
    survey_number   VARCHAR(50) UNIQUE NOT NULL,
    municipality_id INTEGER REFERENCES municipality(id),
    property_type   VARCHAR(20) NOT NULL,
    zone_category   VARCHAR(10) NOT NULL,
    area_sqft       DECIMAL(10,2) NOT NULL,
    -- Tax is NOT stored — computed at query time from rate config
    -- This ensures rate changes automatically apply on next calculation
);
</code></pre>
<p>The <code>EXCLUDE USING gist</code> constraint prevents overlapping rate configs for the same municipality + type + zone combination. PostgreSQL enforces this at the database level — no application code needed to check for conflicts.</p>

<h2>Audit Columns on Every Table</h2>
<p>Every single table in the schema has these four columns:</p>
<pre><code">created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
created_by   INTEGER REFERENCES auth_user(id)
updated_by   INTEGER REFERENCES auth_user(id)
</code></pre>
<p>And a trigger that updates <code>updated_at</code> automatically on every row change. This seems like overhead until a municipality calls asking why a property record changed and when. With audit columns, you can answer that in one query. Without them, you can't answer it at all.</p>

<h2>Soft Delete vs Hard Delete</h2>
<p>In government data, you don't delete records. You mark them inactive. We use a <code>deleted_at</code> column:</p>
<pre><code">deleted_at   TIMESTAMPTZ  -- NULL = active, timestamp = soft-deleted

-- All queries filter active records
CREATE VIEW active_properties AS
    SELECT * FROM property WHERE deleted_at IS NULL;

-- "Delete" a record
UPDATE property SET deleted_at = NOW(), updated_by = $1 WHERE id = $2;
</code></pre>
<p>Why? Because "delete this incorrect survey record" from a supervisor today doesn't mean that record never existed. Audit requirements for government systems typically require a full history of what data existed and when.</p>

<h2>Index Strategy</h2>
<p>Three index decisions that made a real performance difference:</p>
<pre><code">-- 1. Partial index for active records (most queries filter on deleted_at IS NULL)
CREATE INDEX idx_property_active
    ON property(municipality_id, zone_category)
    WHERE deleted_at IS NULL;

-- 2. Composite index for the most common query pattern
CREATE INDEX idx_property_survey_lookup
    ON property(municipality_id, survey_number)
    WHERE deleted_at IS NULL;

-- 3. Index on tax_rate_config for rate lookup (date range query)
CREATE INDEX idx_tax_rate_lookup
    ON tax_rate_config(municipality_id, property_type, zone_category, effective_from);
</code></pre>
<p>The partial index is the most important one. Full-table indexes include deleted records. Since 99% of queries filter <code>WHERE deleted_at IS NULL</code>, the partial index is smaller, faster, and only indexes what gets queried.</p>

<h2>What I'd Do Differently</h2>
<p>I'd add event sourcing for tax calculation history. Currently, if a rate changes, we can recalculate what a property's tax should be at any point in time from the rate config versions. But we can't see a log of "here's what we actually computed on March 15th 2024." For audit purposes, storing computed tax amounts in an immutable ledger table (one row per calculation event) would be better than relying on reconstruction from config history.</p>
    `
  },

  /* ─────────────────────────────────────────────────────────────
     08 — THIRD
     ───────────────────────────────────────────────────────────── */
  {
    id:        'whatsapp-business-api-django',
    slug:      'whatsapp-business-api-django',
    cat:       'django',
    layout:    'third',
    title:     'WhatsApp Business API in Django: Gotchas and Setup for a Real Dealership',
    excerpt:   'Integrating WhatsApp Business API into Skyline Wheels for customer follow-ups. The documentation gaps that cost me a day, and how to avoid them.',
    date:      'Apr 8, 2026',
    read:      '6 min read',
    likes:     17,
    comments:  2,
    tags:      ['WhatsApp API', 'Django', 'Skyline Wheels', 'Automation'],
    toc:       ['Why WhatsApp for a Dealership', 'Business API vs Personal API', 'Template Messages vs Free-Form', 'Django Integration', 'The Gotchas', 'Webhook Verification'],
    body: `
<h2>Why WhatsApp for a Dealership</h2>
<p>On <strong>Skyline Wheels</strong>, when a customer submits a service booking or enquiry, the business needed to send a confirmation and follow-up. Email open rates for automotive businesses are typically under 20%. WhatsApp open rates are over 90%. The dealership owner knew his customers read WhatsApp. So that's where the follow-ups needed to go.</p>

<h2>Business API vs Personal API</h2>
<p>There are several unofficial "WhatsApp APIs" floating around (wa-automate, Baileys, etc.) that work by running a headless WhatsApp Web session. Don't use these in production. Meta actively bans numbers that use unofficial clients. For a business's primary contact number, that's unacceptable risk.</p>
<p>The official Meta WhatsApp Business API (Cloud API) is the right approach. It's free for the first 1000 user-initiated conversations per month. For a dealership sending ~50-100 messages per month, the cost is zero.</p>

<h2>Template Messages vs Free-Form</h2>
<p>This is the gotcha that the documentation doesn't emphasize clearly enough. <strong>You can only send template messages to customers who haven't messaged you in the last 24 hours.</strong> Free-form messages (any text you want) are only allowed within a 24-hour window after the customer last messaged you.</p>
<p>For automated follow-ups (booking confirmations, enquiry responses that fire immediately when a form is submitted), you must use approved message templates. Templates must be submitted to Meta for approval before use — usually takes 1-2 days.</p>
<pre><code">APPROVED TEMPLATE EXAMPLE:
Name: skyline_booking_confirmation
Body: "Hi {{1}}, your service booking for your {{2}} on {{3}} at Skyline Wheels
       is confirmed. Our team will contact you at {{4}} to finalize the slot.
       Reply STOP to opt out."
Variables: [customer_name, bike_model, date, phone_number]
</code></pre>

<h2>Django Integration</h2>
<pre><code">import requests, os

WHATSAPP_API_URL = "https://graph.facebook.com/v19.0/{phone_number_id}/messages"
ACCESS_TOKEN = os.environ['WHATSAPP_ACCESS_TOKEN']
PHONE_NUMBER_ID = os.environ['WHATSAPP_PHONE_NUMBER_ID']

def send_whatsapp_template(to: str, template_name: str, language: str, components: list) -> bool:
    """
    to: phone number in E.164 format (+919876543210)
    components: list of template variable substitutions
    """
    url = WHATSAPP_API_URL.format(phone_number_id=PHONE_NUMBER_ID)
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language},
            "components": components
        }
    }
    response = requests.post(
        url,
        json=payload,
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
        timeout=10
    )
    if response.status_code != 200:
        logger.error(f"WhatsApp send failed: {response.text}")
        return False
    return True

# Usage on booking creation
def send_booking_confirmation(booking):
    send_whatsapp_template(
        to=booking.customer_phone,
        template_name="skyline_booking_confirmation",
        language="en",
        components=[{
            "type": "body",
            "parameters": [
                {"type": "text", "text": booking.customer_name},
                {"type": "text", "text": booking.bike_model},
                {"type": "text", "text": booking.preferred_date.strftime("%d %b %Y")},
                {"type": "text", "text": booking.customer_phone},
            ]
        }]
    )
</code></pre>

<h2>The Gotchas</h2>
<p><strong>1. Phone number format.</strong> The API requires E.164 format (+91XXXXXXXXXX). Indian mobile numbers entered by customers are often 10 digits without the country code. Clean and validate before sending:</p>
<pre><code">import re

def to_e164(phone: str, country_code: str = "91") -> str | None:
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 10:
        return f"+{country_code}{digits}"
    if len(digits) == 12 and digits.startswith(country_code):
        return f"+{digits}"
    return None  # invalid — don't attempt send
</code></pre>
<p><strong>2. Template approval takes time.</strong> Submit your templates before the project launch date, not the day before. Meta took 28 hours to approve ours. If you launch without approved templates, your automated messages can't send.</p>
<p><strong>3. Rate limits.</strong> The free tier limits you to 250 unique phone numbers per day. For a dealership sending 50 messages a month, irrelevant. For a large campaign, plan around it.</p>

<h2>Webhook Verification</h2>
<p>Meta requires you to set up a webhook endpoint that receives delivery receipts and incoming messages. The verification flow is a one-time GET request with a <code>hub.challenge</code> token you must echo back:</p>
<pre><code">class WhatsAppWebhookView(View):
    def get(self, request):
        """Meta verification — called once during webhook setup"""
        mode      = request.GET.get('hub.mode')
        token     = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        if mode == 'subscribe' and token == os.environ['WHATSAPP_VERIFY_TOKEN']:
            return HttpResponse(challenge, content_type='text/plain')
        return HttpResponse(status=403)

    def post(self, request):
        """Incoming messages and delivery receipts"""
        # Process webhook payload — log delivery status, handle replies
        import json
        payload = json.loads(request.body)
        # ... process delivery receipts, incoming messages
        return HttpResponse(status=200)
</code></pre>
<p>Always return 200 quickly on POST webhooks. Meta will retry failed deliveries, and if your endpoint is slow it will retry aggressively and potentially disable the webhook.</p>
    `
  },

];
