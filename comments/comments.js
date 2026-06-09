/* ── Leave With Dad — Comment Widget ─────────────────────────────── */
(function () {
  'use strict';

  // ── Config (read from script tag data-* attributes) ──────────────
  const scriptTag = document.currentScript;
  const SUPABASE_URL    = scriptTag.dataset.supabaseUrl    || 'https://soarurpqwyqxejvkuumi.supabase.co';
  const SUPABASE_ANON   = scriptTag.dataset.supabaseAnonKey || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNvYXJ1cnBxd3lxeGVqdmt1dW1pIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODEwMjI5NzUsImV4cCI6MjA5NjU5ODk3NX0.D2xSyarj32HFOLjT8hWbQm0QGFQSOk8-Jo7oGHi4Cog';
  const ADMIN_USER_ID   = scriptTag.dataset.adminUserId || 'ac64773e-392b-4350-871d-efba51c45574';

  if (!SUPABASE_URL || !SUPABASE_ANON) {
    console.error('[LWD Comments] Missing data-supabase-url or data-supabase-anon-key');
    return;
  }

  // ── Bootstrap Supabase client ─────────────────────────────────────
  const { createClient } = window.supabase;
  const sb = createClient(SUPABASE_URL, SUPABASE_ANON);

  // ── Resolve mount point ───────────────────────────────────────────
  const container = document.getElementById('leavewithdad-comments');
  if (!container) return;

  const PAGE_PATH = container.dataset.pagePath || window.location.pathname;
  const LS_PAGE   = `lwd_page_liked_${PAGE_PATH}`;

  // ── State ─────────────────────────────────────────────────────────
  let currentUser  = null;
  let comments     = [];
  let pageCount    = 0;

  // ── Helpers ───────────────────────────────────────────────────────
  function relativeTime(iso) {
    const diff = (Date.now() - new Date(iso).getTime()) / 1000;
    if (diff < 60)   return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function initials(name) {
    return (name || '?')
      .split(' ')
      .slice(0, 2)
      .map(w => w[0])
      .join('')
      .toUpperCase();
  }

  function avatarEl(url, name) {
    if (url) {
      return `<img class="lwd-user-avatar" src="${escapeHtml(url)}" alt="${escapeHtml(name)}" loading="lazy">`;
    }
    return `<div class="lwd-user-avatar-placeholder">${escapeHtml(initials(name))}</div>`;
  }

  // ── Rate limiting (client-side, 3 comments per user per page per hour) ──
  function getRateKey() {
    return `lwd_rate_${currentUser?.id}_${PAGE_PATH}`;
  }

  function checkRateLimit() {
    const key   = getRateKey();
    const raw   = localStorage.getItem(key);
    const now   = Date.now();
    const hour  = 60 * 60 * 1000;
    let timestamps = raw ? JSON.parse(raw) : [];
    timestamps = timestamps.filter(t => now - t < hour);
    return timestamps.length < 3;
  }

  function recordPost() {
    const key  = getRateKey();
    const raw  = localStorage.getItem(key);
    const now  = Date.now();
    const hour = 60 * 60 * 1000;
    let timestamps = raw ? JSON.parse(raw) : [];
    timestamps = timestamps.filter(t => now - t < hour);
    timestamps.push(now);
    localStorage.setItem(key, JSON.stringify(timestamps));
  }

  // ── Page reaction ─────────────────────────────────────────────────
  async function fetchPageReaction() {
    const { data } = await sb
      .from('page_reactions')
      .select('thumbs_up')
      .eq('page_path', PAGE_PATH)
      .maybeSingle();
    pageCount = data?.thumbs_up ?? 0;
  }

  async function incrementPageReaction() {
    const { data } = await sb
      .from('page_reactions')
      .select('thumbs_up')
      .eq('page_path', PAGE_PATH)
      .maybeSingle();

    if (data) {
      await sb
        .from('page_reactions')
        .update({ thumbs_up: data.thumbs_up + 1 })
        .eq('page_path', PAGE_PATH);
    } else {
      await sb
        .from('page_reactions')
        .insert({ page_path: PAGE_PATH, thumbs_up: 1 });
    }
    pageCount++;
    renderPageReaction();
  }

  // ── Comment reactions ─────────────────────────────────────────────
  async function incrementCommentLike(id) {
    const comment = comments.find(c => c.id === id);
    if (!comment) return;
    await sb
      .from('comments')
      .update({ likes: comment.likes + 1 })
      .eq('id', id);
    comment.likes++;
    const btn = container.querySelector(`.lwd-comment-like-btn[data-id="${id}"]`);
    if (btn) {
      btn.classList.add('lwd-liked');
      btn.querySelector('.lwd-like-count').textContent = comment.likes;
    }
  }

  // ── Delete comment ────────────────────────────────────────────────
  async function deleteComment(id) {
    if (!confirm('Delete this comment?')) return;
    const { error } = await sb.from('comments').delete().eq('id', id);
    if (!error) {
      comments = comments.filter(c => c.id !== id);
      renderThread();
    }
  }

  // ── Load comments ─────────────────────────────────────────────────
  async function fetchComments() {
    const { data } = await sb
      .from('comments')
      .select('*')
      .eq('page_path', PAGE_PATH)
      .order('created_at', { ascending: true });
    comments = data || [];
  }

  // ── Auth ──────────────────────────────────────────────────────────
  async function signIn(provider) {
    await sb.auth.signInWithOAuth({
      provider,
      options: { redirectTo: window.location.href },
    });
  }

  async function signOut() {
    await sb.auth.signOut();
    currentUser = null;
    renderAuthBar();
    renderComposer();
    renderThread();
  }

  // ── Post comment ──────────────────────────────────────────────────
  async function postComment(body) {
    const meta = currentUser.user_metadata || {};
    const displayName = meta.full_name || meta.name || meta.user_name || currentUser.email || 'Reader';
    const avatarUrl   = meta.avatar_url || meta.picture || null;

    const { data, error } = await sb.from('comments').insert({
      page_path:    PAGE_PATH,
      user_id:      currentUser.id,
      display_name: displayName,
      avatar_url:   avatarUrl,
      body:         body,
    }).select().single();

    if (!error && data) {
      recordPost();
      comments.push(data);
      renderThread();
      return true;
    }
    return false;
  }

  // ── Renderers ─────────────────────────────────────────────────────
  function renderPageReaction() {
    const bar   = container.querySelector('.lwd-page-reaction');
    if (!bar) return;
    const liked = !!localStorage.getItem(LS_PAGE);
    bar.querySelector('.lwd-page-reaction-label').innerHTML =
      `👍 <strong>${pageCount}</strong> ${pageCount === 1 ? 'person found' : 'people found'} this helpful`;
    const btn = bar.querySelector('.lwd-like-btn');
    btn.classList.toggle('lwd-liked', liked);
    btn.textContent = liked ? '👍 Thanks!' : '👍 Helpful';
  }

  function renderAuthBar() {
    const bar = container.querySelector('.lwd-auth-bar');
    if (!bar) return;

    if (currentUser) {
      const meta   = currentUser.user_metadata || {};
      const name   = meta.full_name || meta.name || meta.user_name || currentUser.email || 'You';
      const avatar = meta.avatar_url || meta.picture || null;
      bar.innerHTML = `
        <div class="lwd-user-row">
          ${avatarEl(avatar, name)}
          <span class="lwd-user-name">Signed in as <strong>${escapeHtml(name)}</strong></span>
          <button class="lwd-signout-btn" id="lwd-signout">Sign out</button>
        </div>`;
      bar.querySelector('#lwd-signout').addEventListener('click', signOut);
    } else {
      bar.innerHTML = `
        <div class="lwd-auth-prompt">Sign in to leave a comment:</div>
        <div class="lwd-auth-buttons">
          <button class="lwd-oauth-btn lwd-oauth-btn--google" id="lwd-google">
            <svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#fff" opacity=".9"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#fff" opacity=".9"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#fff" opacity=".9"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#fff" opacity=".9"/>
            </svg>
            Continue with Google
          </button>
          <button class="lwd-oauth-btn lwd-oauth-btn--facebook" id="lwd-facebook">
            <svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
              <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
            </svg>
            Continue with Facebook
          </button>
        </div>`;
      bar.querySelector('#lwd-google').addEventListener('click', () => signIn('google'));
      bar.querySelector('#lwd-facebook').addEventListener('click', () => signIn('facebook'));
    }
  }

  function renderComposer() {
    const wrap = container.querySelector('.lwd-composer');
    if (!wrap) return;
    wrap.style.display = currentUser ? '' : 'none';
  }

  function renderThread() {
    const thread = container.querySelector('.lwd-thread');
    if (!thread) return;

    if (comments.length === 0) {
      thread.innerHTML = `<div class="lwd-thread-empty">No comments yet — be the first to leave one.</div>`;
      return;
    }

    thread.innerHTML = comments.map(c => {
      const liked    = !!localStorage.getItem(`lwd_comment_liked_${c.id}`);
      const isAdmin  = ADMIN_USER_ID && currentUser?.id === ADMIN_USER_ID;
      const deletBtn = isAdmin
        ? `<button class="lwd-delete-btn" data-id="${c.id}" title="Delete comment">🗑️</button>`
        : '';
      return `
        <div class="lwd-comment" data-comment-id="${c.id}">
          <div class="lwd-comment-header">
            ${avatarEl(c.avatar_url, c.display_name)}
            <div class="lwd-comment-meta">
              <span class="lwd-comment-author">${escapeHtml(c.display_name)}</span>
              <span class="lwd-comment-time">${relativeTime(c.created_at)}</span>
            </div>
            ${deletBtn}
          </div>
          <div class="lwd-comment-body">${escapeHtml(c.body)}</div>
          <div class="lwd-comment-footer">
            <button class="lwd-comment-like-btn${liked ? ' lwd-liked' : ''}" data-id="${c.id}">
              👍 <span class="lwd-like-count">${c.likes}</span>
            </button>
          </div>
        </div>`;
    }).join('');

    thread.querySelectorAll('.lwd-comment-like-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.dataset.id;
        const lsKey = `lwd_comment_liked_${id}`;
        if (localStorage.getItem(lsKey)) return;
        localStorage.setItem(lsKey, '1');
        incrementCommentLike(id);
      });
    });

    thread.querySelectorAll('.lwd-delete-btn').forEach(btn => {
      btn.addEventListener('click', () => deleteComment(btn.dataset.id));
    });
  }

  // ── Build skeleton HTML ───────────────────────────────────────────
  function buildSkeleton() {
    container.innerHTML = `
      <div class="lwd-section-title">Ask Dad, leave your comment, or just a thumbs up 👍</div>

      <div class="lwd-page-reaction">
        <span class="lwd-page-reaction-label">👍 <strong>0</strong> people found this helpful</span>
        <button class="lwd-like-btn" id="lwd-page-like">👍 Helpful</button>
      </div>

      <div class="lwd-auth-bar">
        <div class="lwd-loading"><span class="lwd-spinner"></span> Loading…</div>
      </div>

      <div class="lwd-composer" style="display:none;">
        <form id="lwd-comment-form" autocomplete="off">
          <input class="lwd-hp" name="url" tabindex="-1" aria-hidden="true">
          <textarea
            id="lwd-comment-body"
            placeholder="Ask Dad, leave your comment, or just a thumbs up 👍"
            maxlength="2000"
          ></textarea>
          <div id="lwd-composer-error" class="lwd-composer-error" style="display:none;"></div>
          <div class="lwd-composer-footer">
            <button type="submit" class="lwd-submit-btn" id="lwd-submit">Post Comment</button>
          </div>
        </form>
      </div>

      <div class="lwd-thread">
        <div class="lwd-loading"><span class="lwd-spinner"></span> Loading comments…</div>
      </div>`;

    // Page reaction button
    const pageLikeBtn = container.querySelector('#lwd-page-like');
    pageLikeBtn.addEventListener('click', () => {
      if (localStorage.getItem(LS_PAGE)) return;
      localStorage.setItem(LS_PAGE, '1');
      incrementPageReaction();
    });

    // Comment form submit
    const form = container.querySelector('#lwd-comment-form');
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const hp    = form.querySelector('input[name="url"]');
      const body  = form.querySelector('#lwd-comment-body').value.trim();
      const errEl = form.querySelector('#lwd-composer-error');

      // Honeypot check
      if (hp.value) return;

      errEl.style.display = 'none';

      if (!body) {
        errEl.textContent = 'Please write something before posting.';
        errEl.style.display = '';
        return;
      }

      if (!checkRateLimit()) {
        errEl.textContent = "You've posted 3 comments this hour. Please try again later.";
        errEl.style.display = '';
        return;
      }

      const submitBtn = form.querySelector('#lwd-submit');
      submitBtn.disabled = true;
      submitBtn.textContent = 'Posting…';

      const ok = await postComment(body);
      submitBtn.disabled = false;
      submitBtn.textContent = 'Post Comment';

      if (ok) {
        form.querySelector('#lwd-comment-body').value = '';
      } else {
        errEl.textContent = 'Something went wrong. Please try again.';
        errEl.style.display = '';
      }
    });
  }

  // ── Init ──────────────────────────────────────────────────────────
  async function init() {
    buildSkeleton();

    // Restore auth session (handles OAuth redirect)
    const { data: { session } } = await sb.auth.getSession();
    currentUser = session?.user ?? null;

    // Load data in parallel
    await Promise.all([fetchComments(), fetchPageReaction()]);

    renderPageReaction();
    renderAuthBar();
    renderComposer();
    renderThread();

    // Listen for auth state changes (sign in / sign out)
    sb.auth.onAuthStateChange((_event, session) => {
      currentUser = session?.user ?? null;
      renderAuthBar();
      renderComposer();
      renderThread();
    });
  }

  // Wait for DOM if needed
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
