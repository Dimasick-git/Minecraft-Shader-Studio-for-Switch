import importlib.util
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "fetch_toolchain.py"
SPEC = importlib.util.spec_from_file_location("mss_fetch_toolchain", SCRIPT)
fetch_toolchain = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(fetch_toolchain)


class FetchToolchainTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.archive = self.root / "fixture.zip"
        self.destination = self.root / "out"

    def tearDown(self):
        self.tempdir.cleanup()

    def _write_zip(self, entries):
        with zipfile.ZipFile(self.archive, "w") as archive:
            for entry in entries:
                if len(entry) == 2:
                    archive.writestr(entry[0], entry[1])
                else:
                    info = zipfile.ZipInfo(entry[0])
                    info.external_attr = entry[2]
                    archive.writestr(info, entry[1])

    def test_extracts_regular_archive(self):
        self._write_zip([("nested/file.txt", "ok")])
        members = fetch_toolchain.extract_zip_safely(self.archive, self.destination)
        self.assertEqual(members, ["nested/file.txt"])
        self.assertEqual((self.destination / "nested/file.txt").read_text(), "ok")

    def test_rejects_path_traversal(self):
        self._write_zip([("../outside.txt", "no")])
        with self.assertRaisesRegex(RuntimeError, "небезопасный путь"):
            fetch_toolchain.extract_zip_safely(self.archive, self.destination)
        self.assertFalse((self.root / "outside.txt").exists())

    def test_rejects_symbolic_link(self):
        symlink_mode = (stat.S_IFLNK | 0o777) << 16
        self._write_zip([("link", "target", symlink_mode)])
        with self.assertRaisesRegex(RuntimeError, "symbolic link"):
            fetch_toolchain.extract_zip_safely(self.archive, self.destination)

    def test_rejects_oversized_uncompressed_archive(self):
        self._write_zip([("payload", "x" * 32)])
        original = fetch_toolchain.MAX_ZIP_UNCOMPRESSED_BYTES
        fetch_toolchain.MAX_ZIP_UNCOMPRESSED_BYTES = 16
        try:
            with self.assertRaisesRegex(RuntimeError, "безопасный лимит"):
                fetch_toolchain.extract_zip_safely(self.archive, self.destination)
        finally:
            fetch_toolchain.MAX_ZIP_UNCOMPRESSED_BYTES = original

    def test_hash_mismatch_deletes_file(self):
        payload = self.root / "payload"
        payload.write_bytes(b"trusted?")
        with self.assertRaisesRegex(RuntimeError, "SHA-256 не совпадает"):
            fetch_toolchain.verify_sha256(payload, "0" * 64, "fixture")
        self.assertFalse(payload.exists())
