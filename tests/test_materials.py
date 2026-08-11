import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mss.cli import main
from mss.compile import compile_project
from mss.errors import ToolchainError
from mss.materials import MaterialReport, compare_switch_materials, summarize_material


class _Named:
    def __init__(self, name):
        self.name = name


class _Variant:
    def __init__(self, shader_count):
        self.shaders = [object() for _ in range(shader_count)]


class _Pass:
    def __init__(self, name, shader_count):
        self.name = name
        self.variants = [_Variant(shader_count)]


class _Buffer:
    def __init__(self, type_name):
        self.type = _Named(type_name)


class _Material:
    name = "SunMoon"
    version = 25
    passes = [_Pass("Transparent", 2)]
    buffers = [_Buffer("Texture2D"), _Buffer("Uniform")]

    @staticmethod
    def get_platforms():
        return [_Named("Vulkan")]

    @staticmethod
    def get_stages():
        return [_Named("Vertex"), _Named("Fragment")]


def _report(path: str, *, name="SunMoon", version=25, platforms=("Vulkan",), stages=("Fragment", "Vertex"), shaders=2, variants=1):
    return MaterialReport(
        path=path,
        sha256="a" * 64,
        size=7,
        name=name,
        format_version=version,
        platforms=platforms,
        stages=stages,
        passes=("Transparent",),
        shader_count=shaders,
        variant_count=variants,
        texture_buffer_count=1,
        lazurite_version="test",
    )


class MaterialTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.bin = self.root / "SunMoon.material.bin"
        self.bin.write_bytes(b"fixture")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_summary_exposes_switch_invariants(self):
        report = summarize_material(_Material(), self.bin)
        self.assertEqual(report.name, "SunMoon")
        self.assertEqual(report.format_version, 25)
        self.assertEqual(report.platforms, ("Vulkan",))
        self.assertEqual(report.stages, ("Fragment", "Vertex"))
        self.assertEqual(report.shader_count, 2)
        self.assertEqual(report.variant_count, 1)
        self.assertEqual(report.texture_buffer_count, 1)
        self.assertEqual(report.size, 7)

    def test_comparison_passes_for_same_switch_material(self):
        comparison = compare_switch_materials(_report("baseline"), _report("candidate"))
        self.assertTrue(comparison.compatible)
        self.assertEqual(comparison.status, "built-and-inspected")
        self.assertFalse(comparison.to_dict()["hardware_verified"])

    def test_comparison_rejects_lost_vulkan(self):
        comparison = compare_switch_materials(
            _report("baseline"),
            _report("candidate", platforms=("ESSL_310",)),
        )
        self.assertFalse(comparison.compatible)
        self.assertFalse(comparison.checks["candidate_has_vulkan"])

    def test_comparison_rejects_format_change(self):
        comparison = compare_switch_materials(
            _report("baseline"), _report("candidate", version=23)
        )
        self.assertFalse(comparison.compatible)
        self.assertFalse(comparison.checks["same_format_version"])


class CompileBaselineTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.project = self.root / "project"
        self.project.mkdir()
        (self.project / "project.json").write_text('{"base_profile": {"platforms": ["Vulkan"]}}')
        self.output = self.root / "out"
        self.baseline = self.root / "Sky.material.bin"
        self.baseline.write_bytes(b"baseline")

    def tearDown(self):
        self.tempdir.cleanup()

    def _executable(self, name, contents):
        path = self.root / name
        path.write_text(contents)
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return path

    def _fake_shaderc(self):
        return self._executable("shaderc", "#!/bin/sh\nexit 0\n")

    def _fake_lazurite(self):
        return self._executable(
            "lazurite",
            "#!/bin/sh\n"
            "out=''\n"
            "while [ $# -gt 0 ]; do\n"
            "  if [ \"$1\" = '-o' ]; then out=$2; shift 2; else shift; fi\n"
            "done\n"
            "printf fixture > \"$out/Sky.material.bin\"\n",
        )

    def test_baseline_is_staged_and_matching_output_is_checked(self):
        baseline_report = _report(str(self.baseline), name="Sky")
        with patch("mss.materials.stage_baseline", return_value=baseline_report) as stage, patch(
            "mss.materials.assert_switch_comparison"
        ) as compare:
            produced = compile_project(
                self.project,
                self.output,
                shaderc=self._fake_shaderc(),
                lazurite=self._fake_lazurite(),
                baseline=self.baseline,
            )
        self.assertEqual([path.name for path in produced], ["Sky.material.bin"])
        stage.assert_called_once_with(self.project.resolve(), self.baseline)
        compare.assert_called_once_with(baseline_report, self.output / "Sky.material.bin")

    def test_baseline_requires_matching_material_name(self):
        baseline_report = _report(str(self.baseline), name="SunMoon")
        with patch("mss.materials.stage_baseline", return_value=baseline_report):
            with self.assertRaises(ToolchainError):
                compile_project(
                    self.project,
                    self.output,
                    shaderc=self._fake_shaderc(),
                    lazurite=self._fake_lazurite(),
                    baseline=self.baseline,
                )


class CliSafetyTests(unittest.TestCase):
    def test_switch_compile_requires_baseline_before_tool_lookup(self):
        with tempfile.TemporaryDirectory() as tempdir:
            project = Path(tempdir) / "project"
            project.mkdir()
            (project / "project.json").write_text("{}")
            self.assertEqual(main(["compile", str(project)]), 2)

    def test_unsafe_switch_smoke_build_is_explicit(self):
        parser = __import__("mss.cli", fromlist=["parser"]).parser()
        args = parser.parse_args(["compile", "project", "--unsafe-no-baseline"])
        self.assertTrue(args.unsafe_no_baseline)
        self.assertIsNone(args.baseline)
