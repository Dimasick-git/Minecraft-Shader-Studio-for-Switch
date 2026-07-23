import json, os, stat, tempfile, unittest
from pathlib import Path
from mss.compile import compile_project, find_tool
from mss.errors import ToolchainError


class CompileTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.root = Path(self.t.name)
        self.project = self.root / "proj"
        self.project.mkdir()
        (self.project / "project.json").write_text('{"base_profile": {"platforms": ["Vulkan"]}}')
        self.out = self.root / "out"

    def tearDown(self):
        self.t.cleanup()

    def _fake_shaderc(self):
        p = self.root / "shadercRelease"
        p.write_text("#!/bin/sh\nexit 0\n")
        p.chmod(p.stat().st_mode | stat.S_IXUSR)
        return p

    def _fake_lazurite(self, rc=0, produce=True):
        """Фейковый lazurite: пишет argv в лог и создаёт материал в -o."""
        p = self.root / "lazurite"
        p.write_text(
            "#!/usr/bin/env python3\n"
            "import json, pathlib, sys\n"
            "a = sys.argv\n"
            f"log = pathlib.Path({str(self.root)!r}) / 'invocation.json'\n"
            "log.write_text(json.dumps(a))\n"
            "out = pathlib.Path(a[a.index('-o') + 1])\n"
            f"produce = {produce!r}\n"
            "if produce:\n"
            "    (out / 'Sky.material.bin').write_bytes(b'MSSTEST')\n"
            f"sys.exit({rc})\n"
        )
        p.chmod(p.stat().st_mode | stat.S_IXUSR)
        return p

    def test_compile_invokes_lazurite_and_collects_output(self):
        laz = self._fake_lazurite()
        bins = compile_project(self.project, self.out, shaderc=self._fake_shaderc(), lazurite=laz)
        self.assertEqual([b.name for b in bins], ["Sky.material.bin"])
        argv = json.loads((self.root / "invocation.json").read_text())
        self.assertEqual(argv[1], "build")
        self.assertIn("-p", argv)
        self.assertEqual(argv[argv.index("-p") + 1], "switch")  # профиль Switch по умолчанию
        self.assertIn("--shaderc", argv)

    def test_custom_profile_and_defines(self):
        laz = self._fake_lazurite()
        compile_project(self.project, self.out, profile="android",
                        defines=["FIRST_LIGHT_STRENGTH 0.5"],
                        shaderc=self._fake_shaderc(), lazurite=laz)
        argv = json.loads((self.root / "invocation.json").read_text())
        self.assertEqual(argv[argv.index("-p") + 1], "android")
        self.assertEqual(argv[argv.index("-d") + 1], "FIRST_LIGHT_STRENGTH 0.5")

    def test_missing_project_json(self):
        empty = self.root / "empty"
        empty.mkdir()
        with self.assertRaises(ToolchainError):
            compile_project(empty, self.out, shaderc=self._fake_shaderc(), lazurite=self._fake_lazurite())

    def test_nonzero_exit_raises(self):
        laz = self._fake_lazurite(rc=3)
        with self.assertRaises(ToolchainError):
            compile_project(self.project, self.out, shaderc=self._fake_shaderc(), lazurite=laz)

    def test_no_output_raises(self):
        laz = self._fake_lazurite(produce=False)
        with self.assertRaises(ToolchainError):
            compile_project(self.project, self.out, shaderc=self._fake_shaderc(), lazurite=laz)

    def test_find_tool_env(self):
        tool = self._fake_shaderc()
        os.environ["MSS_TEST_TOOL"] = str(tool)
        try:
            self.assertEqual(find_tool(None, "MSS_TEST_TOOL", ["missing-bin"]), str(tool))
        finally:
            del os.environ["MSS_TEST_TOOL"]

    def test_find_tool_missing(self):
        with self.assertRaises(ToolchainError):
            find_tool(None, "MSS_NO_SUCH_VAR", ["definitely-not-a-real-binary-42"])
