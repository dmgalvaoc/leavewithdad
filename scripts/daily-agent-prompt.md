# Daily Article Agent — Prompt

**Execute immediately. Do not ask for confirmation. Start writing the article now using the assignment provided at the end of this prompt.**

---

## Article requirements

- **Length:** 800–1000 words
- **Voice:** Dad's practical, slightly opinionated first-person perspective
- **Structure:** lean scaffold — intro, 2-3 body sections, closing takeaway
- **Product boxes:** one `.product-box` per affiliate link — pair each with its matching product image (same index) — no prices displayed
- **Post images:** use the post image URLs provided for article body images — embed directly as `<img src="...">`, do not download
- **Images:** use URLs exactly as provided, do not download files locally
- **Template:** follow the structure of `articles/hvac-leak-detector-plantation/index.html`

---

## Output steps

1. Write article HTML to `articles/{slug}/index.html`
2. Git commit and push to main
3. Call the webhook URL provided in the assignment to mark as draft in the sheet

---

## Publish command (Diego says in Cowork chat)

"publish [slug]" → agent wires to index.html, updates sitemap, git pushes, sets Published Date in sheet.
