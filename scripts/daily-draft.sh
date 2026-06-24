#!/bin/bash
# daily-draft.sh — leavewithdad.com daily article drafter
# Runs via launchd at 6am. Fetches next topic from webhook, drafts with Claude CLI.
# Git push and webhook (which triggers email to dad@leavewithdad.com) are handled
# by this shell script — never delegated to Claude — to guarantee they always run.

REPO_DIR="/Users/diegogalvao/Desktop/leavewithdad"
PROMPT_FILE="$REPO_DIR/scripts/daily-agent-prompt.md"
LOG_DIR="$REPO_DIR/scripts/logs"
LOG_FILE="$LOG_DIR/daily-draft-$(date +%Y-%m-%d).log"
WEBHOOK="$(cat "$REPO_DIR/.sheets-webhook-url")"

mkdir -p "$LOG_DIR"
echo "=== leavewithdad daily draft — $(date) ===" | tee -a "$LOG_FILE"

# ── 1. Fetch next idea from Topic Queue ───────────────────────────────────────
TOPIC_JSON=$(curl -sL "${WEBHOOK}?action=next")
echo "Topic: $TOPIC_JSON" | tee -a "$LOG_FILE"

TOPIC_OK=$(echo "$TOPIC_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('ok','false'))" 2>/dev/null)
if [ "$TOPIC_OK" != "True" ] && [ "$TOPIC_OK" != "true" ]; then
  echo "⚠️  No ideas in queue or webhook error — exiting." | tee -a "$LOG_FILE"
  echo "=== done $(date) ===" >> "$LOG_FILE"
  exit 0
fi

TITLE=$(echo "$TOPIC_JSON"    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('title',''))")
SLUG=$(echo "$TOPIC_JSON"     | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('slug',''))")
CATEGORY=$(echo "$TOPIC_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('category',''))")
NOTES=$(echo "$TOPIC_JSON"    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('notes',''))")
AFF_LINKS=$(echo "$TOPIC_JSON" | python3 -c "
import sys, json
d = json.load(sys.stdin)
links = d.get('affiliateLinks', [])
if links:
    print('Affiliate links:\n' + '\n'.join('- ' + l for l in links))
else:
    print('No affiliate links.')
")

PRODUCT_IMAGES=$(echo "$TOPIC_JSON" | python3 -c "
import sys, json
d = json.load(sys.stdin)
imgs = d.get('productImages', [])
if imgs:
    print('Product images (pair each with its affiliate link in order):\n' + '\n'.join('- ' + u for u in imgs))
else:
    print('No product images.')
")

POST_IMAGES=$(echo "$TOPIC_JSON" | python3 -c "
import sys, json
d = json.load(sys.stdin)
imgs = d.get('postImages', [])
if imgs:
    print('Article post images:\n' + '\n'.join('- ' + u for u in imgs))
else:
    print('No post images.')
")

echo "Drafting: $TITLE ($SLUG)" | tee -a "$LOG_FILE"

# ── 2. Build prompt ───────────────────────────────────────────────────────────
FULL_PROMPT="$(cat "$PROMPT_FILE")

---

## TODAY'S ASSIGNMENT

Execute immediately. Write this article now:

- **Title:** $TITLE
- **Slug:** $SLUG
- **Category:** $CATEGORY
- **Notes:** $NOTES
- $AFF_LINKS
- $PRODUCT_IMAGES
- $POST_IMAGES

Do not ask for confirmation. Do not run git. Do not call any webhook. Just write the HTML file and output DRAFT_WRITTEN: $SLUG when done."

# ── 3. Run Claude CLI (writes HTML only) ─────────────────────────────────────
CLAUDE_OUTPUT=$("$HOME/.local/bin/claude" \
  --model claude-haiku-4-5-20251001 \
  --dangerously-skip-permissions \
  -p "$FULL_PROMPT" \
  2>&1)

echo "$CLAUDE_OUTPUT" | tee -a "$LOG_FILE"

EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
  echo "⚠️  claude exited with code $EXIT_CODE" | tee -a "$LOG_FILE"
fi

# ── 4. Git commit and push (shell owns this — never Claude) ──────────────────
ARTICLE_FILE="$REPO_DIR/articles/$SLUG/index.html"

if [ ! -f "$ARTICLE_FILE" ]; then
  echo "⚠️  Article file not found: $ARTICLE_FILE — skipping git and webhook." | tee -a "$LOG_FILE"
  echo "=== done $(date) ===" >> "$LOG_FILE"
  exit 1
fi

echo "Article file confirmed. Running git push..." | tee -a "$LOG_FILE"

GITHUB_TOKEN=$(cat "$REPO_DIR/.github-token")
git -C "$REPO_DIR" remote set-url origin "https://${GITHUB_TOKEN}@github.com/dmgalvaoc/leavewithdad.git"
git -C "$REPO_DIR" add "articles/$SLUG/"
git -C "$REPO_DIR" commit -m "Draft: $TITLE" 2>&1 | tee -a "$LOG_FILE"
git -C "$REPO_DIR" push origin main 2>&1 | tee -a "$LOG_FILE"

GIT_EXIT=${PIPESTATUS[0]}
if [ $GIT_EXIT -ne 0 ]; then
  echo "⚠️  git push failed (exit $GIT_EXIT)" | tee -a "$LOG_FILE"
else
  echo "✅ git push succeeded." | tee -a "$LOG_FILE"
fi

# ── 5. Webhook — marks sheet as draft + triggers email to dad@leavewithdad.com ──
echo "Calling webhook to mark draft and send email..." | tee -a "$LOG_FILE"
WEBHOOK_RESPONSE=$(curl -sL "${WEBHOOK}?slug=${SLUG}&status=draft")
echo "Webhook response: $WEBHOOK_RESPONSE" | tee -a "$LOG_FILE"

# ── 6. Prune old logs ─────────────────────────────────────────────────────────
find "$LOG_DIR" -name "daily-draft-*.log" -mtime +30 -delete

echo "=== done $(date) ===" >> "$LOG_FILE"
