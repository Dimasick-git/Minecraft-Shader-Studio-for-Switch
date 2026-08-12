from __future__ import annotations

import shutil
from pathlib import Path

from .errors import ValidationError
from .models import validate_title_id

MATERIAL_SUFFIX = ".material.bin"


class OverlayManager:
    """Извлечение локальных baseline и подготовка дерева LayeredFS."""

    def __init__(self, title_id: str = "0100D71004694000"):
        self.title_id = validate_title_id(title_id)

    @staticmethod
    def _material_files(directory: Path) -> list[Path]:
        return sorted(
            path for path in directory.glob(f"*{MATERIAL_SUFFIX}") if path.is_file()
        )

    def extract_materials(
        self,
        romfs_dump: Path,
        destination: Path,
        patterns: list[str] | None = None,
    ) -> list[Path]:
        """Скопировать `*.material.bin` из локального RomFS-дампа.

        Поиск fallback-пути детерминированный. Нулевой результат считается ошибкой,
        чтобы CLI не сообщал об успешном создании baseline без материалов.
        """
        romfs_dump = Path(romfs_dump).expanduser().resolve()
        destination = Path(destination).expanduser().resolve()
        if not romfs_dump.is_dir():
            raise ValidationError(f"Дамп RomFS не найден или не является папкой: {romfs_dump}")

        materials_path = romfs_dump / "renderer" / "materials"
        if not materials_path.is_dir():
            candidates = sorted(path for path in romfs_dump.rglob("materials") if path.parent.name == "renderer")
            if not candidates:
                raise ValidationError(f"Папка renderer/materials не найдена в {romfs_dump}")
            materials_path = candidates[0]

        requested = [item.lower() for item in (patterns or []) if item and item.strip()]
        files = self._material_files(materials_path)
        if requested:
            files = [path for path in files if any(pattern in path.name.lower() for pattern in requested)]
        if not files:
            suffix = f" по фильтру {requested}" if requested else ""
            raise ValidationError(f"В {materials_path} не найдено материалов{suffix}")

        destination.mkdir(parents=True, exist_ok=True)
        extracted: list[Path] = []
        for source in files:
            target = destination / source.name
            if source.resolve() != target.resolve():
                shutil.copy2(source, target)
            extracted.append(target)
        return extracted

    def prepare_layeredfs(
        self,
        source_materials: Path,
        output_dir: Path,
        materials_dest: str = "renderer/materials",
    ) -> Path:
        """Создать чистое LayeredFS-дерево с одним или несколькими material.bin."""
        source_materials = Path(source_materials).expanduser().resolve()
        output_dir = Path(output_dir).expanduser().resolve()
        destination_parts = Path(materials_dest)
        if (
            not materials_dest
            or destination_parts.is_absolute()
            or ".." in destination_parts.parts
            or "\\" in materials_dest
        ):
            raise ValidationError("materials_dest должен быть безопасным относительным POSIX-путём")

        if source_materials.is_file():
            if not source_materials.name.endswith(MATERIAL_SUFFIX):
                raise ValidationError("Источник должен быть файлом *.material.bin или папкой с такими файлами")
            files = [source_materials]
        elif source_materials.is_dir():
            files = self._material_files(source_materials)
            if not files:
                raise ValidationError(f"В папке источника нет файлов *{MATERIAL_SUFFIX}: {source_materials}")
        else:
            raise ValidationError(f"Источник материалов не найден: {source_materials}")

        layered_path = (
            output_dir
            / "atmosphere"
            / "contents"
            / self.title_id
            / "romfs"
            / destination_parts
        )
        if source_materials.is_dir() and source_materials == layered_path:
            raise ValidationError("Источник не может совпадать с папкой назначения LayeredFS")
        layered_path.mkdir(parents=True, exist_ok=True)

        for stale in self._material_files(layered_path):
            stale.unlink()
        for source in files:
            shutil.copy2(source, layered_path / source.name)
        return output_dir
