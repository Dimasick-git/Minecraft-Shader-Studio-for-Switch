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
    current = json.loads(MATRIX.read_text(encoding="utf-8"))["rolling"]
    if offline: return current
    atmosphere = fetch_json(ATM_API)["tag_name"].lstrip("v")
    page = fetch_text(MC_PAGE)
    versions = re.findall(r"Bedrock Edition\s+(\d+(?:\.\d+){1,3})", page, re.I)
    if not versions: raise RuntimeError("Не удалось определить Minecraft Bedrock")
    minecraft = max(versions, key=lambda x: tuple(map(int, x.split('.'))))
    return {"minecraft_bedrock": minecraft, "atmosphere": atmosphere}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--offline", action="store_true"); ap.add_argument("--json", action="store_true")
    args = ap.parse_args(); result = detect(args.offline)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else f"Minecraft={result['minecraft_bedrock']} Atmosphère={result['atmosphere']}")
if __name__ == "__main__": main()
