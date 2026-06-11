# Daily Article Agent — Prompt

This file mirrors the scheduled task prompt. Source of truth is the Cowork scheduled task "leavewithdad-daily-draft".

---

## GOOGLE DRIVE IDs

- Topic Queue Sheet: `1Yftu5cFEd0BP90Ea4LiDEkSN2GUAS56mIlYbH5lMDo4`
- Assets Folder: `1IAQ-9A4hpxgMk3C8hd_aD8gn5nlB0ukc`

---

## Sheet columns (Topic Queue)

| Column | Purpose |
|---|---|
| Order | Posting priority — drag rows to reorder |
| Title | Article title |
| Slug | URL slug |
| Category | Plantation / Home / Yard & Garden / Dad Recommends |
| Status | idea → draft → published |
| Scheduled Date | Set by agent when drafted |
| Published Date | Set when wired to index.html |
| Notes | Any context for the agent |
| Affiliate Link 1 | Amazon affiliate URL (optional) |
| Affiliate Link 2 | Amazon affiliate URL (optional) |
| Affiliate Link 3 | Amazon affiliate URL (optional) |

Agent picks the lowest-Order row where Status = `idea`. After drafting, sets Status to `draft` and fills Scheduled Date.

---

## Agent steps

1. Read Topic Queue Sheet → pick first `idea` by Order
2. Web research (4–6 searches)
3. Check Assets Folder for matching image
4. Write article HTML (template: water-bills-plantation/index.html)
   - Include one .product-box per non-empty Affiliate Link column
   - No prices displayed
5. Update sheet row: Status → `draft`, Scheduled Date → today
6. Git push to main
7. iMessage Diego: draft URL + publish instructions

## Publish command (Diego says in Cowork chat)

"publish [slug]" → agent wires to index.html, updates sitemap, git pushes, sets Published Date in sheet.
