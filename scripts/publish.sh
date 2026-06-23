#!/bin/bash
# leavewithdad — publish.sh
# Usage: bash scripts/publish.sh <slug>
# Wires the article card to index.html, marks sheet as published, commits and pushes.
# Article must already exist at articles/[slug]/index.html before running.
# Run from the repo root: ~/Desktop/leavewithdad/

set -e

REPO="/Users/diegogalvao/Desktop/leavewithdad"
SLUG="$1"
TODAY=$(date +%Y-%m-%d)

if [ -z "$SLUG" ]; then
  echo "ERROR: slug required. Usage: bash scripts/publish.sh <slug>"
  exit 1
fi

ARTICLE_DIR="$REPO/articles/$SLUG"

# ── 1. Verify article exists ────────────────────────────────────────────────
if [ ! -f "$ARTICLE_DIR/index.html" ]; then
  echo "ERROR: $ARTICLE_DIR/index.html not found"
  exit 1
fi

# ── 2. Call sheet webhook — mark published ──────────────────────────────────
WEBHOOK_FILE="$REPO/.sheets-webhook-url"
if [ -f "$WEBHOOK_FILE" ]; then
  WEBHOOK_URL=$(cat "$WEBHOOK_FILE")
  echo "→ Updating sheet: slug=$SLUG status=published date=$TODAY"
  REDIRECT=$(curl -s -i -X POST "$WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d "{\"slug\": \"$SLUG\", \"status\": \"published\", \"date\": \"$TODAY\"}" \
    | grep -i "^location:" | awk '{print $2}' | tr -d '\r\n')
  if [ -n "$REDIRECT" ]; then
    RESPONSE=$(curl -s -X GET "$REDIRECT" -H "Accept: application/json")
    echo "  Sheet response: $RESPONSE"
  else
    echo "  WARNING: no redirect from webhook — sheet may not have updated"
  fi
else
  echo "  WARNING: .sheets-webhook-url not found — skipping sheet update"
fi

# ── 3. Authenticate ──────────────────────────────────────────────────────────
GITHUB_TOKEN=$(cat "$REPO/.github-token")
git -C "$REPO" remote set-url origin "https://${GITHUB_TOKEN}@github.com/dmgalvaoc/leavewithdad.git"

# ── 4. Commit + push ─────────────────────────────────────────────────────────
echo "→ Committing and pushing..."
rm -f "$REPO/.git/HEAD.lock" "$REPO/.git/index.lock" 2>/dev/null || true
git -C "$REPO" add index.html
git -C "$REPO" commit -m "Publish: $SLUG"
git -C "$REPO" push origin main

echo ""
echo "✓ Published: https://leavewithdad.com/articles/$SLUG/"
