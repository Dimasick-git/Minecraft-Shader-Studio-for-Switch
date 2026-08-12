from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .compatibility import assert_supported
from .errors import ValidationError
from .hashing import sha256
from .models import ShaderManifest, validate_title_id

MAX_FILE_SIZE = 64 * 1024 * 1024
MAX_FILES = 4096


def _safe_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValidationError(f"Символические ссылки запрещены: {path}")
        if path.is_file():
            if path.stat().st_size > MAX_FILE_SIZE:
                raise ValidationError(f"Файл слишком большой: {path.name}")
            files.append(path)
    if len(files) > MAX_FILES:
        raise ValidationError("Слишком много файлов в пакете")
    return files


def validate_pack(pack: Path) -> ShaderManifest:
    pack = pack.expanduser().resolve()
    if not pack.is_dir():
        raise ValidationError("Папка пакета не существует")
    manifest = ShaderManifest.load(pack)
    materials = pack / "materials"
    if not materials.is_dir():
        raise ValidationError("Отсутствует папка materials")
    if not list(materials.glob("*.material.bin")):
        raise ValidationError("Нет файлов *.material.bin")
    _safe_files(pack)
    return manifest


def build(
    pack: Path,
    output: Path,
    minecraft: str,
    atmosphere: str,
    title_id: str,
    *,
    allow_untested: bool = False,
) -> tuple[Path, Path]:
    """Собрать проверяемую папку и ZIP-архив LayeredFS-пака."""
    pack, output = pack.expanduser().resolve(), output.expanduser().resolve()
    manifest = validate_pack(pack)
    title_id = validate_title_id(title_id)
    target = assert_supported(minecraft, atmosphere, allow_untested=allow_untested)
    release_name = f"mss-{manifest.id}-{manifest.version}"
    output.mkdir(parents=True, exist_ok=True)
    final_dir, final_zip = output / release_name, output / f"{release_name}.zip"

    with tempfile.TemporaryDirectory(prefix="mss-") as temporary_directory:
        stage = Path(temporary_directory) / release_name
        romfs = stage / "atmosphere" / "contents" / title_id / "romfs"
        destination = romfs / manifest.materials_destination
        destination.mkdir(parents=True)
        for source in sorted((pack / "materials").glob("*.material.bin")):
            shutil.copy2(source, destination / source.name)
        extra = pack / "romfs"
        if extra.is_dir():
            shutil.copytree(extra, romfs, dirs_exist_ok=True)

        records = [
            {
                "path": path.relative_to(stage).as_posix(),
                "size": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in sorted(_safe_files(stage))
        ]
        metadata = {
            "schema": 1,
            "generator": f"Minecraft Shader Studio {__version__}",
            "author": manifest.author,
            "pack": manifest.id,
            "pack_version": str(manifest.version),
            "minecraft": minecraft,
            "atmosphere": atmosphere,
            "compatibility_status": target["status"],
            "built_at": datetime.now(timezone.utc).isoformat(),
            "files": records,
        }
        (stage / "MSS-MANIFEST.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if final_dir.exists():
            shutil.rmtree(final_dir)
        shutil.copytree(stage, final_dir)
        temporary_zip = Path(temporary_directory) / final_zip.name
        with zipfile.ZipFile(
            temporary_zip,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for path in sorted(_safe_files(stage)):
                archive.write(path, path.relative_to(stage).as_posix())
        shutil.copy2(temporary_zip, final_zip)
    return final_dir, final_zip
