/* ═══════════════════════════════════════════════════════════════
   api.js — FastAPI Blog Backend Client
   Ashwani Kumar Portfolio v4

   SETUP:
   1. Add this BEFORE main.js in every HTML file:
      <script src="api.js"></script>
   2. To override API base (e.g. in production), set this before
      loading api.js:
      <script>window.AK_API_BASE = 'https://your-api.railway.app/api/v1';</script>
   3. All AI chat routes through your FastAPI /ai/chat endpoint —
      no Anthropic key exposed client-side.
═══════════════════════════════════════════════════════════════ */

const API_BASE = (() => {
  if (typeof window !== 'undefined' && window.AK_API_BASE) return window.AK_API_BASE;
  const local = location.hostname === 'localhost' || location.hostname === '127.0.0.1';
  return '/api/v1';
})();

/* ── Token helpers ───────────────────────────────────────────── */
const Auth = {
  getToken()        { try { return localStorage.getItem('ak_token'); }    catch { return null; } },
  setToken(t)       { try { localStorage.setItem('ak_token', t); }        catch {} },
  setRefresh(t)     { try { localStorage.setItem('ak_refresh', t); }      catch {} },
  getRefresh()      { try { return localStorage.getItem('ak_refresh'); }  catch { return null; } },
  clear()           { try { localStorage.removeItem('ak_token'); localStorage.removeItem('ak_refresh'); } catch {} },
  authHeaders()     { const t = this.getToken(); return t ? { 'Authorization': `Bearer ${t}` } : {}; },
};

/* ── Core request helper ─────────────────────────────────────── */
async function apiRequest(endpoint, options = {}) {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...Auth.authHeaders(),
        ...options.headers,
      },
      ...options,
    });
    if (res.status === 204) return null;
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return await res.json();
  } catch (e) {
    console.warn(`API [${endpoint}]:`, e.message);
    return null;
  }
}

/* ════════════════════════════════════════════════════════════════
   AUTH
════════════════════════════════════════════════════════════════ */
async function apiRegister(username, email, password) {
  return apiRequest('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ username, email, password }),
  });
}

async function apiLogin(email, password) {
  const data = await apiRequest('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  if (data?.access_token) {
    Auth.setToken(data.access_token);
    Auth.setRefresh(data.refresh_token);
  }
  return data;
}

async function apiRefreshToken() {
  const refresh_token = Auth.getRefresh();
  if (!refresh_token) return null;
  const data = await apiRequest('/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refresh_token }),
  });
  if (data?.access_token) Auth.setToken(data.access_token);
  return data;
}

function apiLogout() {
  Auth.clear();
}

/* ════════════════════════════════════════════════════════════════
   POSTS
════════════════════════════════════════════════════════════════ */

/**
 * Fetch posts list. Falls back to static POSTS array if backend
 * is unreachable, so the portfolio works offline / locally.
 */
async function apiGetPosts(params = {}) {
  const q = new URLSearchParams(params).toString();
  const data = await apiRequest(`/posts${q ? '?' + q : ''}`);
  if (!data && typeof POSTS !== 'undefined') return POSTS;
  return data || [];
}

/**
 * Fetch a single post by slug and increment view count.
 * Falls back to static POSTS if backend is unreachable.
 */
async function apiGetPost(slug) {
  const data = await apiRequest(`/posts/${slug}`);
  if (!data && typeof POSTS !== 'undefined') {
    return POSTS.find(p => p.id === slug || p.slug === slug) || null;
  }
  return data;
}

/* ════════════════════════════════════════════════════════════════
   LIKES  (IP-based anon or user if logged in)
════════════════════════════════════════════════════════════════ */
async function apiTogglePostLike(slug) {
  return apiRequest(`/posts/${slug}/like`, { method: 'POST' });
}

async function apiToggleCommentLike(commentId) {
  return apiRequest(`/comments/${commentId}/like`, { method: 'POST' });
}

/* ════════════════════════════════════════════════════════════════
   COMMENTS
════════════════════════════════════════════════════════════════ */
async function apiGetComments(slug) {
  return apiRequest(`/posts/${slug}/comments`);
}

async function apiPostComment(slug, body, guestName = null, guestEmail = null) {
  return apiRequest(`/posts/${slug}/comments`, {
    method: 'POST',
    body: JSON.stringify({
      body,
      guest_name:  guestName  || undefined,
      guest_email: guestEmail || undefined,
    }),
  });
}

/* ════════════════════════════════════════════════════════════════
   NEWSLETTER
════════════════════════════════════════════════════════════════ */
async function apiSubscribeNewsletter(email) {
  return apiRequest('/newsletter/subscribe', {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
}

/* ════════════════════════════════════════════════════════════════
   AI CHAT
   Routes through your FastAPI backend — no API key client-side.
   messages: [{ role: 'user'|'assistant', content: '...' }]
════════════════════════════════════════════════════════════════ */
async function apiAIChat(messages, postId = null) {
  const payload = { messages: messages.slice(-20) };
  if (postId) payload.post_id = postId;
  console.log('AI payload:', JSON.stringify(payload));
  return apiRequest('/ai/chat', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/* ════════════════════════════════════════════════════════════════
   INTEGRATION HELPERS
════════════════════════════════════════════════════════════════ */

async function initLiveBlogGrid() {
  const posts = await apiGetPosts();
  if (typeof renderAll === 'function') renderAll(posts);
}

function initLiveNewsletter() {
  const btn   = document.getElementById('nl-btn');
  const input = document.getElementById('nl-email');
  const msg   = document.getElementById('nl-msg');
  if (!btn) return;

  btn.addEventListener('click', async () => {
    const email = input?.value.trim();
    if (!email || !email.includes('@')) return;
    btn.textContent = '...';
    btn.disabled = true;
    await apiSubscribeNewsletter(email);
    btn.textContent = 'Subscribe';
    btn.disabled = false;
    if (input) input.value = '';
    if (msg)  { msg.style.display = 'block'; setTimeout(() => msg.style.display = 'none', 3000); }
  });
}

async function apiLoadPost(slugOrId) {
  const live = await apiGetPost(slugOrId);
  if (live) return live;
  if (typeof POSTS !== 'undefined') {
    return POSTS.find(p => p.id === slugOrId || p.slug === slugOrId) || POSTS[0];
  }
  return null;
}

function initLivePostLike(slug, baseCount) {
  const btn   = document.getElementById('pab-like');
  const count = document.getElementById('pab-count');
  if (!btn) return;

  btn.addEventListener('click', async () => {
    const res = await apiTogglePostLike(slug);
    if (res) {
      btn.classList.toggle('liked', res.liked);
      btn.querySelector('svg')?.setAttribute('fill', res.liked ? 'currentColor' : 'none');
      if (count) count.textContent = res.like_count;
    } else {
      const liked = btn.classList.toggle('liked');
      btn.querySelector('svg')?.setAttribute('fill', liked ? 'currentColor' : 'none');
      if (count) count.textContent = baseCount + (liked ? 1 : 0);
    }
    btn.style.transform = 'scale(1.15)';
    setTimeout(() => btn.style.transform = '', 200);
  });
}

async function loadLiveComments(slug) {
  const list    = document.getElementById('comments-list');
  const countEl = document.getElementById('comment-count');
  if (!list) return;

  const comments = await apiGetComments(slug);
  if (!comments) return;

  if (countEl) countEl.textContent = comments.length;

  const AVATAR_COLORS = ['#00e5c0','#a78bfa','#f4b942','#f05f7a','#4ade80','#60a5fa'];
  const avatarColor = name => AVATAR_COLORS[name.charCodeAt(0) % AVATAR_COLORS.length];

  list.innerHTML = comments.map(c => `
    <div class="comment-item" data-id="${c.id}">
      <div class="comment-header">
        <div class="comment-avatar" style="background:${avatarColor(c.display_name)};color:#05080c">
          ${c.display_name[0].toUpperCase()}
        </div>
        <div><div class="comment-name">${c.display_name}</div></div>
        <div class="comment-date">${new Date(c.created_at).toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'})}</div>
      </div>
      <div class="comment-text">${c.body}</div>
      <div class="comment-footer">
        <button class="comment-like" data-id="${c.id}">❤️ ${c.like_count}</button>
        ${c.ai_reply ? `<span class="ai-reply-tag">✦ AI replied</span>` : ''}
      </div>
      ${c.ai_reply ? `
        <div style="margin-top:12px;padding:14px 18px;background:rgba(167,139,250,.06);border:1px solid rgba(167,139,250,.15);border-radius:8px;">
          <div style="font-family:var(--font-mono);font-size:9px;color:#a78bfa;margin-bottom:6px;letter-spacing:.1em">✦ ASHWANI REPLIED</div>
          <div style="font-size:13px;color:var(--text2);line-height:1.7">${c.ai_reply}</div>
        </div>` : ''}
    </div>`).join('');

  list.querySelectorAll('.comment-like').forEach(btn => {
    btn.addEventListener('click', async () => {
      const res = await apiToggleCommentLike(btn.dataset.id);
      if (res) {
        btn.classList.toggle('liked', res.liked);
        btn.textContent = `❤️ ${res.like_count}`;
      } else {
        const n = parseInt(btn.textContent.replace(/\D/g, '')) || 0;
        btn.classList.toggle('liked');
        btn.textContent = `❤️ ${btn.classList.contains('liked') ? n + 1 : n}`;
      }
    });
  });
}

function initLiveCommentForm(slug) {
  const submitBtn = document.getElementById('cf-submit');
  if (!submitBtn) return;

  submitBtn.addEventListener('click', async () => {
    const name  = document.getElementById('cf-name')?.value.trim();
    const email = document.getElementById('cf-email')?.value.trim();
    const body  = document.getElementById('cf-msg')?.value.trim();

    if (!name || !body) {
      ['cf-name','cf-msg'].forEach(id => {
        const el = document.getElementById(id);
        if (el && !el.value.trim()) {
          el.style.borderColor = 'var(--red)';
          setTimeout(() => el.style.borderColor = '', 2000);
        }
      });
      return;
    }

    submitBtn.textContent = 'Posting...';
    submitBtn.disabled = true;

    const isLoggedIn = !!Auth.getToken();
    const res = await apiPostComment(
      slug, body,
      isLoggedIn ? null : name,
      isLoggedIn ? null : (email || null),
    );

    submitBtn.textContent = 'Post Comment';
    submitBtn.disabled = false;

    if (res) {
      document.getElementById('cf-name').value  = '';
      document.getElementById('cf-email').value = '';
      document.getElementById('cf-msg').value   = '';
      await loadLiveComments(slug);
    }
  });
}

/* ════════════════════════════════════════════════════════════════
   EXPORT
════════════════════════════════════════════════════════════════ */
window.AK = {
  Auth,
  apiLogin, apiLogout, apiRegister, apiRefreshToken,
  apiGetPosts, apiGetPost,
  apiTogglePostLike, apiToggleCommentLike,
  apiGetComments, apiPostComment,
  apiSubscribeNewsletter,
  apiAIChat,
  initLiveBlogGrid, initLiveNewsletter,
  apiLoadPost, initLivePostLike,
  loadLiveComments, initLiveCommentForm,
};