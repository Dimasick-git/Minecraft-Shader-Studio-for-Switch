from __future__ import annotations
import shutil
from pathlib import Path
from .errors import ValidationError
from .models import validate_title_id

class OverlayManager:
    """Модуль автоматизации извлечения и подмены файлов (LayeredFS)."""
    
    def __init__(self, title_id: str = "0100D71004694000"):
        self.title_id = validate_title_id(title_id)
        
    def extract_materials(self, romfs_dump: Path, destination: Path, patterns: list[str] | None = None) -> list[Path]:
        """Извлечь ванильные материалы из дампа RomFS в указанную папку."""
        romfs_dump = Path(romfs_dump).resolve()
        destination = Path(destination).resolve()
        
        if not romfs_dump.exists():
            raise ValidationError(f"Дамп RomFS не найден: {romfs_dump}")
        
        # Стандартный путь материалов в Minecraft Bedrock
        materials_path = romfs_dump / "renderer" / "materials"
        if not materials_path.is_dir():
            # Попробуем найти рекурсивно, если дамп не полный
            found_paths = list(romfs_dump.rglob("renderer/materials"))
            if not found_paths:
                raise ValidationError(f"Папка renderer/materials не найдена в {romfs_dump}")
            materials_path = found_paths[0]
            
        destination.mkdir(parents=True, exist_ok=True)
        
        extracted = []
        glob_pattern = "*.material.bin"
        
        for file in materials_path.glob(glob_pattern):
            if patterns:
                if not any(p.lower() in file.name.lower() for p in patterns):
                    continue
            
            dest_file = destination / file.name
            shutil.copy2(file, dest_file)
            extracted.append(dest_file)
            
        return extracted

    def prepare_layeredfs(self, source_materials: Path, output_dir: Path, materials_dest: str = "renderer/materials") -> Path:
        """Подготовить структуру LayeredFS для SD-карты."""
        source_materials = Path(source_materials).resolve()
        output_dir = Path(output_dir).resolve()
        
        # atmosphere/contents/<title_id>/romfs/<materials_dest>
        layered_path = output_dir / "atmosphere" / "contents" / self.title_id / "romfs" / materials_dest
        layered_path.mkdir(parents=True, exist_ok=True)
        
        if source_materials.is_file():
            shutil.copy2(source_materials, layered_path / source_materials.name)
        elif source_materials.is_dir():
            for file in source_materials.glob("*.material.bin"):
                shutil.copy2(file, layered_path / file.name)
        else:
            raise ValidationError(f"Источник материалов не найден: {source_materials}")
            
        return output_dir
