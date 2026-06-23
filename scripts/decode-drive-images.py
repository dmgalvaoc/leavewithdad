#!/usr/bin/env python3
"""
decode-drive-images.py
Reads Drive MCP download cache files (base64 JSON), decodes to real images,
saves to the article slug folder, and updates the HTML with local paths.
"""
import json, base64, os, sys, re, glob

REPO = "/Users/diegogalvao/Desktop/leavewithdad"
SLUG = sys.argv[1] if len(sys.argv) > 1 else "diy-slab"
ARTICLE_DIR = os.path.join(REPO, "articles", SLUG)

# ── 1. Find Drive MCP cache files ──────────────────────────────────────────
CACHE_GLOB = "/var/folders/40/**/tool-results/mcp-badfa243-*-download_file_content-*.txt"
cache_files = glob.glob(CACHE_GLOB, recursive=True)

if not cache_files:
    print("ERROR: No Drive MCP cache files found. Re-run the Claude download first.")
    sys.exit(1)

print(f"Found {len(cache_files)} cache file(s)")

# ── 2. Decode each cache file ──────────────────────────────────────────────
id_to_local = {}  # drive_file_id → local filename

for path in cache_files:
    try:
        size = os.path.getsize(path)
        if size < 1000:
            continue
        print(f"  Reading {os.path.basename(path)} ({size//1024//1024} MB)...")
        with open(path, "r") as f:
            data = json.load(f)
        file_id   = data.get("id", "unknown")
        mime_type = data.get("mimeType", "image/jpeg")
        b64       = data.get("content", "")
        if not b64:
            print(f"    No content in {os.path.basename(path)} — skipping")
            continue
        ext = "jpg" if "jpeg" in mime_type else mime_type.split("/")[-1]
        out_name  = f"img-{file_id[:8]}.{ext}"
        out_path  = os.path.join(ARTICLE_DIR, out_name)
        binary    = base64.b64decode(b64)
        is_image  = (binary[:2] == b'\xff\xd8'
                  or binary[:8] == b'\x89PNG\r\n\x1a\n'
                  or binary[:4] == b'GIF8')
        if not is_image:
            print(f"    {file_id[:8]}: decoded bytes don't look like an image — skipping")
            continue
        with open(out_path, "wb") as out:
            out.write(binary)
        id_to_local[file_id] = out_name
        print(f"    Saved: {out_name} ({len(binary)//1024} KB)")
    except Exception as e:
        print(f"  ERROR with {os.path.basename(path)}: {e}")

if not id_to_local:
    print("\nERROR: No images decoded. Cache files may be stale — re-download from Claude.")
    sys.exit(1)

# ── 3. Update HTML with local paths ───────────────────────────────────────
pattern = re.compile(r'https://lh3\.googleusercontent\.com/d/([\w-]+)')
html_path = os.path.join(ARTICLE_DIR, "index.html")

if os.path.exists(html_path):
    with open(html_path, "r") as f:
        html = f.read()
    changed = False
    for m in pattern.finditer(html):
        fid = m.group(1)
        if fid in id_to_local:
            html = html.replace(m.group(0), id_to_local[fid])
            changed = True
    if changed:
        with open(html_path, "w") as f:
            f.write(html)
        print(f"  Updated: {html_path}")

print(f"\n✓ Done. {len(id_to_local)} image(s) decoded and HTML updated.")
