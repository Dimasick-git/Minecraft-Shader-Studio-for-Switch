"""Open NVN/Maxwell toolchain integration for Minecraft Shader Studio.

Author: Dimasick-git
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import hashlib, json, os, shutil, subprocess, tempfile
from .errors import ToolchainError, ValidationError

class ShaderStage(str, Enum):
    VERTEX = "vert"
    TESS_CONTROL = "tess_ctrl"
    TESS_EVALUATION = "tess_eval"
    GEOMETRY = "geom"
    FRAGMENT = "frag"
    COMPUTE = "comp"

@dataclass(frozen=True)
class NvnArtifact:
    source: Path
    stage: ShaderStage
    raw_maxwell: Path
    dksh: Path | None
    compiler: str
    sha256: str
    size: int

@dataclass(frozen=True)
class NvnInspection:
    size: int
    sha256: str
    has_nvn_prefix: bool
    sph_offset: int | None
    aligned_64: bool


def _sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()


def resolve_compiler(explicit: Path | None = None) -> Path:
    """Resolve uam-nvn first, then upstream UAM.

    uam-nvn is the preferred NVN fork. Upstream uam is a supported fallback
    because its -r output is native Maxwell bytecode for Tegra X1.
    """
    if explicit:
        candidate=explicit.expanduser().resolve()
        if not candidate.is_file(): raise ToolchainError(f"NVN compiler not found: {candidate}")
        return candidate
    env=os.environ.get("MSS_UAM")
    candidates=[env] if env else []
    candidates += [shutil.which("uam-nvn"), shutil.which("uam")]
    for value in candidates:
        if value and Path(value).is_file(): return Path(value).resolve()
    raise ToolchainError("uam-nvn/uam not found; set MSS_UAM or pass --compiler")


def compile_glsl(source: Path, stage: ShaderStage, output_dir: Path, *, compiler: Path | None = None, timeout: int = 180) -> NvnArtifact:
    source=source.resolve(); output_dir=output_dir.resolve()
    if not source.is_file(): raise ValidationError(f"GLSL source not found: {source}")
    if source.stat().st_size > 4*1024*1024: raise ValidationError("GLSL source is too large")
    tool=resolve_compiler(compiler); output_dir.mkdir(parents=True,exist_ok=True)
    raw=output_dir/f"{source.stem}.{stage.value}.maxwell.bin"
    dksh=output_dir/f"{source.stem}.{stage.value}.dksh"
    # Both devkitPro/uam and the public uam-nvn fork use the UAM CLI shape.
    args=[str(tool),"-s",stage.value,"-r",str(raw),"-o",str(dksh),str(source)]
    try:
        result=subprocess.run(args,shell=False,capture_output=True,text=True,timeout=timeout,check=False)
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise ToolchainError(f"NVN compiler launch failed: {exc}") from exc
    if result.returncode:
        tail=(result.stderr or result.stdout)[-4000:]
        raise ToolchainError(f"NVN compiler failed ({result.returncode}):\n{tail}")
    if not raw.is_file() or raw.stat().st_size==0: raise ToolchainError("compiler produced no raw Maxwell output")
    size=raw.stat().st_size
    if size%64: raise ToolchainError(f"raw Maxwell output is not 64-byte aligned: {size}")
    return NvnArtifact(source,stage,raw,dksh if dksh.is_file() else None,tool.name,_sha256(raw),size)


def inspect_nvn(path: Path) -> NvnInspection:
    path=path.resolve()
    if not path.is_file(): raise ValidationError(f"shader binary not found: {path}")
    data=path.read_bytes()
    # Common NVN program data has a 0x30-byte NVN-specific prefix before SPH.
    # SPH does not have a universal ASCII magic, so offset is structural here.
    has_prefix=len(data)>=0x70 and len(data[0x30:])>=0x40
    return NvnInspection(len(data),hashlib.sha256(data).hexdigest(),has_prefix,0x30 if has_prefix else None,len(data)%64==0)


def graft_nvn_prefix(template: Path, raw_maxwell: Path, output: Path) -> Path:
    """Create an experimental NVN blob by preserving a user's 0x30-byte prefix.

    This operation is deliberately explicit and never mutates the template.
    It does not claim that every RenderDragon revision accepts the result; the
    generated sidecar records provenance for hardware testing.
    """
    template=template.resolve(); raw_maxwell=raw_maxwell.resolve(); output=output.resolve()
    t=template.read_bytes(); raw=raw_maxwell.read_bytes()
    if len(t)<0x70: raise ValidationError("template is too small to contain NVN prefix + SPH")
    if not raw or len(raw)%64: raise ValidationError("raw Maxwell payload must be non-empty and 64-byte aligned")
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_bytes(t[:0x30]+raw)
    sidecar={"schema":1,"mode":"experimental-prefix-graft","template_sha256":hashlib.sha256(t).hexdigest(),"payload_sha256":hashlib.sha256(raw).hexdigest(),"output_sha256":_sha256(output),"prefix_size":48,"author":"Dimasick-git"}
    output.with_suffix(output.suffix+".json").write_text(json.dumps(sidecar,indent=2)+"\n",encoding="utf-8")
    return output
