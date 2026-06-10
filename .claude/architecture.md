# Leave With Dad — Site Architecture

## URLs
- Homepage: `https://leavewithdad.com/`
- Articles: `https://leavewithdad.com/[slug]/` (subfolder with index.html)
- Legal: `/privacy/`, `/data-deletion/`
- Verification: `google4eae8e088910c1a6.html`

## Stack
Vanilla HTML/CSS/JS. No framework, no build step. Hosted on GitHub Pages (repo: dmgalvaoc/leavewithdad). Branch: main.

## Key files
- `index.html` — homepage
- `style.css` — homepage styles only (articles use inline `<style>`)
- `comments/comments.js` + `comments.css` — Supabase comment widget
- `share/share.js` + `share.css` — share bar widget
- `sitemap.xml`, `robots.txt`

## Supabase
- URL: https://soarurpqwyqxejvkuumi.supabase.co
- Anon key: hardcoded in comments.js (do not repeat in article HTML)
- Admin UUID: ac64773e-392b-4350-871d-efba51c45574 (hardcoded in comments.js)
- Tables: `comments`, `page_reactions`

## Homepage tab architecture
Nav tabs: Plantation / Home / Yard & Garden / Dad Recommends
- These are FILTER tabs, not separate pages.
- All articles live in ONE cards grid inside `<main id="plantation">`.
- Each card has `data-tags="tag1 tag2"` attributes.
- JS intercepts tab clicks, filters cards to matching tag, scrolls to grid.
- Clicking Plantation (or on load) shows all cards.
- Tab IDs used as filter keys: `plantation`, `home`, `yard`, `recommends`

## Article tagging
Each article card on homepage must have `data-tags` matching one or more tab keys:
- HVAC article: `data-tags="plantation home recommends"`
- St. Augustine article: `data-tags="plantation yard"`
- Add new articles by adding a card to the homepage grid with correct data-tags.

## Google Analytics
Tag ID: G-01DPLMX3L2
Must be in `<head>` of EVERY page (homepage + every article + legal pages).
Place before the AdSense script:
```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-01DPLMX3L2"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-01DPLMX3L2');
</script>
```

## Per-article checklist (every new article)
Cowork creates the article folder — Claude wires it up:
1. `<link rel="stylesheet" href="/share/share.css">` in `<head>`
2. `<div class="lwd-share"></div>` immediately after `.article-meta`
3. `<div id="leavewithdad-comments" data-page-path="/[slug]"></div>` before footer
4. `<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>` before `</body>`
5. `<script src="/comments/comments.js"></script>` after supabase script
6. `<script src="/share/share.js"></script>` after comments script
7. Breadcrumb: `<a href="/">← Leave With Dad</a> › <a href="/#[tab]">Tab Name</a> › Article Title`
8. Nav: correct `class="active"` on matching tabs, all links use `/#[tab]` format
9. Footer: Home / Privacy Policy / Data Deletion / Contact (mailto) only — no dead links
10. OG tags: og:image, article:published_time, article:author
11. Homepage: add card with correct `data-tags`
12. sitemap.xml: add URL entry

## Share bar
Drop-in: `<div class="lwd-share"></div>` anywhere.
Requires `/share/share.css` in `<head>` and `/share/share.js` before `</body>`.
Buttons: Copy Link, Facebook, LinkedIn, Instagram (copy+toast), Email, native share on mobile.

## Comments widget
Drop-in: `<div id="leavewithdad-comments" data-page-path="/[slug]"></div>` + supabase CDN + `/comments/comments.js`.
Keyed to `data-page-path`. No keys needed in HTML — all hardcoded in comments.js.

## Footer (all pages)
```html
<footer>
  <div class="footer-inner">
    <nav class="footer-links">
      <a href="/">Home</a>
      <a href="/privacy/">Privacy Policy</a>
      <a href="/data-deletion/">Data Deletion</a>
      <a href="mailto:diegomgalvaoc@gmail.com">Contact</a>
    </nav>
    <p class="footer-copy">&copy; 2026 Leave With Dad · Plantation, FL</p>
  </div>
</footer>
```

## Palette
- Forest green: #2C3E35
- Deep green: #1e2e27
- Terra cotta: #C4622D
- Parchment: #F5F0E8
- Muted green: #8aaa97
- White: #ffffff

## Fonts
- Headlines: Playfair Display (serif)
- Body/UI: Inter (sans-serif)
