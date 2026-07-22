from __future__ import annotations
from pathlib import Path
import subprocess
from .errors import ToolchainError

class MaterialCompiler:
    """Safe adapter. It never invokes a shell and never downloads tools."""
    def __init__(self, executable: Path):
        self.executable = executable

    def compile(self, source: Path, output: Path, timeout: int = 180) -> None:
        if not self.executable.is_file():
            raise ToolchainError(f"Компилятор не найден: {self.executable}")
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            result = subprocess.run(
                [str(self.executable), "-c", str(source), "-o", str(output)],
                shell=False, capture_output=True, text=True, timeout=timeout, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ToolchainError(f"Ошибка запуска toolchain: {exc}") from exc
        if result.returncode:
            tail = (result.stderr or result.stdout)[-2000:]
            raise ToolchainError(f"Toolchain завершился с кодом {result.returncode}:\n{tail}")
