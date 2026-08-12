#!/usr/bin/env python3
"""Загрузка host-тулчейна для Vulkan-пайплайна MSS.

Скачивает только открытые компоненты:

1. `shaderc` из `veka0/bgfx-mcbe` для host-машины;
2. закреплённые по Git-ревизии хедеры BGFX для исходников `.sc`;
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
import hashlib
import platform
import stat
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHADERC_RELEASE = "https://github.com/veka0/bgfx-mcbe/releases/download/binaries/"
# Закреплённый публичный commit, а не moving target `master`.
BGFX_REVISION = "3aefb30faf793ce94d4eef0f29918da0684fc30e"
BGFX_RAW = f"https://raw.githubusercontent.com/veka0/bgfx-mcbe/{BGFX_REVISION}/src/"
REFERENCE_MERGE_RELEASE = "https://github.com/devendrn/newb-shader/releases/download/dev/"

MAX_DOWNLOAD_BYTES = 64 * 1024 * 1024
MAX_ZIP_ENTRIES = 512
MAX_ZIP_UNCOMPRESSED_BYTES = 128 * 1024 * 1024

# Хеши вычислены из файлов публичного release/binaries и закреплённой BGFX_REVISION.
# Добавляйте новые значения осознанно после ручной проверки upstream артефакта.
EXPECTED_BINARY_SHA256 = {
    "shaderc-linux-x64.zip": "7b0b2679d788f3d86cfdb8afe33f545e992465b94127b5e6bd85807b261ff87b",
}
EXPECTED_HEADER_SHA256 = {
    "bgfx_shader.sh": "cd9c660d6ea4f96b0f7c8ed6f18cc96c8c3ec151b5e557c432f176e44ad89de9",
    "bgfx_compute.sh": "214851a85bc055b9f351ca93484a7efa17f3df06f06129b6606a2918bbb7d3cd",
}

SHADERC_PLATFORMS = {
    ("Linux", "x86_64"): "shaderc-linux-x64.zip",
    ("Windows", "AMD64"): "shaderc-win-x64.zip",
    ("Darwin", "x86_64"): "shaderc-osx-x64.zip",
    ("Darwin", "arm64"): "shaderc-osx-x64.zip",  # через Rosetta
    ("Linux", "aarch64"): "shaderc-android-arm64.zip",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_sha256(path: Path, expected: str, label: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        path.unlink(missing_ok=True)
        raise RuntimeError(
            f"SHA-256 не совпадает для {label}: ожидался {expected}, получен {actual}. "
            "Файл удалён; не запускайте непроверенный toolchain."
        )


def download(url: str, destination: Path) -> None:
    print(f"  <- {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "MSS-toolchain/0.3"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(MAX_DOWNLOAD_BYTES + 1)
    if len(data) < 100:
        raise RuntimeError(f"Подозрительно маленький файл ({len(data)} байт): {url}")
    if len(data) > MAX_DOWNLOAD_BYTES:
        raise RuntimeError(f"Скачивание превышает лимит {MAX_DOWNLOAD_BYTES} байт: {url}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    print(f"  -> {destination} ({len(data)} байт)")


def extract_zip_safely(archive: Path, destination: Path) -> list[str]:
    """Распаковать ZIP без traversal, symlink и zip-bomb сценариев."""
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(archive) as zip_file:
        members = zip_file.infolist()
        uncompressed_size = sum(member.file_size for member in members)
        if len(members) > MAX_ZIP_ENTRIES:
            raise RuntimeError(f"ZIP содержит слишком много записей: {len(members)}")
        if uncompressed_size > MAX_ZIP_UNCOMPRESSED_BYTES:
            raise RuntimeError(
                "ZIP после распаковки превысит безопасный лимит "
                f"{MAX_ZIP_UNCOMPRESSED_BYTES} байт"
            )
        for member in members:
            target = (root / member.filename).resolve()
            mode = member.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise RuntimeError(f"ZIP содержит недопустимую symbolic link: {member.filename}")
            if target != root and root not in target.parents:
                raise RuntimeError(f"ZIP содержит небезопасный путь: {member.filename}")
        zip_file.extractall(root)
    return [member.filename for member in members]


def fetch_shaderc(dest_dir: Path, platform_key: str | None, allow_unverified: bool) -> Path | None:
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
    expected = EXPECTED_BINARY_SHA256.get(filename)
    if expected:
        verify_sha256(binary, expected, filename)
        print(f"  SHA-256 verified: {binary.name}")
    elif allow_unverified:
        print(f"  ! Нет закреплённого SHA-256 для {filename}; разрешено явным флагом")
    else:
        binary.unlink(missing_ok=True)
        raise RuntimeError(
            f"Для {filename} нет закреплённого SHA-256. Добавьте проверенный хеш "
            "в скрипт или повторите только при явном --allow-unverified-toolchain."
        )
    return binary


def fetch_headers(include_dir: Path) -> None:
    for header, expected in EXPECTED_HEADER_SHA256.items():
        destination = include_dir / header
        download(BGFX_RAW + header, destination)
        verify_sha256(destination, expected, f"BGFX header {header}")
        print(f"  SHA-256 verified: {header}")


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
        "--allow-unverified-toolchain",
        action="store_true",
        help="разрешить shaderc для платформы без закреплённого SHA-256; не рекомендуется",
    )
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
        default=ROOT / "toolchains" / "reference-merge",
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
    binary = fetch_shaderc(args.bin_dir, args.platform_key, args.allow_unverified_toolchain)
    print(f"Скачиваю хедеры BGFX (revision {BGFX_REVISION[:12]})...")
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
