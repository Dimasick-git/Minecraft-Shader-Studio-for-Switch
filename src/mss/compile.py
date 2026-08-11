"""Интеграция Lazurite build: компиляция шейдер-проектов в material.bin.

Основной путь для Nintendo Switch — платформа Vulkan (SPIR-V). Успешная
компиляция сама по себе не является доказательством запуска на консоли: при
передаче ``baseline`` MSS дополнительно проверяет сохранение platform tag,
формата и базовых шейдерных метаданных ванильного Switch-материала.

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
        path = Path(explicit)
        if not path.is_file():
            raise ToolchainError(f"Инструмент не найден по указанному пути: {path}")
        return str(path)
    env_value = os.environ.get(env_var)
    if env_value:
        path = Path(env_value)
        if not path.is_file():
            raise ToolchainError(f"{env_var} указывает на несуществующий файл: {path}")
        return str(path)
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    raise ToolchainError(
        f"Не найден инструмент {names[0]!r}. Установите его, задайте {env_var} "
        "или передайте путь аргументом (см. scripts/fetch_toolchain.py)."
    )


def _material_name_from_output(path: Path) -> str:
    suffix = ".material.bin"
    return path.name[: -len(suffix)] if path.name.endswith(suffix) else path.stem


def compile_project(
    project: Path | str,
    output: Path | str,
    *,
    profile: str = DEFAULT_PROFILE,
    shaderc: Path | str | None = None,
    lazurite: Path | str | None = None,
    defines: list[str] | None = None,
    baseline: Path | str | None = None,
    timeout: int = 900,
) -> list[Path]:
    """Скомпилировать Lazurite-проект в набор `.material.bin`.

    По умолчанию используется профиль ``switch``. Если задан ``baseline``,
    он должен быть пользовательским Vulkan material.bin от той же версии
    Minecraft. MSS безопасно копирует его в игнорируемый ``vanilla/`` каталога
    проекта, запускает Lazurite, а затем проверяет парный результат. Проверка
    структурная; подтверждение на реальном Switch остаётся отдельным шагом.
    """
    project_dir = Path(project).resolve()
    output_dir = Path(output).resolve()
    if not (project_dir / "project.json").is_file():
        raise ToolchainError(f"Не похоже на Lazurite-проект (нет project.json): {project_dir}")

    baseline_report = None
    if baseline is not None:
        from .materials import stage_baseline

        baseline_report = stage_baseline(project_dir, baseline)

    lazurite_exe = find_tool(lazurite, "MSS_LAZURITE", ["lazurite"])
    shaderc_exe = find_tool(shaderc, "MSS_SHADERC", ["shadercRelease", "shaderc"])

    # Lazurite не создаёт выходную директорию самостоятельно.
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        lazurite_exe,
        "build",
        str(project_dir),
        "-o",
        str(output_dir),
        "--shaderc",
        shaderc_exe,
        "-p",
        profile,
    ]
    for define in defines or []:
        command += ["-d", define]

    try:
        process = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise ToolchainError(f"lazurite build превысил таймаут {timeout}s") from exc
    except OSError as exc:
        raise ToolchainError(f"Не удалось запустить lazurite: {exc}") from exc

    if process.returncode != 0:
        log = (process.stdout + "\n" + process.stderr).strip().splitlines()
        tail = "\n".join(log[-15:])
        raise ToolchainError(f"lazurite build завершился с кодом {process.returncode}:\n{tail}")

    produced = sorted(output_dir.glob("*.material.bin"))
    if not produced:
        raise ToolchainError(
            "lazurite build не создал ни одного .material.bin — проверьте "
            "merge_source и include_patterns в project.json"
        )

    if baseline_report is not None:
        from .materials import assert_switch_comparison

        matching = [
            material for material in produced
            if _material_name_from_output(material) == baseline_report.name
        ]
        if not matching:
            raise ToolchainError(
                "Lazurite завершился успешно, но не создал материал, соответствующий "
                f"baseline {baseline_report.name!r}. Собраны: "
                + ", ".join(material.name for material in produced)
            )
        for material in matching:
            assert_switch_comparison(baseline_report, material)

    return produced
