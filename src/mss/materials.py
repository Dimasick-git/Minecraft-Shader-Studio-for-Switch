"""Инспекция и проверка `.material.bin` для Switch/Vulkan.

Этот модуль намеренно различает два состояния:

* ``built-and-inspected`` — material.bin структурно собран и сохраняет Vulkan,
  формат и базовые метаданные ванильного материала;
* ``hardware-verified`` — пользователь отдельно подтвердил результат на своей
  консоли. Автоматически присваивать это состояние нельзя.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from .errors import ToolchainError

SWITCH_PLATFORM = "Vulkan"


@dataclass(frozen=True)
class MaterialReport:
    """Стабильная, сериализуемая сводка material.bin."""

    path: str
    sha256: str
    size: int
    name: str
    format_version: int
    platforms: tuple[str, ...]
    stages: tuple[str, ...]
    passes: tuple[str, ...]
    shader_count: int
    variant_count: int
    texture_buffer_count: int
    lazurite_version: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SwitchComparison:
    """Результат структурного сравнения baseline и собранного материала."""

    baseline: MaterialReport
    candidate: MaterialReport
    checks: dict[str, bool]
    compatible: bool
    status: str = "built-and-inspected"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "compatible": self.compatible,
            "checks": self.checks,
            "baseline": self.baseline.to_dict(),
            "candidate": self.candidate.to_dict(),
            "hardware_verified": False,
        }


@dataclass(frozen=True)
class StagedBaseline:
    """Временная копия baseline, необходимая Lazurite merge_source."""

    report: MaterialReport
    target: Path
    created: bool


def _lazurite_version() -> str:
    try:
        return version("lazurite")
    except PackageNotFoundError:
        return "unknown"


def _require_material(path: Path | str) -> Path:
    material = Path(path).expanduser().resolve()
    if not material.is_file():
        raise ToolchainError(f"Material не найден: {material}")
    if material.stat().st_size == 0:
        raise ToolchainError(f"Material пуст: {material}")
    return material


def _platform_name(platform: Any) -> str:
    return str(getattr(platform, "name", platform))


def _count_shaders(material: Any) -> tuple[int, int]:
    shader_count = 0
    variant_count = 0
    for shader_pass in material.passes:
        for variant in shader_pass.variants:
            variant_count += 1
            shader_count += len(variant.shaders)
    return shader_count, variant_count


def _count_texture_buffers(material: Any) -> int:
    count = 0
    for buffer in material.buffers:
        buffer_type = _platform_name(getattr(buffer, "type", "")).lower()
        if "texture" in buffer_type:
            count += 1
    return count


def summarize_material(material: Any, path: Path | str) -> MaterialReport:
    """Построить отчёт из объекта ``lazurite.material.Material``.

    Функция отделена от загрузки, поэтому её можно тестировать на простых
    фиктивных объектах без зависимости от проприетарных игровых файлов.
    """
    source = _require_material(path)
    shader_count, variant_count = _count_shaders(material)
    platforms = tuple(sorted(_platform_name(p) for p in material.get_platforms()))
    stages = tuple(sorted(_platform_name(s) for s in material.get_stages()))
    passes = tuple(sorted(str(shader_pass.name) for shader_pass in material.passes))
    return MaterialReport(
        path=str(source),
        sha256=sha256(source.read_bytes()).hexdigest(),
        size=source.stat().st_size,
        name=str(material.name),
        format_version=int(material.version),
        platforms=platforms,
        stages=stages,
        passes=passes,
        shader_count=shader_count,
        variant_count=variant_count,
        texture_buffer_count=_count_texture_buffers(material),
        lazurite_version=_lazurite_version(),
    )


def inspect_material(path: Path | str) -> MaterialReport:
    """Загрузить material.bin через публичный Python API Lazurite."""
    source = _require_material(path)
    try:
        from lazurite.material.material import Material
    except ImportError as exc:
        raise ToolchainError(
            "Lazurite не установлен. Установите зависимости проекта перед "
            "инспекцией material.bin."
        ) from exc
    try:
        material = Material.load_bin_file(str(source))
    except Exception as exc:  # Lazurite exposes several parser exceptions.
        raise ToolchainError(f"Lazurite не смог прочитать {source.name}: {exc}") from exc
    return summarize_material(material, source)


def require_switch_baseline(path: Path | str) -> MaterialReport:
    """Проверить, что baseline действительно содержит Vulkan-варианты Switch."""
    report = inspect_material(path)
    if SWITCH_PLATFORM not in report.platforms:
        rendered = ", ".join(report.platforms) or "нет"
        raise ToolchainError(
            f"{Path(report.path).name} не является Switch/Vulkan baseline: "
            f"найдены платформы: {rendered}. Используйте material.bin из RomFS "
            "вашей Switch-версии Minecraft."
        )
    if report.shader_count == 0 or report.variant_count == 0:
        raise ToolchainError(
            f"{Path(report.path).name} не содержит шейдерных вариантов и не пригоден "
            "как merge baseline."
        )
    return report


def compare_switch_materials(
    baseline: Path | str | MaterialReport,
    candidate: Path | str | MaterialReport,
) -> SwitchComparison:
    """Сравнить invariants, которые обязаны сохраниться для Switch-материала.

    Проверка не анализирует картинку и не заменяет тест на консоли. Она ловит
    типовые ложноположительные сборки: потерю Vulkan, смену формата, имени,
    стадий или всех вариантов шейдера.
    """
    base = baseline if isinstance(baseline, MaterialReport) else require_switch_baseline(baseline)
    built = candidate if isinstance(candidate, MaterialReport) else inspect_material(candidate)
    checks = {
        "baseline_has_vulkan": SWITCH_PLATFORM in base.platforms,
        "candidate_has_vulkan": SWITCH_PLATFORM in built.platforms,
        "same_material_name": base.name == built.name,
        "same_format_version": base.format_version == built.format_version,
        "stages_preserved": set(base.stages).issubset(built.stages),
        "passes_preserved": set(base.passes).issubset(built.passes),
        "shader_count_preserved": built.shader_count >= base.shader_count > 0,
        "variant_count_preserved": built.variant_count >= base.variant_count > 0,
        "texture_buffers_preserved": built.texture_buffer_count >= base.texture_buffer_count,
    }
    return SwitchComparison(
        baseline=base,
        candidate=built,
        checks=checks,
        compatible=all(checks.values()),
    )


def assert_switch_comparison(
    baseline: Path | str | MaterialReport,
    candidate: Path | str | MaterialReport,
) -> SwitchComparison:
    """Сравнить material.bin и завершить сборку понятной ошибкой при нарушении invariant."""
    comparison = compare_switch_materials(baseline, candidate)
    if not comparison.compatible:
        failed = ", ".join(key for key, passed in comparison.checks.items() if not passed)
        raise ToolchainError(
            "Собранный material.bin не прошёл Switch/Vulkan-проверку: " + failed
        )
    return comparison


def material_filename(name: str) -> str:
    """Вернуть безопасное стандартное имя material.bin для Lazurite material name."""
    if not isinstance(name, str) or not name or name in {".", ".."}:
        raise ToolchainError("Некорректное имя материала в baseline")
    if "/" in name or "\\" in name or Path(name).name != name:
        raise ToolchainError(f"Небезопасное имя материала в baseline: {name!r}")
    return f"{name}.material.bin"


def stage_baseline(project: Path | str, baseline: Path | str) -> StagedBaseline:
    """Поместить пользовательский baseline в локальный, игнорируемый каталог проекта.

    Lazurite читает ``merge_source`` из ``project.json``. Все поставляемые MSS
    examples используют ``vanilla/`` как merge source; поэтому перед сборкой
    внешний baseline копируется туда. Файлы дампа никогда не должны попадать в
    Git и исключены `.gitignore`.
    """
    import shutil

    project_dir = Path(project).expanduser().resolve()
    report = require_switch_baseline(baseline)
    target_dir = project_dir / "vanilla"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / material_filename(report.name)
    source = Path(report.path)
    if source == target:
        return StagedBaseline(report=report, target=target, created=False)
    if target.exists():
        if sha256(target.read_bytes()).hexdigest() != report.sha256:
            raise ToolchainError(
                f"Временный baseline уже существует и отличается: {target}. "
                "Удалите его вручную или используйте совпадающий материал."
            )
        return StagedBaseline(report=report, target=target, created=False)
    shutil.copy2(source, target)
    return StagedBaseline(report=report, target=target, created=True)


def remove_staged_baseline(staged: StagedBaseline | None) -> None:
    """Удалить только временную копию, созданную текущей сборкой."""
    if staged is not None and staged.created:
        staged.target.unlink(missing_ok=True)
