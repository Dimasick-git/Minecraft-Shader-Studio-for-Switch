from __future__ import annotations
from pathlib import Path
import argparse, json, shutil, sys
from . import __version__
from .compatibility import load_matrix
from .packager import build, validate_pack
from .errors import MSSError
from .nvn import ShaderStage, compile_glsl, inspect_nvn, graft_nvn_prefix

def parser() -> argparse.ArgumentParser:
    p=argparse.ArgumentParser(prog="mss",description="Minecraft Shader Studio")
    p.add_argument("--version",action="version",version=__version__)
    sub=p.add_subparsers(dest="command",required=True)
    sub.add_parser("latest",help="Show rolling targets")
    sub.add_parser("doctor",help="Check local toolchain")
    init=sub.add_parser("init",help="Initialize a new shader pack project");init.add_argument("name");init.add_argument("--author",default="Anonymous")
    v=sub.add_parser("validate",help="Validate shader pack");v.add_argument("pack",type=Path)
    up=sub.add_parser("unpack",help="Unpack .material.bin using Lazurite");up.add_argument("input",type=Path);up.add_argument("-o","--output",type=Path,default=Path("unpacked"))
    b=sub.add_parser("build",help="Build LayeredFS pack")
    b.add_argument("pack",type=Path);b.add_argument("--output",type=Path,default=Path("dist"));b.add_argument("--minecraft-version",required=True);b.add_argument("--atmosphere-version",required=True);b.add_argument("--title-id",required=True);b.add_argument("--allow-untested",action="store_true")
    n=sub.add_parser("nvn",help="NVN/Maxwell pipeline");ns=n.add_subparsers(dest="nvn_command",required=True)
    c=ns.add_parser("compile",help="Compile GLSL with uam-nvn/uam");c.add_argument("source",type=Path);c.add_argument("--stage",choices=[x.value for x in ShaderStage],required=True);c.add_argument("--output",type=Path,default=Path("build/nvn"));c.add_argument("--compiler",type=Path)
    i=ns.add_parser("inspect",help="Inspect NVN/Maxwell binary");i.add_argument("binary",type=Path)
    g=ns.add_parser("graft",help="Graft user-owned NVN prefix onto raw Maxwell payload");g.add_argument("--template",type=Path,required=True);g.add_argument("--raw",type=Path,required=True);g.add_argument("--output",type=Path,required=True)
    return p

def main(argv=None)->int:
    args=parser().parse_args(argv)
    try:
        if args.command=="latest": print(json.dumps(load_matrix()["rolling"],ensure_ascii=False,indent=2));return 0
        if args.command=="doctor":
            print(f"Python: {sys.version.split()[0]}")
            print(f"uam-nvn/uam: {shutil.which('uam-nvn') or shutil.which('uam') or 'not found'}")
            print(f"Lazurite: {shutil.which('lazurite') or 'not found'}")
            print(f"Java: {shutil.which('java') or 'not found (required for MaterialBinTool)'}")
            print(f"MaterialBinTool: {shutil.which('MaterialBinTool.jar') or os.environ.get('MATERIAL_BIN_TOOL_JAR') or 'not found (optional)'}")
            print("MSS core: OK");return 0
        if args.command=="init":
            from .packager import init_project
            path = init_project(args.name, args.author)
            print(f"Project initialized in: {path}"); return 0
        if args.command=="validate": m=validate_pack(args.pack);print(f"OK: {m.id} {m.version}, author={m.author}");return 0
        if args.command=="unpack":
            from .external import unpack_material
            unpack_material(args.input, args.output)
            print(f"Unpacked to: {args.output}"); return 0
        if args.command=="build":
            folder,archive=build(args.pack,args.output,args.minecraft_version,args.atmosphere_version,args.title_id,allow_untested=args.allow_untested);print(f"Folder: {folder}\nArchive: {archive}");return 0
        if args.command=="nvn":
            if args.nvn_command=="compile":
                artifact=compile_glsl(args.source,ShaderStage(args.stage),args.output,compiler=args.compiler);print(json.dumps({"raw":str(artifact.raw_maxwell),"dksh":str(artifact.dksh) if artifact.dksh else None,"compiler":artifact.compiler,"sha256":artifact.sha256,"size":artifact.size},indent=2));return 0
            if args.nvn_command=="inspect": print(json.dumps(inspect_nvn(args.binary).__dict__,indent=2));return 0
            if args.nvn_command=="graft": print(graft_nvn_prefix(args.template,args.raw,args.output));return 0
    except MSSError as exc: print(f"ERROR: {exc}",file=sys.stderr);return 2
    except (OSError,ValueError) as exc: print(f"ERROR: {exc}",file=sys.stderr);return 2
    return 1
if __name__=="__main__":raise SystemExit(main())
