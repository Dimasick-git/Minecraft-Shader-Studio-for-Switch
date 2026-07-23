#!/usr/bin/env python3
"""Rolling version detector. Author: Dimasick-git."""
from __future__ import annotations
import argparse, json, re, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "compatibility" / "matrix.json"
ATM_API = "https://api.github.com/repos/Atmosphere-NX/Atmosphere/releases/latest"
MC_PAGE = "https://feedback.minecraft.net/hc/en-us/sections/360001186971-Release-Changelogs"

def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "MSS-version-bot/0.1"})
    with urllib.request.urlopen(req, timeout=20) as r: return json.load(r)

def fetch_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": "MSS-version-bot/0.1"})
    with urllib.request.urlopen(req, timeout=20) as r: return r.read().decode("utf-8", "replace")

def detect(offline=False):
    data = json.loads(MATRIX.read_text(encoding="utf-8"))
    current = data["rolling"]
    if offline: return current
    
    # Detect Atmosphere
    atmosphere = fetch_json(ATM_API)["tag_name"].lstrip("v")
    
    # Detect Minecraft
    page = fetch_text(MC_PAGE)
    versions = re.findall(r"Bedrock Edition\s+(\d+(?:\.\d+){1,3})", page, re.I)
    if not versions: raise RuntimeError("Не удалось определить Minecraft Bedrock")
    minecraft = max(versions, key=lambda x: tuple(map(int, x.split('.'))))
    
    # Mock Build ID detection (in real world, this would scrape a database or API)
    # For automation, we'll generate a placeholder if it's a new version
    build_id = "UNKNOWN"
    if minecraft == current["minecraft_bedrock"]:
        build_id = current.get("build_id", "UNKNOWN")
    
    return {"minecraft_bedrock": minecraft, "atmosphere": atmosphere, "build_id": build_id}

def update_matrix(result):
    data = json.loads(MATRIX.read_text(encoding="utf-8"))
    changed = False
    
    if data["rolling"]["minecraft_bedrock"] != result["minecraft_bedrock"] or \
       data["rolling"]["atmosphere"] != result["atmosphere"]:
        data["rolling"]["minecraft_bedrock"] = result["minecraft_bedrock"]
        data["rolling"]["atmosphere"] = result["atmosphere"]
        data["rolling"]["build_id"] = result["build_id"]
        data["rolling"]["checked_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
        
        # Add to targets if not exists
        exists = any(t["minecraft"] == result["minecraft_bedrock"] for t in data["targets"])
        if not exists:
            data["targets"].insert(0, {
                "minecraft": result["minecraft_bedrock"],
                "atmosphere_min": result["atmosphere"],
                "status": "detected",
                "notes": "Automatically detected via GitHub Actions"
            })
        changed = True
    
    if changed:
        MATRIX.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return True
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--update", action="store_true")
    args = ap.parse_args()
    
    result = detect(args.offline)
    if args.update:
        updated = update_matrix(result)
        if updated:
            print("Matrix updated.")
        else:
            print("No changes detected.")
    
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Minecraft={result['minecraft_bedrock']} Atmosphère={result['atmosphere']} BuildID={result.get('build_id', 'N/A')}")
if __name__ == "__main__": main()
