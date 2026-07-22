from __future__ import annotations
from pathlib import Path
import subprocess
import shutil
import os
from .errors import ToolchainError

def unpack_material(material_bin: Path, output_dir: Path):
    """Unpack .material.bin using lazurite (Python API)"""
    try:
        import lazurite
        # Lazurite can be used as a library or CLI. 
        # Here we use it to unpack materials.
        # Based on lazurite documentation, we can use its core functions.
        # For simplicity in this integration, we'll use the CLI if available or call its internal logic.
        args = ["lazurite", "unpack", str(material_bin), "-o", str(output_dir)]
        subprocess.run(args, check=True, capture_output=True)
    except ImportError:
        raise ToolchainError("lazurite not installed. Run 'pip install lazurite'")
    except subprocess.CalledProcessError as e:
        raise ToolchainError(f"Lazurite failed to unpack: {e.stderr.decode()}")

def run_material_bin_tool(args: list[str]):
    """Run MaterialBinTool.jar if available"""
    jar_path = os.environ.get("MATERIAL_BIN_TOOL_JAR") or shutil.which("MaterialBinTool.jar")
    if not jar_path:
        # Check common locations
        common = [Path("tools/MaterialBinTool.jar"), Path("/usr/local/bin/MaterialBinTool.jar")]
        for p in common:
            if p.exists():
                jar_path = str(p)
                break
    
    if not jar_path:
        raise ToolchainError("MaterialBinTool.jar not found. Set MATERIAL_BIN_TOOL_JAR environment variable.")
    
    cmd = ["java", "-jar", jar_path] + args
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise ToolchainError(f"MaterialBinTool failed: {e.stderr.decode()}")
