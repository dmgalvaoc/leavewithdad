# Leave With Dad — Claude Instructions

Read this at the start of every session. These rules are non-negotiable.

---

## The One Rule That Overrides Everything

**Every article HTML file MUST be built from `scripts/article-scaffold.html`.** No exceptions. Never write a `<style>` block inside an article. Never invent your own layout. Copy the scaffold, fill in the `{{PLACEHOLDERS}}`, write the body content inside `{{ARTICLE_BODY}}`. That's it.

---

## Site Overview

Vanilla HTML/CSS/JS. No framework, no build step.
Hosted on GitHub Pages — repo: `dmgalvaoc/leavewithdad`, branch: `main`.
Live at: `https://leavewithdad.com/`

---

## Stack & Key Files

- `index.html` — homepage
- `style.css` — homepage styles only. Articles never use inline styles.
- `article.css` — shared article styles, loaded via `<link>` in every article
- `scripts/article-scaffold.html` — **the only valid starting point for any new article**
- `comments/comments.js` + `comments.css` — Supabase comment widget
- `share/share.js` + `share.css` — share bar widget
- `sitemap.xml`, `robots.txt`

---

## Article Scaffold — Mandatory Usage

Every new article must start as a copy of `scripts/article-scaffold.html`.

**Placeholders to fill:**

| Placeholder | What it is |
|---|---|
| `{{TITLE}}` | Full SEO title |
| `{{META_DESCRIPTION}}` | 150–160 char meta description |
| `{{SLUG}}` | URL slug, e.g. `plantation-alarm-permit` |
| `{{DATE}}` | ISO date, e.g. `2026-06-24` |
| `{{MONTH_YEAR}}` | e.g. `June 2026` |
| `{{CATEGORY}}` | Tab label: `Plantation`, `Home`, `Yard & Garden`, or `Dad Recommends` |
| `{{CATEGORY_ANCHOR}}` | Tab ID: `plantation`, `home`, `yard`, or `recommends` |
| `{{SUBCATEGORY}}` | Short topic label for breadcrumb |
| `{{HERO_IMAGE_URL}}` | Full URL to hero image |
| `{{READ_TIME}}` | Estimated minutes |
| `{{KICKER}}` | Opening hook sentence (see voice guide below) |
| `{{ARTICLE_BODY}}` | Full article HTML content |
| `{{ACTIVE_PLANTATION}}` / `{{ACTIVE_HOME}}` / etc. | Set `class="active"` on the matching nav item, remove from others |
| `{{DAD_STRIP_QUOTE}}` | One punchy takeaway quote |
| `{{DAD_STRIP_SIGNOFF}}` | Short location/context line |

---

## Post Images (from the sheet's Post Image columns)

If the sheet has a value in **Post Image 1**, it MUST be embedded as a `<div class="article-photo">` block immediately after `<div class="lwd-share"></div>` and before `<div class="article-body">`:

```html
<div class="article-photo">
  <img src="{{POST_IMAGE_URL}}" alt="{{DESCRIPTIVE_ALT}}" />
</div>
```

If the sheet has a value in **Post Image 2** (or more), each additional image MUST be embedded inline inside the article body at a logical break between sections.

For Google Drive share links (`https://drive.google.com/file/d/FILE_ID/view`), convert to a direct image URL: `https://drive.google.com/uc?export=view&id=FILE_ID`

If the sheet has no Post Image values, omit the block entirely — do not invent placeholder images.

---

## Per-Article Checklist (verify before every commit)

1. Google Analytics tag (`G-01DPLMX3L2`) in `<head>`
2. Canonical URL set to `https://leavewithdad.com/articles/{{SLUG}}/`
3. Full Open Graph block: `og:image`, `article:published_time`, `article:author`
4. Twitter Card block
5. JSON-LD Article schema
6. Google Fonts (Playfair Display + Inter) loaded via `<link>`
7. Tabler Icons CDN loaded via `<link>`
8. `/style.css?v=3` and `/article.css?v=1` and `/share/share.css` loaded via `<link>`
9. Favicon set (ico + 512 + 192 + apple-touch-icon)
10. Topbar with logo and search box
11. Sidebar nav with correct `class="active"` on matching tab
12. Breadcrumb: `← Leave With Dad › Tab Name › Article Title`
13. `<div class="lwd-share"></div>` immediately after `.article-meta`
14. Comments widget: `<div id="leavewithdad-comments" data-page-path="/articles/{{SLUG}}"></div>`
15. Supabase CDN script + `/comments/comments.js` + `/share/share.js` before `</body>`
16. Dad Strip section with quote and signoff
17. Footer: Home / Privacy Policy / Data Deletion / Contact (mailto only) — no dead links
18. Homepage `index.html`: add card with correct `data-tags`
19. `sitemap.xml`: add URL entry

---

## Homepage Tab Architecture

Nav tabs: Plantation / Home / Yard & Garden / Dad Recommends
- These are **filter tabs**, not separate pages.
- All article cards live in one grid inside `<main id="plantation">`.
- Each card needs `data-tags="tag1 tag2"` matching one or more tab IDs.
- Tab IDs: `plantation`, `home`, `yard`, `recommends`

---

## Voice & Content Rules

- **First-person dad.** Blunt, practical, slightly opinionated.
- Lead with the most useful fact. No slow intros.
- Kicker: hook with a real situation or confession, not a generic intro.
- 600–800 words total for the article body.
- Use `h2` headers throughout.
- Never fluffy. Never affiliate-disclosure paragraphs.
- It's Diego and his wife — no nearby family. Don't write about relatives helping out.
- **Do not display any prices** in product boxes.

---

## Available Article Components

```html
<div class="tip-box"><strong>Dad's tip</strong> ...</div>
<div class="warning-box"><strong>Warning</strong> ...</div>
<div class="quick-ref"><h3>...</h3><ul><li>...</li></ul></div>
<table class="info-table"><thead>...</thead><tbody>...</tbody></table>
<blockquote>...</blockquote>

<!-- Product box (one per affiliate link): -->
<div class="product-box">
  <div class="product-img">
    <a href="{{AFFILIATE_LINK}}" target="_blank" rel="nofollow sponsored">
      <img src="{{PRODUCT_IMAGE_URL}}" alt="{{PRODUCT_NAME}}" />
    </a>
  </div>
  <div class="product-box-content">
    <h4>{{PRODUCT_NAME}}</h4>
    <p>{{PRODUCT_DESCRIPTION}}</p>
    <a href="{{AFFILIATE_LINK}}" class="btn-amazon" target="_blank" rel="nofollow sponsored">
      <i class="ti ti-brand-amazon"></i> View on Amazon
    </a>
  </div>
</div>
```

---

## Design Palette

| Name | Hex |
|---|---|
| Forest green | `#2C3E35` |
| Deep green | `#1e2e27` |
| Terra cotta | `#C4622D` |
| Parchment | `#F5F0E8` |
| Muted green | `#8aaa97` |
| White | `#ffffff` |

- Headlines: Playfair Display (serif)
- Body/UI: Inter (sans-serif)

Product images always use **white background (#fff)** — never parchment or gray.

---

## Google Analytics

Tag ID: `G-01DPLMX3L2`
Must be in `<head>` of every page — homepage, every article, every legal page.

---

## Supabase

- URL: `https://soarurpqwyqxejvkuumi.supabase.co`
- Anon key and admin UUID are hardcoded in `comments/comments.js` — **do not repeat them in article HTML**

---

## Git & Deploy Rules

- Never commit `.env` or secret files.
- After every commit, push to GitHub — deploy is automatic via GitHub Pages.
- "Committed" means pushed and live. Always push after committing.
- Claude writes HTML only. The shell scripts handle git add, commit, and push.
