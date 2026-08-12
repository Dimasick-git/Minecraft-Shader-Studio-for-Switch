from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json, re
from .errors import ValidationError
from .versioning import Version

_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")
_TITLE_ID = re.compile(r"^[0-9A-Fa-f]{16}$")

@dataclass(frozen=True)
class ShaderManifest:
    schema: int
    id: str
    name: str
    version: Version
    author: str
    description: str
    materials_destination: str

    @classmethod
    def load(cls, pack: Path) -> "ShaderManifest":
        path = pack / "shader.json"
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ValidationError("Отсутствует shader.json") from exc
        except json.JSONDecodeError as exc:
            raise ValidationError(f"shader.json: {exc.msg}") from exc
        if not isinstance(raw, dict):
            raise ValidationError("shader.json должен содержать JSON-объект")
        required = {"schema", "id", "name", "version", "author", "description", "materials_destination"}
        missing = sorted(required - raw.keys())
        unknown = sorted(raw.keys() - required)
        if missing: raise ValidationError("Отсутствуют поля: " + ", ".join(missing))
        if unknown: raise ValidationError("Неизвестные поля: " + ", ".join(unknown))
        if raw["schema"] != 1: raise ValidationError("Поддерживается только schema=1")
        if not _ID.fullmatch(raw["id"]): raise ValidationError("id должен быть kebab-case")
        for key in ("name", "author", "description"):
            if not isinstance(raw[key], str) or not raw[key].strip():
                raise ValidationError(f"Поле {key} не может быть пустым")
        dest = raw["materials_destination"]
        destination = Path(dest) if isinstance(dest, str) else None
        if (
            not isinstance(dest, str)
            or not dest
            or destination.is_absolute()
            or ".." in destination.parts
            or any(part in {"", "."} for part in destination.parts)
            or "\\" in dest
        ):
            raise ValidationError("materials_destination должен быть непустым безопасным относительным POSIX-путём")
        return cls(1, raw["id"], raw["name"].strip(), Version.parse(raw["version"]), raw["author"].strip(), raw["description"].strip(), dest)


def validate_title_id(value: str) -> str:
    if not _TITLE_ID.fullmatch(value):
        raise ValidationError("Title ID должен состоять из 16 hex-символов")
    return value.upper()
