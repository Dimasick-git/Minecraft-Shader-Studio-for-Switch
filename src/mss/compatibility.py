from __future__ import annotations
from pathlib import Path
import json
from .errors import CompatibilityError, ValidationError
from .versioning import Version

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MATRIX = ROOT / "compatibility" / "matrix.json"

def load_matrix(path: Path = DEFAULT_MATRIX) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"Матрица совместимости повреждена: {exc}") from exc
    if data.get("schema") != 1 or not isinstance(data.get("targets"), list):
        raise ValidationError("Некорректная compatibility/matrix.json")
    return data

def assert_supported(minecraft: str, atmosphere: str, *, allow_untested: bool = False, matrix_path: Path = DEFAULT_MATRIX) -> dict:
    mc, atm = Version.parse(minecraft), Version.parse(atmosphere)
    for target in load_matrix(matrix_path)["targets"]:
        if target.get("minecraft") == str(mc):
            minimum = Version.parse(target["atmosphere_min"])
            if atm < minimum:
                raise CompatibilityError(f"Требуется Atmosphère >= {minimum}")
            if target.get("status") != "verified" and not allow_untested:
                raise CompatibilityError("Версия обнаружена, но ещё не подтверждена тестами")
            return target
    if allow_untested:
        return {"minecraft": str(mc), "atmosphere_min": str(atm), "status": "unsafe-override"}
    raise CompatibilityError("Неизвестная версия Minecraft; сборка заблокирована")
