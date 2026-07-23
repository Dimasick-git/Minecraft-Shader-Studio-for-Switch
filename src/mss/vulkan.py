from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib, json, os, shutil, subprocess
from .errors import ToolchainError, ValidationError

@dataclass(frozen=True)
class SpirvArtifact:
    source: Path
    stage: str
    spirv: Path
    compiler: str
    sha256: str
    size: int

def resolve_vulkan_compiler() -> Path:
    """Resolve glslangValidator or spirv-as"""
    candidates = [shutil.which("glslangValidator"), shutil.which("glslang")]
    for value in candidates:
        if value and Path(value).is_file(): return Path(value).resolve()
    raise ToolchainError("glslangValidator not found. Please install Vulkan SDK.")

def compile_to_spirv(source: Path, stage: str, output_dir: Path) -> SpirvArtifact:
    """Compile GLSL to SPIR-V bytecode"""
    source = source.resolve(); output_dir.mkdir(parents=True, exist_ok=True)
    tool = resolve_vulkan_compiler()
    spirv = output_dir / f"{source.stem}.{stage}.spv"
    
    args = [str(tool), "-V", "-S", stage, "-o", str(spirv), str(source)]
    try:
        result = subprocess.run(args, capture_output=True, text=True, check=False)
    except Exception as e:
        raise ToolchainError(f"Vulkan compiler failed: {e}")
        
    if result.returncode != 0:
        raise ToolchainError(f"glslangValidator failed: {result.stderr}")
        
    data = spirv.read_bytes()
    return SpirvArtifact(source, stage, spirv, tool.name, hashlib.sha256(data).hexdigest(), len(data))
