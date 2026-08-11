#!/usr/bin/env python3
"""Загрузка host-тулчейна для Vulkan-пайплайна MSS.

Скачивает только открытые компоненты:

1. `shaderc` из `veka0/bgfx-mcbe` для host-машины;
2. хедеры BGFX для исходников `.sc`;
3. опциональные сериализованные reference-материалы из dev-релиза Newb Shader.

Reference-материалы не являются Switch baseline и не заменяют material.bin,
извлечённый пользователем из RomFS той же версии Minecraft. Для установки на
Switch `mss compile --profile switch` требует именно пользовательский
`--baseline` с платформой Vulkan.

Только стандартная библиотека. Пример:
    python3 scripts/fetch_toolchain.py
    python3 scripts/fetch_toolchain.py --reference-merge
"""
from __future__ import annotations

import argparse
import platform
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHADERC_RELEASE = "https://github.com/veka0/bgfx-mcbe/releases/download/binaries/"
BGFX_RAW = "https://raw.githubusercontent.com/veka0/bgfx-mcbe/master/src/"
REFERENCE_MERGE_RELEASE = "https://github.com/devendrn/newb-shader/releases/download/dev/"

SHADERC_PLATFORMS = {
    ("Linux", "x86_64"): "shaderc-linux-x64.zip",
    ("Windows", "AMD64"): "shaderc-win-x64.zip",
    ("Darwin", "x86_64"): "shaderc-osx-x64.zip",
    ("Darwin", "arm64"): "shaderc-osx-x64.zip",  # через Rosetta
    ("Linux", "aarch64"): "shaderc-android-arm64.zip",
}


def download(url: str, dest: Path) -> None:
    print(f"  <- {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "MSS-toolchain/0.2"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
    if len(data) < 100:
        raise RuntimeError(f"Подозрительно маленький файл ({len(data)} байт): {url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    print(f"  -> {dest} ({len(data)} байт)")


def extract_zip_safely(archive: Path, destination: Path) -> list[str]:
    """Распаковать ZIP, не позволяя архиву записать файл вне destination."""
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(archive) as zip_file:
        members = zip_file.infolist()
        for member in members:
            target = (root / member.filename).resolve()
            if target != root and root not in target.parents:
                raise RuntimeError(f"ZIP содержит небезопасный путь: {member.filename}")
        zip_file.extractall(root)
    return [member.filename for member in members]


def fetch_shaderc(dest_dir: Path, platform_key: str | None) -> Path | None:
    key = (platform.system(), platform.machine())
    filename = SHADERC_PLATFORMS.get(key) if platform_key is None else f"shaderc-{platform_key}.zip"
    if not filename:
        print(f"! Неизвестная платформа {key}: скачайте вручную из {SHADERC_RELEASE}")
        return None
    archive = dest_dir / filename
    download(SHADERC_RELEASE + filename, archive)
    members = extract_zip_safely(archive, dest_dir)
    archive.unlink()
    binary = None
    for name in members:
        candidate = dest_dir / name
        if candidate.is_file() and not name.endswith((".txt", ".md")):
            if not name.endswith(".exe"):
                candidate.chmod(candidate.stat().st_mode | 0o755)
            binary = candidate
    if binary is None:
        raise RuntimeError(f"В архиве {filename} не найден исполняемый shaderc")
    return binary


def fetch_headers(include_dir: Path) -> None:
    for header in ("bgfx_shader.sh", "bgfx_compute.sh"):
        download(BGFX_RAW + header, include_dir / header)


def fetch_reference_merge(destination: Path, mc_version: str) -> None:
    filename = f"src-materials-{mc_version}.zip"
    archive = destination / filename
    download(REFERENCE_MERGE_RELEASE + filename, archive)
    extract_zip_safely(archive, destination)
    archive.unlink()
    count = len(list(destination.glob("*.material.json")))
    print(f"  reference-материалов: {count}")
    print("  Внимание: это не Switch baseline; не используйте их как --baseline.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bin-dir", type=Path, default=ROOT / "toolchains" / "bin")
    parser.add_argument("--include-dir", type=Path, default=ROOT / "toolchains" / "include")
    parser.add_argument(
        "--reference-merge",
        action="store_true",
        help="Скачать открытые reference material.json для изучения; не для Switch baseline",
    )
    parser.add_argument(
        "--vanilla",
        dest="reference_merge",
        action="store_true",
        help="Устаревший alias для --reference-merge; загружает только reference-материалы",
    )
    parser.add_argument(
        "--reference-dir",
        type=Path,
        default=ROOT / "examples" / "first-light" / "reference-merge",
    )
    parser.add_argument("--mc-version", default="1.26.10", help="Версия reference-материалов Newb Shader")
    parser.add_argument(
        "--platform",
        dest="platform_key",
        default=None,
        help="Форсировать платформу shaderc: linux-x64, win-x64, osx-x64, android-arm64, android-arm",
    )
    args = parser.parse_args()

    print("Скачиваю shaderc (bgfx-mcbe)...")
    binary = fetch_shaderc(args.bin_dir, args.platform_key)
    print("Скачиваю хедеры BGFX...")
    fetch_headers(args.include_dir)
    if args.reference_merge:
        print(f"Скачиваю reference-материалы {args.mc_version}...")
        fetch_reference_merge(args.reference_dir, args.mc_version)

    print("\nГотово.")
    if binary:
        print(f"shaderc: {binary}")
        print(f"Подсказка: export MSS_SHADERC={binary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
