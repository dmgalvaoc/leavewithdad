# Daily Article Agent — Prompt

**Execute immediately. Do not ask for confirmation. Start now.**

---

## Your only job

Write the article HTML file. The shell script handles git and the webhook — do NOT run git or curl yourself.

---

## Article requirements

- **Length:** 800–1000 words
- **Voice:** Dad's practical, slightly opinionated first-person perspective
- **Structure:** lean scaffold — intro, 2-3 body sections, closing takeaway
- **Product boxes:** one `.product-box` per affiliate link — pair each with its matching product image (same index) — no prices displayed
- **Post images:** use the post image URLs provided for article body images — embed directly as `<img src="...">`, do not download
- **Images:** use URLs exactly as provided, do not download files locally
- **Template:** read and follow the structure of `/Users/diegogalvao/Desktop/leavewithdad/articles/hvac-leak-detector-plantation/index.html`

---

## Step 1 — Write the article

Use the Write tool to create the file at this exact absolute path:
`/Users/diegogalvao/Desktop/leavewithdad/articles/SLUG/index.html`

Replace SLUG with the slug from the assignment below.

When done, output this exact line so the shell script can confirm success:
`DRAFT_WRITTEN: SLUG`

Replace SLUG with the actual slug value.

---

## Publish command (Diego says in Cowork chat)

"publish [slug]" → agent wires to index.html, updates sitemap, git pushes, sets Published Date in sheet.
