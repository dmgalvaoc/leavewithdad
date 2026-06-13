#!/bin/bash
# fix-images.command
# Downloads Drive images for a slug, saves locally, updates HTML, commits + pushes
# Usage: double-click, or: bash scripts/fix-images.command diy-slab
# If no arg given, defaults to diy-slab

set -e
cd "$(dirname "$0")/.."
REPO="$(pwd)"
SLUG="${1:-diy-slab}"
LIVE_DIR="$REPO/$SLUG"
DRAFT_DIR="$REPO/drafts/$SLUG"

echo "=== Fixing images for: $SLUG ==="

python3 - "$LIVE_DIR" "$DRAFT_DIR" <<'PYEOF'
import sys, re, os, urllib.request, shutil

def download_drive_image(file_id, out_path):
    url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        # Check if Google returned an HTML warning page instead of image
        if data[:4] in (b'\xff\xd8\xff\xe0', b'\xff\xd8\xff\xe1', b'\x89PNG'):
            with open(out_path, "wb") as f:
                f.write(data)
            print(f"  Downloaded: {os.path.basename(out_path)} ({len(data)//1024} KB)")
            return True
        # Try the export=view variant
        url2 = f"https://drive.google.com/uc?export=view&id={file_id}"
        req2 = urllib.request.Request(url2, headers=headers)
        with urllib.request.urlopen(req2, timeout=30) as resp2:
            data2 = resp2.read()
        if len(data2) > 10000:
            with open(out_path, "wb") as f:
                f.write(data2)
            print(f"  Downloaded (view): {os.path.basename(out_path)} ({len(data2)//1024} KB)")
            return True
        print(f"  WARNING: got small/HTML response for {file_id} — skipping")
        return False
    except Exception as e:
        print(f"  ERROR downloading {file_id}: {e}")
        return False

live_dir = sys.argv[1]
draft_dir = sys.argv[2]
html_file = os.path.join(live_dir, "index.html")

if not os.path.exists(html_file):
    print(f"ERROR: {html_file} not found")
    sys.exit(1)

with open(html_file, "r") as f:
    html = f.read()

pattern = re.compile(r'https://lh3\.googleusercontent\.com/d/([\w-]+)')
seen = {}
new_html = html

for m in pattern.finditer(html):
    file_id = m.group(1)
    if file_id in seen:
        if seen[file_id]:
            new_html = new_html.replace(m.group(0), seen[file_id])
        continue
    filename = f"img-{file_id[:8]}.jpg"
    out_path = os.path.join(live_dir, filename)
    ok = download_drive_image(file_id, out_path)
    if ok:
        seen[file_id] = filename
        new_html = new_html.replace(m.group(0), filename)
        # Also update draft
        draft_out = os.path.join(draft_dir, filename)
        shutil.copy2(out_path, draft_out)
    else:
        seen[file_id] = None

with open(html_file, "w") as f:
    f.write(new_html)

# Also update draft HTML
draft_html = os.path.join(draft_dir, "index.html")
if os.path.exists(draft_html):
    with open(draft_html, "r") as f:
        dhtml = f.read()
    for orig_id, local_name in seen.items():
        if local_name:
            dhtml = dhtml.replace(f"https://lh3.googleusercontent.com/d/{orig_id}", local_name)
    with open(draft_html, "w") as f:
        f.write(dhtml)

print("  HTML updated with local image paths")
PYEOF

echo ""
echo "=== Committing ==="
GITHUB_TOKEN=$(cat "$REPO/.github-token")
git -C "$REPO" remote set-url origin "https://${GITHUB_TOKEN}@github.com/dmgalvaoc/leavewithdad.git"
rm -f "$REPO/.git/HEAD.lock" "$REPO/.git/index.lock" "$REPO/.git/refs/remotes/origin/main.lock" 2>/dev/null || true

REMOTE_HEAD=$(git -C "$REPO" ls-remote origin HEAD | cut -f1)
git -C "$REPO" read-tree "$REMOTE_HEAD"
git -C "$REPO" add "$SLUG/" drafts/"$SLUG"/
TREE=$(git -C "$REPO" write-tree)
COMMIT=$(git -C "$REPO" commit-tree "$TREE" -p "$REMOTE_HEAD" -m "Fix: download Drive images locally for $SLUG")
git -C "$REPO" push origin "${COMMIT}:refs/heads/main"

echo ""
echo "✓ Done. Images are now local and live at https://leavewithdad.com/$SLUG/"
echo "Press any key to close..."
read -n 1
