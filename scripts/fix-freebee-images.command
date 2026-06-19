#!/usr/bin/env python3
"""
fix-freebee-images.command
Double-click to fix broken Freebee article images.

The Freebee CDN uses expiring AWS signed URLs. This script:
  1. Fetches fresh image URLs from ridefreebee.com (they sign on every page load)
  2. Downloads the images locally
  3. Updates the article HTML to use local filenames
  4. Commits + pushes to GitHub
"""
import re, os, subprocess, urllib.request, sys

REPO        = os.path.expanduser("~/Desktop/leavewithdad")
ARTICLE_DIR = os.path.join(REPO, "articles/freebee-plantation-electric-rideshare")
TOKEN_FILE  = os.path.join(REPO, ".github-token")

if not os.path.exists(TOKEN_FILE):
    print("ERROR: .github-token not found"); sys.exit(1)
GITHUB_TOKEN = open(TOKEN_FILE).read().strip()

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

# Stable base64 fingerprints of each S3 file embedded in the imgproxy URLs.
# The HMAC signature prefix changes with each signing, but the base64 S3 path is constant.
IMAGE_TARGETS = [
    # (local_filename, stable_base64_fragment, primary_page_to_search)
    ("freebee-hero.jpg",
     "aHR0cHM6Ly9mcmVlYmVlLXpvbmVzLnMzLmFtYXpvbmF3cy5jb20vbWVkaWEvMjAyNS8wNi8wMy82MzIzZmNiOC",
     "https://ridefreebee.com/service-areas/plantation"),
    ("freebee-midtown.jpg",
     "aHR0cHM6Ly9mcmVlYmVlLXpvbmVzLnMzLmFtYXpvbmF3cy5jb20vbWVkaWEvMjAyNi8wMy8xNi84NzE4NmQ2Ny0",
     "https://ridefreebee.com/"),
    ("freebee-fleet.jpg",
     "aHR0cHM6Ly9mcmVlYmVlLXpvbmVzLnMzLmFtYXpvbmF3cy5jb20vbWVkaWEvMjAyNS8wOC8xMi85ZDc2MWRkNC0",
     "https://ridefreebee.com/"),
]

FALLBACK_PAGES = [
    "https://ridefreebee.com/service-areas",
    "https://ridefreebee.com/service-areas/aventura",
    "https://ridefreebee.com/service-areas/fort-lauderdale",
]

APP_IMG_URL  = ("https://ridefreebee.com/_next/image"
                "?url=%2F_next%2Fstatic%2Fmedia%2Ffreebee-phones.1c3f6ebc.png&w=640&q=75")
APP_IMG_FILE = "freebee-app.png"


def fetch_text(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", errors="ignore")

def fetch_bytes(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


print("=" * 55)
print("  fix-freebee-images — leavewithdad.com")
print("=" * 55)

page_cache = {}
def get_page(url):
    if url not in page_cache:
        print(f"  fetching {url}")
        try:    page_cache[url] = fetch_text(url)
        except Exception as e:
            print(f"  WARNING: {e}"); page_cache[url] = ""
    return page_cache[url]


# ── Step 1: find fresh signed URLs and download ────────────────────────────────
print("\n→ Downloading vehicle images...")
downloaded = {}

for (filename, fingerprint, search_url) in IMAGE_TARGETS:
    out_path    = os.path.join(ARTICLE_DIR, filename)
    search_list = [search_url] + FALLBACK_PAGES
    img_url     = None
    for page_url in search_list:
        html    = get_page(page_url)
        pattern = (r'https://img\.ridefreebee\.com/[A-Za-z0-9_\-]+/rs:fit:\d+:\d+:\d+/'
                   + re.escape(fingerprint[:40]) + r'[A-Za-z0-9=_\-\?&%]*')
        m = re.search(pattern, html)
        if m:
            img_url = m.group(0)
            break
    if img_url:
        try:
            data = fetch_bytes(img_url)
            with open(out_path, "wb") as f: f.write(data)
            downloaded[filename] = True
            print(f"  ✓ {filename} ({len(data)//1024}KB)")
        except Exception as e:
            print(f"  ✗ {filename}: {e}"); downloaded[filename] = False
    else:
        print(f"  ✗ {filename}: URL not found on Freebee pages")
        downloaded[filename] = False


# ── Step 2: app screenshot (stable asset) ─────────────────────────────────────
print("\n→ Downloading app screenshot...")
try:
    data = fetch_bytes(APP_IMG_URL)
    with open(os.path.join(ARTICLE_DIR, APP_IMG_FILE), "wb") as f: f.write(data)
    downloaded[APP_IMG_FILE] = True
    print(f"  ✓ {APP_IMG_FILE} ({len(data)//1024}KB)")
except Exception as e:
    print(f"  ✗ {APP_IMG_FILE}: {e}"); downloaded[APP_IMG_FILE] = False


# ── Step 3: update HTML ────────────────────────────────────────────────────────
print("\n→ Updating article HTML...")
html_path = os.path.join(ARTICLE_DIR, "index.html")
with open(html_path) as f: html = f.read()

for (filename, fingerprint, _) in IMAGE_TARGETS:
    if downloaded.get(filename):
        pattern = (r'https://img\.ridefreebee\.com/[^\s"\']*'
                   + re.escape(fingerprint[:30]) + r'[^\s"\']*')
        new_html = re.sub(pattern, filename, html)
        if new_html != html:
            html = new_html
            print(f"  Replaced → {filename}")

if downloaded.get(APP_IMG_FILE):
    html = re.sub(
        r'https://ridefreebee\.com/_next/image\?url=%2F_next%2Fstatic%2Fmedia%2Ffreebee-phones[^\s"\']*',
        APP_IMG_FILE, html)

with open(html_path, "w") as f: f.write(html)
print("  ✓ HTML saved")


# ── Step 4: git plumbing commit + push ────────────────────────────────────────
print("\n→ Committing and pushing to GitHub...")
try:
    remote_url = f"https://{GITHUB_TOKEN}@github.com/dmgalvaoc/leavewithdad.git"
    for lock in ["HEAD.lock", "index.lock", "refs/remotes/origin/main.lock"]:
        try: os.remove(os.path.join(REPO, ".git", lock))
        except: pass
    remote_head = subprocess.check_output(
        ["git", "-C", REPO, "ls-remote", remote_url, "HEAD"], text=True).split()[0]
    subprocess.run(["git", "-C", REPO, "read-tree", remote_head], check=True)
    subprocess.run(["git", "-C", REPO, "add",
                    "articles/freebee-plantation-electric-rideshare/"], check=True)
    tree = subprocess.check_output(["git", "-C", REPO, "write-tree"], text=True).strip()
    env  = {**os.environ,
            "GIT_AUTHOR_NAME": "Dad",    "GIT_AUTHOR_EMAIL": "dad@leavewithdad.com",
            "GIT_COMMITTER_NAME": "Dad", "GIT_COMMITTER_EMAIL": "dad@leavewithdad.com"}
    commit = subprocess.check_output(
        ["git", "-C", REPO, "commit-tree", tree, "-p", remote_head,
         "-m", "Fix: host Freebee images locally (expired CDN URLs)"],
        env=env, text=True).strip()
    result = subprocess.run(
        ["git", "-C", REPO, "push", remote_url, f"{commit}:refs/heads/main"],
        capture_output=True, text=True)
    print((result.stdout + result.stderr).strip())
    if result.returncode == 0:
        print("\n✓ Done! Images fixed and live.")
    else:
        print("\n✗ Push failed — see output above.")
except Exception as e:
    print(f"  ERROR: {e}")

input("\nPress Enter to close…")
