#!/usr/bin/env python3
"""
python3 ~/Desktop/leavewithdad/scripts/decode-beer-fridge.py
Run this NOW — the temp files expire.
"""
import json, base64, os, subprocess

REPO = os.path.expanduser("~/Desktop/leavewithdad")

TR = ("/var/folders/40/q255cwnd6xj5nxl0qh1qvp2r0000gn/T/claude-hostloop-plugins"
      "/b763ab2874e78b46/projects"
      "/-Users-diegogalvao-Library-Application-Support-Claude-local-agent-mode-sessions"
      "-a2620b84-cabd-4d77-8d38-7feca7d6a85b"
      "-253719ac-af7d-4399-bd8a-5e09c4f9e0cd"
      "-local-eeea7981-c538-4f03-8cd7-66f9b467d769-out-20k7ud"
      "/10f54a5e-a2aa-4540-84e5-0e627e553c69/tool-results")

IMAGES = [
    (f"{TR}/mcp-badfa243-d8e6-4962-9ec2-99b624f10325-download_file_content-1781813864300.txt",
     "articles/beer-fridge/1x-Sp5TXfyj9CSvGnl5m6h7cGnbJ5Agm6.jpg"),
    (f"{TR}/mcp-badfa243-d8e6-4962-9ec2-99b624f10325-download_file_content-1781813871486.txt",
     "articles/beer-fridge/17PUeT7hEsPbbomXcLNiOg_AbZm9P_IFg.jpg"),
]

decoded = []
for src, dest_rel in IMAGES:
    dest = os.path.join(REPO, dest_rel)
    if not os.path.exists(src):
        print(f"✗ Temp file missing: {os.path.basename(src)}")
        print("  Ask Claude to re-download from Drive and run this script again immediately.")
        continue
    print(f"Decoding {os.path.basename(dest_rel)}...")
    with open(src) as f:
        data = json.load(f)
    img = base64.b64decode(data["content"])
    if img[:2] != b'\xff\xd8' and img[:4] != b'\x89PNG':
        print(f"  ✗ Not a valid image — {img[:8].hex()}"); continue
    with open(dest, "wb") as f:
        f.write(img)
    decoded.append(dest_rel)
    print(f"  ✓ {len(img)//1024}KB")

if not decoded:
    input("Nothing decoded. Press Enter…"); exit(1)

print("\nPushing to GitHub...")
token = open(os.path.join(REPO, ".github-token")).read().strip()
remote = f"https://{token}@github.com/dmgalvaoc/leavewithdad.git"
for lk in ["HEAD.lock","index.lock","refs/remotes/origin/main.lock"]:
    try: os.remove(os.path.join(REPO,".git",lk))
    except: pass
head = subprocess.check_output(["git","-C",REPO,"ls-remote",remote,"HEAD"],text=True).split()[0]
subprocess.run(["git","-C",REPO,"read-tree",head],check=True)
subprocess.run(["git","-C",REPO,"add","articles/beer-fridge/"],check=True)
tree = subprocess.check_output(["git","-C",REPO,"write-tree"],text=True).strip()
env  = {**os.environ,"GIT_AUTHOR_NAME":"Dad","GIT_AUTHOR_EMAIL":"dad@leavewithdad.com",
        "GIT_COMMITTER_NAME":"Dad","GIT_COMMITTER_EMAIL":"dad@leavewithdad.com"}
commit = subprocess.check_output(
    ["git","-C",REPO,"commit-tree",tree,"-p",head,
     "-m","Fix: real beer-fridge images from Drive (replace HTML placeholders)"],
    env=env,text=True).strip()
r = subprocess.run(["git","-C",REPO,"push",remote,f"{commit}:refs/heads/main"],
    capture_output=True,text=True)
print((r.stdout+r.stderr).strip())
print("\n✓ Done — https://leavewithdad.com/articles/beer-fridge/" if r.returncode==0 else "\n✗ Push failed")
