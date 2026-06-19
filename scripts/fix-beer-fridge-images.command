#!/usr/bin/env python3
"""
fix-beer-fridge-images.command
Double-click to re-download the beer fridge images from Google Drive and push.

publish.sh used drive.google.com/uc?export=download which returned a login page.
This script uses lh3.googleusercontent.com/d/{fileId} — the public direct URL.
"""
import os, sys, urllib.request, subprocess

REPO         = os.path.expanduser("~/Desktop/leavewithdad")
ARTICLE_DIR  = os.path.join(REPO, "articles/beer-fridge")
DRAFT_DIR    = os.path.join(REPO, "drafts/beer-fridge")
TOKEN_FILE   = os.path.join(REPO, ".github-token")

if not os.path.exists(TOKEN_FILE):
    print("ERROR: .github-token not found"); sys.exit(1)
GITHUB_TOKEN = open(TOKEN_FILE).read().strip()
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

# The filenames are the Drive file IDs (set by publish.sh)
IMAGES = [
    "1x-Sp5TXfyj9CSvGnl5m6h7cGnbJ5Agm6.jpg",
    "17PUeT7hEsPbbomXcLNiOg_AbZm9P_IFg.jpg",
]

print("=" * 55)
print("  fix-beer-fridge-images — leavewithdad.com")
print("=" * 55)
print()

downloaded = []
for filename in IMAGES:
    file_id   = filename.replace(".jpg", "")
    url       = f"https://lh3.googleusercontent.com/d/{file_id}"
    out_path  = os.path.join(ARTICLE_DIR, filename)
    draft_path = os.path.join(DRAFT_DIR, filename)
    print(f"→ Downloading {filename}...")
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        if data[:2] == b'\xff\xd8' or data[:4] == b'\x89PNG':
            with open(out_path, "wb") as f: f.write(data)
            with open(draft_path, "wb") as f: f.write(data)
            downloaded.append(filename)
            print(f"  ✓ {filename} ({len(data)//1024}KB)")
        else:
            print(f"  ✗ Got non-image response — Drive file may not be publicly shared")
            print(f"    First bytes: {data[:40]}")
    except Exception as e:
        print(f"  ✗ {e}")

if not downloaded:
    print("\nERROR: No images downloaded. Make sure the Drive images are set to 'Anyone with the link'.")
    input("Press Enter to close…"); sys.exit(1)

print(f"\n→ Committing {len(downloaded)} image(s) to GitHub...")
try:
    remote_url  = f"https://{GITHUB_TOKEN}@github.com/dmgalvaoc/leavewithdad.git"
    for lock in ["HEAD.lock", "index.lock", "refs/remotes/origin/main.lock"]:
        try: os.remove(os.path.join(REPO, ".git", lock))
        except: pass
    remote_head = subprocess.check_output(
        ["git", "-C", REPO, "ls-remote", remote_url, "HEAD"], text=True).split()[0]
    subprocess.run(["git", "-C", REPO, "read-tree", remote_head], check=True)
    subprocess.run(["git", "-C", REPO, "add",
                    "articles/beer-fridge/", "drafts/beer-fridge/"], check=True)
    tree = subprocess.check_output(["git", "-C", REPO, "write-tree"], text=True).strip()
    env  = {**os.environ,
            "GIT_AUTHOR_NAME": "Dad",    "GIT_AUTHOR_EMAIL": "dad@leavewithdad.com",
            "GIT_COMMITTER_NAME": "Dad", "GIT_COMMITTER_EMAIL": "dad@leavewithdad.com"}
    commit = subprocess.check_output(
        ["git", "-C", REPO, "commit-tree", tree, "-p", remote_head,
         "-m", "Fix: replace HTML placeholders with real beer-fridge images"],
        env=env, text=True).strip()
    result = subprocess.run(
        ["git", "-C", REPO, "push", remote_url, f"{commit}:refs/heads/main"],
        capture_output=True, text=True)
    print((result.stdout + result.stderr).strip())
    if result.returncode == 0:
        print("\n✓ Done! Beer fridge images are live.")
        print("  https://leavewithdad.com/articles/beer-fridge/")
    else:
        print("\n✗ Push failed — see output above.")
except Exception as e:
    print(f"  ERROR: {e}")

input("\nPress Enter to close…")
