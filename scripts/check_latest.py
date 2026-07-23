#!/usr/bin/env python3
"""Rolling version detector. Author: Dimasick-git.

Primary sources are GitHub "releases/latest" redirects (no API rate limits,
works from Actions runners without a token):
  - Minecraft Bedrock: Mojang/bedrock-samples (official per-release mirror;
    previews are prereleases and never resolve as "latest").
  - Atmosphère: Atmosphere-NX/Atmosphere.
Fallbacks: GitHub REST API, then the minecraft.net feedback changelog page.

Bedrock version scheme is the canonical full form with the leading major:
"1.26.34" (press shorthand "26.34" is NOT stored in the matrix).
"""
from __future__ import annotations
import argparse, json, re, sys, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "compatibility" / "matrix.json"

MC_LATEST = "https://github.com/Mojang/bedrock-samples/releases/latest"
ATM_LATEST = "https://github.com/Atmosphere-NX/Atmosphere/releases/latest"
MC_API = "https://api.github.com/repos/Mojang/bedrock-samples/releases/latest"
ATM_API = "https://api.github.com/repos/Atmosphere-NX/Atmosphere/releases/latest"
MC_PAGE = "https://feedback.minecraft.net/hc/en-us/sections/360001186971-Release-Changelogs"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _headers():
    return {"User-Agent": "MSS-version-bot/0.2"}


def latest_tag_via_redirect(url):
    """Resolve a GitHub releases/latest redirect and return the tag name."""
    opener = urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request(url, headers=_headers())
    try:
        opener.open(req, timeout=20)
    except urllib.error.HTTPError as e:
        loc = e.headers.get("Location", "") if e.headers else ""
        if "/releases/tag/" in loc:
            return loc.rsplit("/releases/tag/", 1)[1].split("?")[0]
    except Exception:
        return None
    return None


def fetch_json(url):
    req = urllib.request.Request(url, headers=_headers())
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def fetch_text(url):
    req = urllib.request.Request(url, headers=_headers())
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "replace")


def normalize_bedrock(value):
    """Normalize Bedrock version notations to the canonical engine form.

    - Engine/samples tags: "v1.26.34.3" -> "1.26.34" (release keeps 3 components).
    - 2026+ changelog shorthand: "26.34" -> "1.26.34" (Mojang's changelog omits
      the leading engine major; bedrock-samples tags keep it).
    """
    v = (value or "").lstrip("vV").strip()
    if not v:
        return None
    if re.fullmatch(r"2\d\.\d+(?:\.\d+)?", v):  # bare year-style shorthand
        v = "1." + v
    parts = v.split(".")
    if len(parts) >= 4:
        v = ".".join(parts[:3])
    return v if re.fullmatch(r"1\.\d+(?:\.\d+){1,2}", v) else None


def _vtuple(v):
    return tuple(map(int, v.split(".")))


def detect_minecraft():
    """Collect candidates from all sources and return the highest version.

    bedrock-samples can lag behind hotfixes, and the changelog page can be
    unavailable (Zendesk 403 for bots) — the max across sources wins.
    """
    candidates = []
    # 1) Official Mojang bedrock-samples releases (stable only).
    v = normalize_bedrock(latest_tag_via_redirect(MC_LATEST))
    if v:
        candidates.append(v)
    # 2) GitHub API fallback.
    if not candidates:
        try:
            v = normalize_bedrock(fetch_json(MC_API).get("tag_name", ""))
            if v:
                candidates.append(v)
        except Exception:
            pass
    # 3) Changelog page (best effort): matches both "1.26.34 (Bedrock)" and "26.34 (Bedrock)".
    try:
        page = fetch_text(MC_PAGE)
        for raw in re.findall(r"\b((?:1\.)?\d{2}\.\d+(?:\.\d+)?)\s*\((?:Bedrock|bedrock)", page):
            v = normalize_bedrock(raw)
            if v:
                candidates.append(v)
    except Exception as e:
        print(f"WARN: changelog page unavailable: {e}", file=sys.stderr)
    if not candidates:
        raise RuntimeError("Не удалось определить Minecraft Bedrock")
    return max(candidates, key=_vtuple)


def detect_atmosphere():
    tag = latest_tag_via_redirect(ATM_LATEST)
    if tag:
        return tag.lstrip("vV")
    return fetch_json(ATM_API)["tag_name"].lstrip("vV")


def detect(offline=False):
    data = json.loads(MATRIX.read_text(encoding="utf-8"))
    current = data["rolling"]
    if offline:
        return current

    # Resilient detection: on failure keep current values instead of crashing the watcher.
    try:
        atmosphere = detect_atmosphere()
    except Exception as e:
        print(f"WARN: Atmosphère detection failed: {e}", file=sys.stderr)
        atmosphere = current["atmosphere"]
    try:
        minecraft = detect_minecraft()
    except Exception as e:
        print(f"WARN: Minecraft detection failed: {e}", file=sys.stderr)
        minecraft = current["minecraft_bedrock"]

    build_id = current.get("build_id", "UNKNOWN") if minecraft == current["minecraft_bedrock"] else "UNKNOWN"
    return {"minecraft_bedrock": minecraft, "atmosphere": atmosphere, "build_id": build_id}


def _is_newer(new, current):
    """Forward-only guard: sources may lag, never downgrade the matrix."""
    try:
        return _vtuple(new) > _vtuple(current)
    except Exception:
        return new != current


def update_matrix(result):
    data = json.loads(MATRIX.read_text(encoding="utf-8"))
    changed = False

    mc_newer = _is_newer(result["minecraft_bedrock"], data["rolling"]["minecraft_bedrock"])
    atm_newer = _is_newer(result["atmosphere"], data["rolling"]["atmosphere"])
    if not mc_newer:
        result = dict(result, minecraft_bedrock=data["rolling"]["minecraft_bedrock"])
    if not atm_newer:
        result = dict(result, atmosphere=data["rolling"]["atmosphere"])

    if mc_newer or atm_newer:
        data["rolling"]["minecraft_bedrock"] = result["minecraft_bedrock"]
        data["rolling"]["atmosphere"] = result["atmosphere"]
        data["rolling"]["build_id"] = result["build_id"]
        data["rolling"]["checked_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()

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
        if update_matrix(result):
            print("Matrix updated.")
        else:
            print("No changes detected.")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Minecraft={result['minecraft_bedrock']} Atmosphère={result['atmosphere']} BuildID={result.get('build_id', 'N/A')}")


if __name__ == "__main__":
    main()
