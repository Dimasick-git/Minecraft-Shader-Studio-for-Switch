#!/usr/bin/env python3
"""Загрузка тулчейна Vulkan-пайплайна. Author: Dimasick-git.

Скачивает:
1. shaderc (сборка bgfx-mcbe от veka0) — компилятор bgfx SC → SPIR-V и др.
2. Шейдерные хедеры bgfx (bgfx_shader.sh, bgfx_compute.sh) для include.
3. (опционально, --vanilla) сериализованные ванильные материалы
   (*.material.json) из dev-релиза newb-shader — для merge_source.

Ванильные material.bin из ДАМПА вашей копии игры этот скрипт не заменяет:
для финальной сборки под конкретную версию Switch рекомендуется merge с
файлами из собственного дампа (см. docs/wiki/SWITCH_GUIDE.md).

Только стандартная библиотека. Пример:
    python3 scripts/fetch_toolchain.py --vanilla
"""
from __future__ import annotations

import argparse
import os
import platform
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SHADERC_RELEASE = "https://github.com/veka0/bgfx-mcbe/releases/download/binaries/"
BGFX_RAW = "https://raw.githubusercontent.com/veka0/bgfx-mcbe/master/src/"
VANILLA_RELEASE = "https://github.com/devendrn/newb-shader/releases/download/dev/"

SHADERC_PLATFORMS = {
    ("Linux", "x86_64"): "shaderc-linux-x64.zip",
    ("Windows", "AMD64"): "shaderc-win-x64.zip",
    ("Darwin", "x86_64"): "shaderc-osx-x64.zip",
    ("Darwin", "arm64"): "shaderc-osx-x64.zip",  # через Rosetta
    ("Linux", "aarch64"): "shaderc-android-arm64.zip",
}


def download(url: str, dest: Path) -> None:
    print(f"  <- {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "MSS-toolchain/0.2"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    if len(data) < 100:
        raise RuntimeError(f"Подозрительно маленький файл ({len(data)} байт): {url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    print(f"  -> {dest} ({len(data)} байт)")


def fetch_shaderc(dest_dir: Path, platform_key: str | None) -> Path | None:
    key = (platform.system(), platform.machine())
    filename = SHADERC_PLATFORMS.get(key) if platform_key is None else f"shaderc-{platform_key}.zip"
    if not filename:
        print(f"! Неизвестная платформа {key}: скачайте вручную из {SHADERC_RELEASE}")
        return None
    archive = dest_dir / filename
    download(SHADERC_RELEASE + filename, archive)
    with zipfile.ZipFile(archive) as z:
        z.extractall(dest_dir)
        members = z.namelist()
    archive.unlink()
    binary = None
    for name in members:
        p = dest_dir / name
        if p.is_file() and not name.endswith((".txt", ".md")):
            if not name.endswith(".exe"):
                p.chmod(p.stat().st_mode | 0o755)
            binary = p
    return binary


def fetch_headers(include_dir: Path) -> None:
    for header in ("bgfx_shader.sh", "bgfx_compute.sh"):
        download(BGFX_RAW + header, include_dir / header)


def fetch_vanilla(vanilla_dir: Path, mc_version: str) -> None:
    filename = f"src-materials-{mc_version}.zip"
    archive = vanilla_dir / filename
    download(VANILLA_RELEASE + filename, archive)
    with zipfile.ZipFile(archive) as z:
        z.extractall(vanilla_dir)
    archive.unlink()
    count = len(list(vanilla_dir.glob("*.material.json")))
    print(f"  ванильных материалов: {count}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bin-dir", type=Path, default=ROOT / "toolchains" / "bin")
    ap.add_argument("--include-dir", type=Path, default=ROOT / "examples" / "first-light" / "include")
    ap.add_argument("--vanilla", action="store_true", help="Скачать сериализованные ванильные материалы")
    ap.add_argument("--vanilla-dir", type=Path, default=ROOT / "examples" / "first-light" / "vanilla")
    ap.add_argument("--mc-version", default="1.26.10", help="Версия материалов из dev-релиза newb-shader")
    ap.add_argument("--platform", dest="platform_key", default=None,
                    help="Форсировать платформу shaderc: linux-x64, win-x64, osx-x64, android-arm64, android-arm")
    args = ap.parse_args()

    print("Скачиваю shaderc (bgfx-mcbe)...")
    binary = fetch_shaderc(args.bin_dir, args.platform_key)
    print("Скачиваю хедеры bgfx...")
    fetch_headers(args.include_dir)
    if args.vanilla:
        print(f"Скачиваю ванильные материалы {args.mc_version}...")
        fetch_vanilla(args.vanilla_dir, args.mc_version)

    print("\nГотово.")
    if binary:
        print(f"shaderc: {binary}")
        print(f"Подсказка: export MSS_SHADERC={binary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
