/* Studforge — Smooth Interactions v2 */
'use strict';

// ══════════════════════════════════════════════════════
// 1. Orange loading bar (shows during navigation)
// ══════════════════════════════════════════════════════

const loadBar = (() => {
  const el = document.createElement('div');
  el.style.cssText =
    'position:fixed;top:0;left:0;right:0;height:2px;' +
    'background:#f97316;width:0;z-index:9999;pointer-events:none;' +
    'box-shadow:0 0 14px rgba(249,115,22,.8),0 0 4px rgba(249,115,22,.4);' +
    'transition:width .5s cubic-bezier(.4,0,.2,1),opacity .38s ease;' +
    'will-change:width,opacity;';
  document.body.appendChild(el);

  let tid;

  return {
    start() {
      clearTimeout(tid);
      el.style.transition = 'none';
      el.style.width = '0';
      el.style.opacity = '1';
      requestAnimationFrame(() => {
        el.style.transition = 'width .55s cubic-bezier(.4,0,.2,1),opacity .38s ease';
        el.style.width = '62%';
      });
    },
    done() {
      el.style.transition = 'width .22s ease,opacity .4s ease';
      el.style.width = '100%';
      tid = setTimeout(() => {
        el.style.opacity = '0';
        setTimeout(() => { el.style.width = '0'; }, 400);
      }, 160);
    }
  };
})();

// ══════════════════════════════════════════════════════
// 2. Page exit + entrance transitions
// ══════════════════════════════════════════════════════

const getContent = () => document.querySelector('.content');

function enterPage() {
  const c = getContent();
  if (!c) return;
  c.style.cssText += ';opacity:0;transform:translateY(12px);';
  requestAnimationFrame(() => {
    c.style.transition = 'opacity .3s cubic-bezier(.4,0,.2,1),transform .32s cubic-bezier(.4,0,.2,1)';
    c.style.opacity = '1';
    c.style.transform = 'translateY(0)';
  });
}

// Intercept clicks on internal links
document.addEventListener('click', e => {
  const link = e.target.closest('a[href]');
  if (!link) return;

  const href = link.getAttribute('href') || '';
  if (
    !href ||
    href.startsWith('#') ||
    href.startsWith('mailto:') ||
    href.startsWith('tel:') ||
    link.target === '_blank' ||
    e.ctrlKey || e.metaKey || e.shiftKey
  ) return;

  try {
    const url = new URL(href, location.origin);
    if (url.origin !== location.origin) return;
  } catch { return; }

  e.preventDefault();
  loadBar.start();

  const c = getContent();
  if (c) {
    c.style.transition = 'opacity .17s ease,transform .17s ease';
    c.style.opacity = '0';
    c.style.transform = 'translateY(5px)';
  }

  setTimeout(() => { location.href = href; }, 170);
}, false);

// Show bar + enter animation on form submits (POST navigation)
document.addEventListener('submit', () => loadBar.start(), false);

// Run entrance when page is shown (including back/forward cache)
window.addEventListener('pageshow', () => {
  loadBar.done();
  enterPage();
});

// ══════════════════════════════════════════════════════
// 3. Stagger entrance for cards
// ══════════════════════════════════════════════════════

(function stagger() {
  const els = [...document.querySelectorAll('.stat-card, .card')];
  els.forEach((el, i) => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(18px)';
    el.style.willChange = 'opacity,transform';
    setTimeout(() => {
      el.style.transition =
        `opacity .36s cubic-bezier(.4,0,.2,1) ${i * 60}ms,` +
        `transform .4s cubic-bezier(.4,0,.2,1) ${i * 60}ms`;
      el.style.opacity = '1';
      el.style.transform = 'translateY(0)';
      setTimeout(() => { el.style.willChange = 'auto'; }, 500 + i * 60);
    }, 30 + i * 60);
  });
})();

// ══════════════════════════════════════════════════════
// 4. Animated number counter on stat cards
// ══════════════════════════════════════════════════════

document.querySelectorAll('.stat-value').forEach(el => {
  const original = el.textContent.trim();
  const isEuro   = original.startsWith('€');
  const numStr   = original.replace(/[^0-9.]/g, '');
  const target   = parseFloat(numStr);

  if (!target || target < 1) return;

  const isFloat = original.includes('.');
  const prefix  = isEuro ? '€ ' : '';
  const dur     = 900;

  function easeOutCubic(t) { return 1 - Math.pow(1 - t, 3); }

  let started = false;

  // Use IntersectionObserver so counter only runs when visible
  const obs = new IntersectionObserver(entries => {
    if (entries[0].isIntersecting && !started) {
      started = true;
      obs.disconnect();

      const t0 = performance.now();
      function tick(now) {
        const p   = Math.min((now - t0) / dur, 1);
        const val = target * easeOutCubic(p);
        el.textContent = prefix + (isFloat ? val.toFixed(2) : Math.round(val).toString());
        if (p < 1) {
          requestAnimationFrame(tick);
        } else {
          el.textContent = original;
        }
      }
      requestAnimationFrame(tick);
    }
  }, { threshold: 0.5 });

  obs.observe(el);
});

// ══════════════════════════════════════════════════════
// 5. Button ripple on primary buttons
// ══════════════════════════════════════════════════════

document.querySelectorAll('.btn-primary').forEach(btn => {
  btn.addEventListener('pointerdown', e => {
    const rect = btn.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const rip = document.createElement('span');
    rip.style.cssText =
      `position:absolute;border-radius:50%;pointer-events:none;` +
      `left:${x}px;top:${y}px;width:0;height:0;` +
      `background:rgba(255,255,255,.24);` +
      `transform:translate(-50%,-50%);` +
      `animation:ripple .55s cubic-bezier(.4,0,.2,1) forwards;`;

    btn.appendChild(rip);
    setTimeout(() => rip.remove(), 600);
  });
});

// ══════════════════════════════════════════════════════
// 6. Alert auto-dismiss with smooth collapse
// ══════════════════════════════════════════════════════

document.querySelectorAll('.alert').forEach(el => {
  function dismiss() {
    const h = el.offsetHeight;
    el.style.overflow = 'hidden';
    el.style.maxHeight = h + 'px';

    requestAnimationFrame(() => {
      el.style.transition =
        'opacity .28s ease,transform .28s ease,' +
        'max-height .35s cubic-bezier(.4,0,.2,1),' +
        'margin-bottom .35s ease,padding .35s ease';
      el.style.opacity   = '0';
      el.style.transform = 'translateY(-6px)';
      el.style.maxHeight = '0';
      el.style.marginBottom = '0';
      el.style.paddingTop = '0';
      el.style.paddingBottom = '0';
    });

    setTimeout(() => el.remove(), 380);
  }

  const btn = el.querySelector('.alert-close');
  if (btn) btn.addEventListener('click', dismiss);
  setTimeout(dismiss, 5000);
});

// ══════════════════════════════════════════════════════
// 7. Confirm delete dialogs
// ══════════════════════════════════════════════════════

document.querySelectorAll('.confirm-delete').forEach(form => {
  form.addEventListener('submit', e => {
    if (!confirm('Wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.')) {
      e.preventDefault();
    }
  });
});

// ══════════════════════════════════════════════════════
// 8. Clickable table rows
// ══════════════════════════════════════════════════════

document.querySelectorAll('tr[data-href]').forEach(row => {
  row.addEventListener('click', e => {
    if (!e.target.closest('a,button,form')) {
      location.href = row.dataset.href;
    }
  });
});

// ══════════════════════════════════════════════════════
// 9. Topbar shadow on scroll
// ══════════════════════════════════════════════════════

const topbar = document.querySelector('.topbar');
if (topbar) {
  window.addEventListener('scroll', () => {
    topbar.classList.toggle('scrolled', window.scrollY > 8);
  }, { passive: true });
}

// ══════════════════════════════════════════════════════
// 10. Live-Sync — alle Clients sehen Änderungen sofort
// ══════════════════════════════════════════════════════

(function liveSync() {
  // Login-Seite hat kein .content — dort nicht pollen
  if (!document.querySelector('.content')) return;

  let baseVersion = null;
  let formDirty   = false;

  // Sobald jemand in ein Formular tippt: nicht neu laden (Eingaben schützen)
  document.addEventListener('input', e => {
    if (e.target.closest('form')) formDirty = true;
  }, true);

  function typingNow() {
    const el = document.activeElement;
    return el && ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName);
  }

  async function check() {
    try {
      const r = await fetch('/api/version', { cache: 'no-store' });
      if (r.status === 401) { location.reload(); return; }   // Session abgelaufen → Login zeigen
      if (!r.ok) return;
      const j = await r.json();
      if (baseVersion === null) { baseVersion = j.v; return; }
      if (j.v !== baseVersion && !formDirty && !typingNow()) {
        // Daten haben sich geändert (anderer Benutzer) → sanft neu laden
        loadBar.start();
        const c = getContent();
        if (c) {
          c.style.transition = 'opacity .15s ease';
          c.style.opacity = '.45';
        }
        setTimeout(() => location.reload(), 130);
      }
    } catch (_) { /* Server kurz nicht erreichbar — einfach weiter versuchen */ }
  }

  check();
  setInterval(check, 2500);
})();
