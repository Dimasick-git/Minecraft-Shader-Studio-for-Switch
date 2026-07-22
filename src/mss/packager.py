from __future__ import annotations
from pathlib import Path
import json, shutil, tempfile, zipfile
from datetime import datetime, timezone
from .models import ShaderManifest, validate_title_id
from .compatibility import assert_supported
from .hashing import sha256
from .errors import ValidationError

MAX_FILE_SIZE = 64 * 1024 * 1024
MAX_FILES = 4096

def _safe_files(root: Path):
    files = []
    for p in root.rglob("*"):
        if p.is_symlink(): raise ValidationError(f"Символические ссылки запрещены: {p}")
        if p.is_file():
            if p.stat().st_size > MAX_FILE_SIZE: raise ValidationError(f"Файл слишком большой: {p.name}")
            files.append(p)
    if len(files) > MAX_FILES: raise ValidationError("Слишком много файлов в пакете")
    return files

def validate_pack(pack: Path) -> ShaderManifest:
    pack = pack.resolve()
    if not pack.is_dir(): raise ValidationError("Папка пакета не существует")
    manifest = ShaderManifest.load(pack)
    materials = pack / "materials"
    if not materials.is_dir(): raise ValidationError("Отсутствует папка materials")
    bins = list(materials.glob("*.material.bin"))
    if not bins: raise ValidationError("Нет файлов *.material.bin")
    _safe_files(pack)
    return manifest

def build(pack: Path, output: Path, minecraft: str, atmosphere: str, title_id: str, *, allow_untested: bool = False) -> tuple[Path, Path]:
    pack, output = pack.resolve(), output.resolve()
    manifest = validate_pack(pack)
    title_id = validate_title_id(title_id)
    target = assert_supported(minecraft, atmosphere, allow_untested=allow_untested)
    release_name = f"mss-{manifest.id}-{manifest.version}"
    output.mkdir(parents=True, exist_ok=True)
    final_dir, final_zip = output / release_name, output / f"{release_name}.zip"
    with tempfile.TemporaryDirectory(prefix="mss-") as td:
        stage = Path(td) / release_name
        romfs = stage / "atmosphere" / "contents" / title_id / "romfs"
        destination = romfs / manifest.materials_destination
        destination.mkdir(parents=True)
        for source in sorted((pack / "materials").glob("*.material.bin")):
            shutil.copy2(source, destination / source.name)
        extra = pack / "romfs"
        if extra.is_dir(): shutil.copytree(extra, romfs, dirs_exist_ok=True)
        records = []
        for p in sorted(_safe_files(stage)):
            records.append({"path": p.relative_to(stage).as_posix(), "size": p.stat().st_size, "sha256": sha256(p)})
        meta = {
            "schema": 1, "generator": "Minecraft Shader Studio 0.1.0",
            "author": "Dimasick-git", "pack": manifest.id, "pack_version": str(manifest.version),
            "minecraft": minecraft, "atmosphere": atmosphere, "compatibility_status": target["status"],
            "built_at": datetime.now(timezone.utc).isoformat(), "files": records,
        }
        (stage / "MSS-MANIFEST.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if final_dir.exists(): shutil.rmtree(final_dir)
        shutil.copytree(stage, final_dir)
        tmp_zip = Path(td) / final_zip.name
        with zipfile.ZipFile(tmp_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for p in sorted(_safe_files(stage)):
                zf.write(p, p.relative_to(stage).as_posix())
        shutil.copy2(tmp_zip, final_zip)
    return final_dir, final_zip

def init_project(name: str, author: str, preset: str = "basic") -> Path:
    root = Path(name).resolve()
    if root.exists():
        raise ValidationError(f"Директория {name} уже существует")
    
    root.mkdir(parents=True)
    (root / "materials").mkdir()
    (root / "romfs").mkdir()
    
    shader_json = {
        "schema": 1,
        "id": name.lower().replace(" ", "-"),
        "name": name,
        "version": "0.1.0",
        "author": author,
        "description": f"New Minecraft RenderDragon shader pack based on {preset} preset",
        "materials_destination": "data/renderer/materials"
    }
    (root / "shader.json").write_text(json.dumps(shader_json, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    
    # Add a basic template README
    (root / "materials" / "README.md").write_text("# Materials\nPlace your `.material.bin` files here.\n", encoding="utf-8")
    
    glsl_dir = root / "src"
    glsl_dir.mkdir()
    
    if preset == "newb-x":
        (glsl_dir / "newb_x_base.vert").write_text("// Preset: Newb X Legacy Base\n// Based on https://github.com/devendrn/newb-x-mcbe\n#version 450\n\nlayout(location = 0) in vec3 position;\nlayout(location = 1) in vec2 uv;\n\nvoid main() {\n    // Newb X specific logic would go here\n    gl_Position = vec4(position, 1.0);\n}\n", encoding="utf-8")
        (glsl_dir / "newb_x_base.frag").write_text("// Preset: Newb X Legacy Base\n#version 450\n\nlayout(location = 0) out vec4 fragColor;\n\nvoid main() {\n    // Newb X lighting calculations\n    fragColor = vec4(0.5, 0.7, 1.0, 1.0); // Sky-ish blue\n}\n", encoding="utf-8")
    elif preset == "mcbe-codebase":
        (glsl_dir / "vanilla.vert").write_text("// Preset: MCBE Shader Codebase (Vanilla Restored)\n// Based on https://github.com/veka0/mcbe-shader-codebase\n#version 450\n\nvoid main() {\n    // Restored vanilla logic\n    gl_Position = vec4(0.0);\n}\n", encoding="utf-8")
    else:
        (glsl_dir / "example.vert").write_text("// Basic RenderDragon Vertex Shader Template\n#version 450\n\nlayout(location = 0) in vec3 position;\n\nvoid main() {\n    gl_Position = vec4(position, 1.0);\n}\n", encoding="utf-8")
        (glsl_dir / "example.frag").write_text("// Basic RenderDragon Fragment Shader Template\n#version 450\n\nlayout(location = 0) out vec4 fragColor;\n\nvoid main() {\n    fragColor = vec4(1.0, 1.0, 1.0, 1.0);\n}\n", encoding="utf-8")
    
    return root
