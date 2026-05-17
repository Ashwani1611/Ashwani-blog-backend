/* ═══════════════════════════════════════
   ASHWANI KUMAR — PORTFOLIO v4
   main.js — Shared Interactivity
═══════════════════════════════════════ */

/* ── CURSOR ── */
(function initCursor() {
  const dot  = document.getElementById('cursor');
  const ring = document.getElementById('cursor-ring');
  if (!dot || !ring) return;
  let mx = -100, my = -100, rx = -100, ry = -100;
  document.addEventListener('mousemove', e => {
    mx = e.clientX; my = e.clientY;
    dot.style.left = mx + 'px'; dot.style.top = my + 'px';
  });
  document.addEventListener('mousedown', () => ring.classList.add('click'));
  document.addEventListener('mouseup',   () => ring.classList.remove('click'));
  document.querySelectorAll('a,button,[data-hover]').forEach(el => {
    el.addEventListener('mouseenter', () => { dot.classList.add('hover');  ring.classList.add('hover'); });
    el.addEventListener('mouseleave', () => { dot.classList.remove('hover'); ring.classList.remove('hover'); });
  });
  (function raf() {
    rx += (mx - rx) * .11; ry += (my - ry) * .11;
    ring.style.left = rx + 'px'; ring.style.top = ry + 'px';
    requestAnimationFrame(raf);
  })();
})();

/* ── NAV SCROLL ── */
(function initNav() {
  const nav = document.getElementById('nav');
  if (!nav) return;
  const onScroll = () => nav.classList.toggle('solid', window.scrollY > 30);
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  const btn  = document.getElementById('hamburger');
  const menu = document.getElementById('mobile-menu');
  if (btn && menu) {
    btn.addEventListener('click', () => {
      btn.classList.toggle('open');
      menu.classList.toggle('open');
      document.body.style.overflow = menu.classList.contains('open') ? 'hidden' : '';
    });
    menu.querySelectorAll('a').forEach(a => {
      a.addEventListener('click', () => {
        btn.classList.remove('open');
        menu.classList.remove('open');
        document.body.style.overflow = '';
      });
    });
  }
})();

/* ── THEME TOGGLE ── */
(function initTheme() {
  const root     = document.documentElement;
  const navRight = document.querySelector('.nav-right');
  if (navRight) {
    navRight.insertAdjacentHTML('afterbegin', `
      <button id="theme-toggle" aria-label="Toggle theme">
        <span class="icon-sun">☀️</span>
        <span class="icon-moon">🌙</span>
      </button>
    `);
  }
  const btn = document.getElementById('theme-toggle');
  const saved       = localStorage.getItem('theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  root.setAttribute('data-theme', saved || (prefersDark ? 'dark' : 'light'));

  btn?.addEventListener('click', () => {
    const next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
  });

  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
    if (!localStorage.getItem('theme'))
      root.setAttribute('data-theme', e.matches ? 'dark' : 'light');
  });
})();

/* ── SCROLL PROGRESS ── */
(function initProgress() {
  const bar = document.getElementById('scroll-progress');
  if (!bar) return;
  window.addEventListener('scroll', () => {
    const pct = window.scrollY / (document.documentElement.scrollHeight - window.innerHeight) * 100;
    bar.style.width = Math.min(pct, 100) + '%';
  }, { passive: true });
})();

/* ── PARTICLE CANVAS ── */
(function initCanvas() {
  const canvas = document.getElementById('bg-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let W, H;

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener('resize', resize);

  const N = window.innerWidth < 700 ? 40 : 70;
  const particles = Array.from({ length: N }, () => ({
    x:  Math.random() * window.innerWidth,
    y:  Math.random() * window.innerHeight,
    vx: (Math.random() - .5) * .25,
    vy: (Math.random() - .5) * .25,
    r:  Math.random() * 1.2 + .4,
    o:  Math.random() * .35 + .08,
  }));

  let mouseX = W / 2, mouseY = H / 2;
  document.addEventListener('mousemove', e => { mouseX = e.clientX; mouseY = e.clientY; });

  function draw() {
    ctx.clearRect(0, 0, W, H);
    const ox = (mouseX / W - .5) * 18;
    const oy = (mouseY / H - .5) * 18;
    particles.forEach(p => {
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0) p.x = W; if (p.x > W) p.x = 0;
      if (p.y < 0) p.y = H; if (p.y > H) p.y = 0;
      ctx.beginPath();
      ctx.arc(p.x + ox * .25, p.y + oy * .25, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(0,229,192,${p.o})`;
      ctx.fill();
    });
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const a = particles[i], b = particles[j];
        const dist = Math.hypot(a.x - b.x, a.y - b.y);
        if (dist < 110) {
          ctx.beginPath();
          ctx.moveTo(a.x + ox * .25, a.y + oy * .25);
          ctx.lineTo(b.x + ox * .25, b.y + oy * .25);
          ctx.strokeStyle = `rgba(0,229,192,${.05 * (1 - dist / 110)})`;
          ctx.lineWidth = .5; ctx.stroke();
        }
      }
    }
    requestAnimationFrame(draw);
  }
  draw();
})();

/* ── PAGE TRANSITIONS ── */
(function initTransitions() {
  const overlay = document.getElementById('page-transition');
  const label   = document.getElementById('pt-label');
  if (!overlay) return;

  overlay.style.transition    = 'transform .55s cubic-bezier(.76,0,.24,1)';
  overlay.style.transformOrigin = 'top';
  overlay.style.transform     = 'scaleY(1)';
  setTimeout(() => { overlay.style.transform = 'scaleY(0)'; }, 50);

  document.querySelectorAll('a[href]').forEach(link => {
    const href = link.getAttribute('href');
    if (!href || href.startsWith('#') || href.startsWith('http') ||
        href.startsWith('mailto') || link.target === '_blank') return;
    link.addEventListener('click', e => {
      e.preventDefault();
      if (label) {
        label.textContent = '→ ' + href.replace('.html','').replace('/','');
        label.style.opacity = '1';
      }
      overlay.style.transformOrigin = 'bottom';
      overlay.style.transform = 'scaleY(1)';
      setTimeout(() => { window.location.href = href; }, 580);
    });
  });
})();

/* ── SCROLL REVEAL ── */
(function initReveal() {
  const els = document.querySelectorAll('.reveal, .reveal-left, .reveal-right');
  if (!els.length) return;
  const io = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        const delay = e.target.dataset.delay || 0;
        setTimeout(() => e.target.classList.add('in'), +delay);
        io.unobserve(e.target);
      }
    });
  }, { threshold: .1 });
  els.forEach(el => io.observe(el));
})();

/* ── TEXT SCRAMBLE ── */
class TextScramble {
  constructor(el) {
    this.el    = el;
    this.chars = '!<>-_\\/[]{}—=+*^?#アイウエオカキ';
    this.update = this.update.bind(this);
  }
  setText(newText) {
    const old = this.el.innerText;
    const len = Math.max(old.length, newText.length);
    const p   = new Promise(r => (this.resolve = r));
    this.queue = Array.from({ length: len }, (_, i) => ({
      from:  old[i]     || '',
      to:    newText[i] || '',
      start: Math.floor(Math.random() * 18),
      end:   Math.floor(Math.random() * 18) + 18,
      char:  ''
    }));
    cancelAnimationFrame(this.raf);
    this.frame = 0;
    this.update();
    return p;
  }
  update() {
    let out = '', done = 0;
    this.queue.forEach(q => {
      if (this.frame >= q.end) { done++; out += q.to; }
      else if (this.frame >= q.start) {
        if (!q.char || Math.random() < .28)
          q.char = this.chars[Math.floor(Math.random() * this.chars.length)];
        out += `<span style="color:var(--cyan);opacity:.6">${q.char}</span>`;
      } else out += q.from;
    });
    this.el.innerHTML = out;
    if (done < this.queue.length) {
      this.frame++;
      this.raf = requestAnimationFrame(this.update);
    } else this.resolve();
  }
}
window.TextScramble = TextScramble;

/* ── TYPEWRITER ── */
function initTypewriter(el, words, speed = 80, pause = 2200) {
  if (!el) return;
  let wi = 0, ci = 0, del = false;
  function tick() {
    const w = words[wi];
    el.textContent = del ? w.slice(0, ci - 1) : w.slice(0, ci + 1);
    del ? ci-- : ci++;
    if (!del && ci > w.length)  { del = true; setTimeout(tick, pause); return; }
    if (del  && ci === 0)       { del = false; wi = (wi + 1) % words.length; }
    setTimeout(tick, del ? 35 : speed);
  }
  tick();
}
window.initTypewriter = initTypewriter;

/* ── MAGNETIC BUTTON ── */
document.querySelectorAll('[data-magnetic]').forEach(el => {
  el.addEventListener('mousemove', e => {
    const r = el.getBoundingClientRect();
    const x = (e.clientX - r.left - r.width  / 2) * .35;
    const y = (e.clientY - r.top  - r.height / 2) * .35;
    el.style.transform = `translate(${x}px,${y}px)`;
  });
  el.addEventListener('mouseleave', () => { el.style.transform = ''; });
});

/* ── COUNTER ANIMATION ── */
function animCounter(el) {
  const target = parseInt(el.dataset.count);
  const suffix = el.dataset.suffix || '';
  const dur    = 1800;
  const start  = performance.now();
  (function tick(now) {
    const t    = Math.min((now - start) / dur, 1);
    const ease = 1 - Math.pow(1 - t, 3);
    el.textContent = Math.round(ease * target) + suffix;
    if (t < 1) requestAnimationFrame(tick);
  })(start);
}
document.querySelectorAll('[data-count]').forEach(el => {
  new IntersectionObserver(entries => {
    if (entries[0].isIntersecting) { animCounter(el); }
  }, { threshold: .5 }).observe(el);
});

/* ── ACTIVE NAV LINK ── */
(function setActiveNav() {
  const path = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-center a').forEach(a => {
    const href = a.getAttribute('href').split('/').pop();
    if (href === path || (path === '' && href === 'index.html'))
      a.classList.add('active');
  });
})();