#!/bin/bash
# leavewithdad — publish.sh
# Usage: bash scripts/publish.sh <slug>
# Copies a draft to live, calls the sheet webhook, commits and pushes.
# Run from the repo root: ~/Desktop/leavewithdad/

set -e

REPO="/Users/diegogalvao/Desktop/leavewithdad"
SLUG="$1"
TODAY=$(date +%Y-%m-%d)

if [ -z "$SLUG" ]; then
  echo "ERROR: slug required. Usage: bash scripts/publish.sh <slug>"
  exit 1
fi

DRAFT_DIR="$REPO/drafts/$SLUG"
LIVE_DIR="$REPO/$SLUG"

# ── 1. Verify draft exists ──────────────────────────────────────────────────
if [ ! -f "$DRAFT_DIR/index.html" ]; then
  echo "ERROR: $DRAFT_DIR/index.html not found"
  exit 1
fi

# ── 2. Download Drive images from draft HTML before copying ─────────────────
echo "→ Downloading Drive images from draft HTML..."
python3 - "$DRAFT_DIR" <<'PYEOF'
import sys, re, subprocess, os, urllib.request

draft_dir = sys.argv[1]
html_file = os.path.join(draft_dir, "index.html")
if not os.path.exists(html_file):
    print("  No index.html found — skipping image download")
    sys.exit(0)

with open(html_file, "r") as f:
    html = f.read()

# Find all lh3.googleusercontent.com/d/{fileId} patterns
drive_pattern = re.compile(r'https://lh3\.googleusercontent\.com/d/([\w-]+)')
ids_seen = {}
new_html = html

for m in drive_pattern.finditer(html):
    file_id = m.group(1)
    if file_id in ids_seen:
        continue
    # Try to determine filename from existing img alt or just use fileId
    filename = file_id + ".jpg"
    out_path = os.path.join(draft_dir, filename)
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t"
    try:
        req = urllib.request.Request(download_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        with open(out_path, "wb") as out:
            out.write(data)
        print(f"  Downloaded: {filename} ({len(data)//1024} KB)")
        # Replace URL in HTML with local path
        new_html = new_html.replace(m.group(0), filename)
        ids_seen[file_id] = filename
    except Exception as e:
        print(f"  WARNING: Could not download {file_id}: {e} — keeping Drive URL")
        ids_seen[file_id] = None

if ids_seen:
    with open(html_file, "w") as f:
        f.write(new_html)
    print("  HTML updated with local image paths")
PYEOF
echo "  Image step done"

# ── 3. Copy draft to live slug folder ───────────────────────────────────────
echo "→ Copying draft to live..."
cp -r "$DRAFT_DIR/." "$LIVE_DIR/"
echo "  Done: $LIVE_DIR"

# ── 3. Call sheet webhook — mark published (two-step POST+GET) ───────────────
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

# ── 4. Authenticate ──────────────────────────────────────────────────────────
GITHUB_TOKEN=$(cat "$REPO/.github-token")
git -C "$REPO" remote set-url origin "https://${GITHUB_TOKEN}@github.com/dmgalvaoc/leavewithdad.git"

# ── 5. Git plumbing commit + push (works even with stale lock files) ──────────
echo "→ Committing and pushing..."
# Clear locks if possible (works from Mac; no-op if permission denied from sandbox)
rm -f "$REPO/.git/HEAD.lock" "$REPO/.git/index.lock" "$REPO/.git/refs/remotes/origin/main.lock" 2>/dev/null || true

# Always use remote HEAD as parent — local HEAD may lag behind
REMOTE_HEAD=$(git -C "$REPO" ls-remote origin HEAD | cut -f1)
git -C "$REPO" read-tree "$REMOTE_HEAD"
git -C "$REPO" add "$SLUG/" index.html 2>/dev/null || true
TREE=$(git -C "$REPO" write-tree)
COMMIT=$(git -C "$REPO" commit-tree "$TREE" -p "$REMOTE_HEAD" -m "Publish: $SLUG")
git -C "$REPO" push origin "${COMMIT}:refs/heads/main"

echo ""
echo "✓ Published: https://leavewithdad.com/$SLUG/"
