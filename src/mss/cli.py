from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from . import __version__
from .compatibility import load_matrix
from .errors import MSSError
from .nvn import ShaderStage, compile_glsl, graft_nvn_prefix, inspect_nvn
from .packager import build, validate_pack
from .overlay import OverlayManager


def _print_json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _installed_version(package: str) -> str:
    try:
        return version(package)
    except PackageNotFoundError:
        return "not installed"


def _bundled_shaderc() -> str | None:
    """Вернуть shaderc, скачанный штатным fetch_toolchain.py, если он есть."""
    candidate = Path(__file__).resolve().parents[2] / "toolchains" / "bin" / "shadercRelease"
    return str(candidate) if candidate.is_file() else None


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mss", description="Minecraft Shader Studio")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    # Overlay commands
    ov = sub.add_parser("overlay", help="Управление файлами игры (RomFS/LayeredFS)")
    ov_sub = ov.add_subparsers(dest="subcommand", required=True)

    ov_ext = ov_sub.add_parser("extract", help="Извлечь материалы из дампа RomFS")
    ov_ext.add_argument("romfs", type=Path, help="Путь к дампу RomFS")
    ov_ext.add_argument("-o", "--output", type=Path, required=True, help="Куда сохранить материалы")
    ov_ext.add_argument("-p", "--pattern", action="append", help="Фильтр по именам (напр. Sky, SunMoon)")

    ov_app = ov_sub.add_parser("apply", help="Подготовить структуру LayeredFS для SD-карты")
    ov_app.add_argument("source", type=Path, help="Путь к скомпилированным материалам или папке")
    ov_app.add_argument("-o", "--output", type=Path, default=Path("layeredfs_out"), help="Выходная папка для SD")
    ov_app.add_argument("--title-id", default="0100D71004694000", help="Title ID игры")

    sub.add_parser("latest", help="Показать rolling compatibility targets")
    sub.add_parser("doctor", help="Проверить локальный тулчейн")

    init = sub.add_parser("init", help="Инициализировать новый shader pack project")
    init.add_argument("name")
    init.add_argument("--author", default="Anonymous")
    init.add_argument("--preset", choices=["basic", "newb-x", "mcbe-codebase"], default="basic")

    validate = sub.add_parser("validate", help="Проверить manifest shader pack")
    validate.add_argument("pack", type=Path)

    unpack = sub.add_parser("unpack", help="Распаковать .material.bin через Lazurite")
    unpack.add_argument("input", type=Path)
    unpack.add_argument("-o", "--output", type=Path, default=Path("unpacked"))

    material = sub.add_parser("material", help="Инспекция и структурная проверка material.bin")
    material_sub = material.add_subparsers(dest="material_command", required=True)
    inspect = material_sub.add_parser("inspect", help="Показать platform, format, variants и hash material.bin")
    inspect.add_argument("input", type=Path)
    compare = material_sub.add_parser(
        "compare",
        help="Сравнить Switch/Vulkan baseline с собранным material.bin; не заменяет тест на железе",
    )
    compare.add_argument("--baseline", type=Path, required=True, help="Ванильный Switch Vulkan material.bin")
    compare.add_argument("--candidate", type=Path, required=True, help="Собранный material.bin")

    build_parser = sub.add_parser("build", help="Собрать LayeredFS pack")
    build_parser.add_argument("pack", type=Path)
    build_parser.add_argument("--output", type=Path, default=Path("dist"))
    build_parser.add_argument("--minecraft-version", required=True)
    build_parser.add_argument("--atmosphere-version", required=True)
    build_parser.add_argument(
        "--title-id",
        default="0100D71004694000",
        help="Title ID игры (по умолчанию Minecraft Bedrock: 0100D71004694000)",
    )
    build_parser.add_argument("--allow-untested", action="store_true")

    nvn = sub.add_parser("nvn", help="Экспериментальный NVN/Maxwell pipeline")
    nvn_sub = nvn.add_subparsers(dest="nvn_command", required=True)
    nvn_compile = nvn_sub.add_parser("compile", help="Скомпилировать GLSL через uam-nvn/uam")
    nvn_compile.add_argument("source", type=Path)
    nvn_compile.add_argument("--stage", choices=[stage.value for stage in ShaderStage], required=True)
    nvn_compile.add_argument("--output", type=Path, default=Path("build/nvn"))
    nvn_compile.add_argument("--compiler", type=Path)
    nvn_inspect = nvn_sub.add_parser("inspect", help="Инспектировать NVN/Maxwell binary")
    nvn_inspect.add_argument("binary", type=Path)
    nvn_graft = nvn_sub.add_parser("graft", help="Добавить пользовательский NVN prefix к raw Maxwell payload")
    nvn_graft.add_argument("--template", type=Path, required=True)
    nvn_graft.add_argument("--raw", type=Path, required=True)
    nvn_graft.add_argument("--output", type=Path, required=True)

    vulkan = sub.add_parser("vulkan", help="Отдельный Vulkan/SPIR-V pipeline (не material.bin)")
    vulkan_sub = vulkan.add_subparsers(dest="vulkan_command", required=True)
    vulkan_compile = vulkan_sub.add_parser("compile", help="Скомпилировать GLSL в SPIR-V")
    vulkan_compile.add_argument("source", type=Path)
    vulkan_compile.add_argument("--stage", choices=["vert", "frag", "comp"], required=True)
    vulkan_compile.add_argument("--output", type=Path, default=Path("build/vulkan"))

    compile_parser = sub.add_parser(
        "compile",
        help="Скомпилировать Lazurite project в material.bin (Switch/Vulkan по умолчанию)",
    )
    compile_parser.add_argument("project", type=Path)
    compile_parser.add_argument("-o", "--output", type=Path, default=Path("materials"))
    compile_parser.add_argument("--profile", default="switch", help="Профиль из project.json (по умолчанию: switch)")
    compile_parser.add_argument(
        "--shaderc",
        type=Path,
        help="Путь к shaderc из bgfx-mcbe (или MSS_SHADERC)",
    )
    compile_parser.add_argument("--lazurite", type=Path, help="Путь к lazurite (или MSS_LAZURITE)")
    compile_parser.add_argument(
        "--baseline",
        type=Path,
        help="Ванильный Vulkan material.bin из RomFS вашей Switch-версии Minecraft",
    )
    compile_parser.add_argument(
        "--unsafe-no-baseline",
        action="store_true",
        help="Разрешить только smoke-сборку без структурной Switch-проверки; результат не готов к установке",
    )
    compile_parser.add_argument(
        "-d",
        "--define",
        action="append",
        dest="defines",
        help="Дополнительный макрос (можно несколько раз)",
    )
    return parser


def _require_switch_baseline(args: argparse.Namespace) -> None:
    if args.profile != "switch" or args.baseline is not None or args.unsafe_no_baseline:
        return
    raise MSSError(
        "Для профиля switch обязателен --baseline с ванильным Vulkan material.bin "
        "из RomFS той же версии игры. Для CI допускается только явный "
        "--unsafe-no-baseline; такой результат нельзя устанавливать на Switch."
    )


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "latest":
            _print_json(load_matrix()["rolling"])
            return 0
        if args.command == "overlay":
            manager = OverlayManager(title_id=getattr(args, "title_id", "0100D71004694000"))
            if args.subcommand == "extract":
                extracted = manager.extract_materials(args.romfs, args.output, args.pattern)
                print(f"Извлечено {len(extracted)} материалов в {args.output}")
                for f in extracted:
                    print(f"  - {f.name}")
            elif args.subcommand == "apply":
                out = manager.prepare_layeredfs(args.source, args.output)
                print(f"Структура LayeredFS готова в {out}")
                print(f"Скопируйте содержимое {out} в корень SD-карты.")
            return 0
        if args.command == "doctor":
            print(f"Python: {sys.version.split()[0]}")
            print(f"Lazurite package: {_installed_version('lazurite')}")
            print(f"uam-nvn/uam: {shutil.which('uam-nvn') or shutil.which('uam') or 'not found'}")
            print(f"Lazurite CLI: {shutil.which('lazurite') or os.environ.get('MSS_LAZURITE') or 'not found'}")
            print(
                "shaderc (bgfx-mcbe): "
                + (
                    shutil.which("shadercRelease")
                    or shutil.which("shaderc")
                    or os.environ.get("MSS_SHADERC")
                    or _bundled_shaderc()
                    or "not found (см. scripts/fetch_toolchain.py)"
                )
            )
            print(f"Java: {shutil.which('java') or 'not found (только для legacy MaterialBinTool)'}")
            print("MSS hardware status: no automatic verification; use a controlled console test.")
            return 0
        if args.command == "init":
            from .packager import init_project

            path = init_project(args.name, args.author, preset=args.preset)
            print(f"Project initialized in: {path}")
            return 0
        if args.command == "validate":
            manifest = validate_pack(args.pack)
            print(f"OK: {manifest.id} {manifest.version}, author={manifest.author}")
            return 0
        if args.command == "unpack":
            from .external import unpack_material

            unpack_material(args.input, args.output)
            print(f"Unpacked to: {args.output}")
            return 0
        if args.command == "material":
            from .materials import compare_switch_materials, inspect_material

            if args.material_command == "inspect":
                _print_json(inspect_material(args.input).to_dict())
                return 0
            if args.material_command == "compare":
                comparison = compare_switch_materials(args.baseline, args.candidate)
                _print_json(comparison.to_dict())
                return 0 if comparison.compatible else 3
        if args.command == "build":
            folder, archive = build(
                args.pack,
                args.output,
                args.minecraft_version,
                args.atmosphere_version,
                args.title_id,
                allow_untested=args.allow_untested,
            )
            print(f"Folder: {folder}\nArchive: {archive}")
            return 0
        if args.command == "nvn":
            if args.nvn_command == "compile":
                artifact = compile_glsl(args.source, ShaderStage(args.stage), args.output, compiler=args.compiler)
                _print_json(
                    {
                        "raw": str(artifact.raw_maxwell),
                        "dksh": str(artifact.dksh) if artifact.dksh else None,
                        "compiler": artifact.compiler,
                        "sha256": artifact.sha256,
                        "size": artifact.size,
                    }
                )
                return 0
            if args.nvn_command == "inspect":
                _print_json(inspect_nvn(args.binary).__dict__)
                return 0
            if args.nvn_command == "graft":
                print(graft_nvn_prefix(args.template, args.raw, args.output))
                return 0
        if args.command == "vulkan" and args.vulkan_command == "compile":
            from .vulkan import compile_to_spirv

            artifact = compile_to_spirv(args.source, args.stage, args.output)
            _print_json(
                {
                    "spirv": str(artifact.spirv),
                    "compiler": artifact.compiler,
                    "sha256": artifact.sha256,
                    "size": artifact.size,
                }
            )
            return 0
        if args.command == "compile":
            _require_switch_baseline(args)
            from .compile import compile_project

            produced = compile_project(
                args.project,
                args.output,
                profile=args.profile,
                shaderc=args.shaderc,
                lazurite=args.lazurite,
                defines=args.defines,
                baseline=args.baseline,
            )
            for material_path in produced:
                print(material_path)
            status = "built-and-inspected" if args.baseline else "smoke-build-only"
            print(f"OK: {len(produced)} material.bin (профиль: {args.profile}; status: {status})")
            return 0
    except MSSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
