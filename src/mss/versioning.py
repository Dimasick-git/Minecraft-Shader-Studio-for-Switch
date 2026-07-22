from __future__ import annotations
import re
from dataclasses import dataclass
from .errors import ValidationError

_VERSION = re.compile(r"^(?:0|[1-9]\d*)(?:\.(?:0|[1-9]\d*)){1,3}$")

@dataclass(frozen=True, order=True)
class Version:
    parts: tuple[int, ...]

    @classmethod
    def parse(cls, value: str) -> "Version":
        if not isinstance(value, str) or not _VERSION.fullmatch(value):
            raise ValidationError(f"Некорректная версия: {value!r}")
        return cls(tuple(int(x) for x in value.split(".")))

    def __str__(self) -> str:
        return ".".join(map(str, self.parts))
