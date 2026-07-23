"""Интеграция lazurite build: компиляция шейдер-проектов в material.bin.

Основной путь для Nintendo Switch: платформа Vulkan (SPIR-V) — именно такие
шейдеры загружает Switch-версия Minecraft (см. docs/RESEARCH-2026-07.md).

Инструменты ищутся в порядке: явный аргумент → переменная окружения → PATH.
- lazurite:  MSS_LAZURITE  (pip install lazurite)
- shaderc:   MSS_SHADERC   (сборка bgfx-mcbe: shadercRelease)
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from .errors import ToolchainError

DEFAULT_PROFILE = "switch"
SWITCH_PLATFORM = "Vulkan"


def find_tool(explicit: Path | str | None, env_var: str, names: list[str]) -> str:
    """Найти исполняемый файл инструмента: аргумент → env → PATH."""
    if explicit:
        p = Path(explicit)
        if not p.is_file():
            raise ToolchainError(f"Инструмент не найден по указанному пути: {p}")
        return str(p)
    env_value = os.environ.get(env_var)
    if env_value:
        p = Path(env_value)
        if not p.is_file():
            raise ToolchainError(f"{env_var} указывает на несуществующий файл: {p}")
        return str(p)
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    raise ToolchainError(
        f"Не найден инструмент {names[0]!r}. Установите его, задайте {env_var} "
        f"или передайте путь аргументом (см. scripts/fetch_toolchain.py)."
    )


def compile_project(
    project: Path | str,
    output: Path | str,
    *,
    profile: str = DEFAULT_PROFILE,
    shaderc: Path | str | None = None,
    lazurite: Path | str | None = None,
    defines: list[str] | None = None,
    timeout: int = 900,
) -> list[Path]:
    """Скомпилировать lazurite-проект в набор .material.bin.

    Возвращает отсортированный список собранных файлов.
    Профиль по умолчанию — "switch" (платформа Vulkan из project.json).
    """
    project = Path(project).resolve()
    output = Path(output).resolve()
    if not (project / "project.json").is_file():
        raise ToolchainError(f"Не похоже на lazurite-проект (нет project.json): {project}")

    lazurite_exe = find_tool(lazurite, "MSS_LAZURITE", ["lazurite"])
    shaderc_exe = find_tool(shaderc, "MSS_SHADERC", ["shadercRelease", "shaderc"])

    # lazurite не создаёт выходную директорию самостоятельно
    output.mkdir(parents=True, exist_ok=True)

    cmd = [
        lazurite_exe, "build", str(project),
        "-o", str(output),
        "--shaderc", shaderc_exe,
        "-p", profile,
    ]
    for define in defines or []:
        cmd += ["-d", define]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise ToolchainError(f"lazurite build превысил таймаут {timeout}s") from exc
    except OSError as exc:
        raise ToolchainError(f"Не удалось запустить lazurite: {exc}") from exc

    if proc.returncode != 0:
        log = (proc.stdout + "\n" + proc.stderr).strip().splitlines()
        tail = "\n".join(log[-15:])
        raise ToolchainError(f"lazurite build завершился с кодом {proc.returncode}:\n{tail}")

    produced = sorted(output.glob("*.material.bin"))
    if not produced:
        raise ToolchainError(
            "lazurite build не создал ни одного .material.bin — проверьте "
            "merge_source и include_patterns в project.json"
        )
    return produced
