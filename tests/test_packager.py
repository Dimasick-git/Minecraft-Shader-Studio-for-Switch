import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from mss.errors import ValidationError
from mss.packager import build, validate_pack


class PackagerTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.pack = self.root / "pack"
        (self.pack / "materials").mkdir(parents=True)
        self.author = "Pack Author"
        (self.pack / "shader.json").write_text(
            json.dumps(
                {
                    "schema": 1,
                    "id": "vibrant-lite",
                    "name": "Vibrant Lite",
                    "version": "0.1.0",
                    "author": self.author,
                    "description": "test",
                    "materials_destination": "data/renderer/materials",
                }
            ),
            encoding="utf-8",
        )
        (self.pack / "materials" / "Sky.material.bin").write_bytes(b"MSS-TEST-FIXTURE")

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_validate(self):
        self.assertEqual(validate_pack(self.pack).id, "vibrant-lite")

    def test_build_layout_hash_manifest_and_author(self):
        with patch("mss.packager.assert_supported", return_value={"status": "verified"}):
            folder, archive = build(
                self.pack,
                self.root / "dist",
                "26.32",
                "1.11.2",
                "0123456789ABCDEF",
            )
        metadata = json.loads((folder / "MSS-MANIFEST.json").read_text())
        self.assertTrue(archive.is_file())
        self.assertEqual(metadata["author"], self.author)
        self.assertEqual(len(metadata["files"][0]["sha256"]), 64)
        with zipfile.ZipFile(archive) as zip_archive:
            self.assertIn(
                "atmosphere/contents/0123456789ABCDEF/romfs/data/renderer/materials/Sky.material.bin",
                zip_archive.namelist(),
            )

    def test_requires_material(self):
        (self.pack / "materials" / "Sky.material.bin").unlink()
        with self.assertRaises(ValidationError):
            validate_pack(self.pack)

    def test_rejects_symlink(self):
        try:
            (self.pack / "link").symlink_to(self.pack / "shader.json")
        except OSError:
            self.skipTest("symlink unavailable")
        with self.assertRaises(ValidationError):
            validate_pack(self.pack)
