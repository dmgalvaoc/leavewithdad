/* ── Leave With Dad — Share Bar ───────────────────────────────────── */
(function () {
  'use strict';

  const PAGE_URL   = encodeURIComponent(window.location.href);
  const PAGE_TITLE = encodeURIComponent(document.title);

  // ── Toast ─────────────────────────────────────────────────────────
  let toastEl = null;
  function showToast(msg) {
    if (!toastEl) {
      toastEl = document.createElement('div');
      toastEl.className = 'lwd-share-toast';
      document.body.appendChild(toastEl);
    }
    toastEl.textContent = msg;
    toastEl.classList.add('lwd-visible');
    clearTimeout(toastEl._timer);
    toastEl._timer = setTimeout(() => toastEl.classList.remove('lwd-visible'), 2400);
  }

  // ── Copy to clipboard ─────────────────────────────────────────────
  function copyLink(btn) {
    navigator.clipboard.writeText(window.location.href).then(() => {
      btn.classList.add('lwd-copied');
      const prev = btn.innerHTML;
      btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> Copied!`;
      showToast('Link copied to clipboard');
      setTimeout(() => { btn.classList.remove('lwd-copied'); btn.innerHTML = prev; }, 2000);
    }).catch(() => {
      showToast('Copy not supported — select the URL manually');
    });
  }

  // ── SVG icons ─────────────────────────────────────────────────────
  const icons = {
    copy: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`,
    facebook: `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M24 12.073C24 5.405 18.627 0 12 0S0 5.405 0 12.073C0 18.1 4.388 23.094 10.125 24v-8.437H7.078v-3.49h3.047v-2.66c0-3.025 1.792-4.697 4.533-4.697 1.312 0 2.686.236 2.686.236v2.97h-1.513c-1.491 0-1.956.93-1.956 1.886v2.265h3.328l-.532 3.49h-2.796V24C19.612 23.094 24 18.1 24 12.073z"/></svg>`,
    linkedin: `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>`,
    instagram: `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 1 0 0 12.324 6.162 6.162 0 0 0 0-12.324zM12 16a4 4 0 1 1 0-8 4 4 0 0 1 0 8zm6.406-11.845a1.44 1.44 0 1 0 0 2.881 1.44 1.44 0 0 0 0-2.881z"/></svg>`,
    email: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>`,
    share: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>`,
  };

  // ── Build share bar HTML ───────────────────────────────────────────
  function buildBar(container) {
    const fbUrl  = `https://www.facebook.com/sharer/sharer.php?u=${PAGE_URL}`;
    const liUrl  = `https://www.linkedin.com/sharing/share-offsite/?url=${PAGE_URL}`;
    const emUrl  = `mailto:?subject=${PAGE_TITLE}&body=I thought you'd find this useful: ${PAGE_URL}`;

    container.innerHTML = `<span class="lwd-share-label">Share</span><button class="lwd-share-btn lwd-share-btn--copy" id="lwd-copy">${icons.copy} Copy link</button><a class="lwd-share-btn" href="${fbUrl}" target="_blank" rel="noopener">${icons.facebook} Facebook</a><a class="lwd-share-btn" href="${liUrl}" target="_blank" rel="noopener">${icons.linkedin} LinkedIn</a><button class="lwd-share-btn lwd-share-btn--instagram" id="lwd-instagram">${icons.instagram} Instagram</button><a class="lwd-share-btn" href="${emUrl}">${icons.email} Email</a>`;

    container.querySelector('#lwd-copy').addEventListener('click', function () {
      copyLink(this);
    });

    container.querySelector('#lwd-instagram').addEventListener('click', function () {
      navigator.clipboard.writeText(window.location.href).then(() => {
        showToast('Link copied — open Instagram and paste in your story or bio');
      }).catch(() => {
        showToast('Copy not supported — select the URL manually');
      });
    });

  }

  // ── Mount all share bars on page ──────────────────────────────────
  function init() {
    document.querySelectorAll('.lwd-share').forEach(buildBar);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
