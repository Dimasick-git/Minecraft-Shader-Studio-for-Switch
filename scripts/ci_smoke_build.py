#!/usr/bin/env python3
"""Создать CI smoke-артефакт без Nintendo RomFS и без игровых material.bin.

Скрипт берёт открытый `*.material.json` из reference merge source, временно
помещает его в игнорируемый merge-source example и выполняет только
`--unsafe-no-baseline`. Полученный material.bin имеет статус smoke-build-only;
он предназначен для анализа CI и не является файлом для установки на Switch.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = {
    "first-light": ("Sky", "FIRST_LIGHT_STRENGTH 0.35"),
    "texture-probe": ("SunMoon", "TEXTURE_PROBE_STRENGTH 0.25"),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project", choices=sorted(PROJECTS))
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    material_name, define = PROJECTS[args.project]
    project = ROOT / "examples" / args.project
    reference = args.reference_dir.resolve() / f"{material_name}.material.json"
    merge_source = project / "vanilla" / reference.name
    output = args.output.resolve()

    if not reference.is_file():
        raise SystemExit(f"Reference material не найден: {reference}")

    merge_source.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(reference, merge_source)
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "mss.cli",
                "compile",
                str(project),
                "-o",
                str(output),
                "--unsafe-no-baseline",
                "-d",
                define,
            ],
            check=True,
        )
        candidate = output / f"{material_name}.material.bin"
        subprocess.run(
            [sys.executable, "-m", "mss.cli", "material", "inspect", str(candidate)],
            check=True,
        )
    finally:
        merge_source.unlink(missing_ok=True)

    status_file = output / "CI-STATUS.txt"
    status_file.write_text(
        "smoke-build-only\n"
        "This artifact uses public reference material metadata and has not been hardware-verified.\n"
        "Do not install it on Nintendo Switch.\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
