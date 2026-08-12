import json
import tempfile
import unittest
from pathlib import Path

from mss.errors import ValidationError
from mss.models import ShaderManifest, validate_title_id

BASE = {
    "schema": 1,
    "id": "test-pack",
    "name": "Test",
    "version": "0.1.0",
    "author": "Dimasick-git",
    "description": "x",
    "materials_destination": "data/materials",
}


class ModelTests(unittest.TestCase):
    def write(self, data):
        temporary_directory = tempfile.TemporaryDirectory()
        path = Path(temporary_directory.name)
        (path / "shader.json").write_text(json.dumps(data), encoding="utf-8")
        return temporary_directory, path

    def test_manifest(self):
        temporary_directory, path = self.write(BASE)
        self.addCleanup(temporary_directory.cleanup)
        self.assertEqual(ShaderManifest.load(path).author, "Dimasick-git")

    def test_unknown_field(self):
        temporary_directory, path = self.write(BASE | {"evil": 1})
        self.addCleanup(temporary_directory.cleanup)
        with self.assertRaises(ValidationError):
            ShaderManifest.load(path)

    def test_traversal(self):
        temporary_directory, path = self.write(BASE | {"materials_destination": "../../escape"})
        self.addCleanup(temporary_directory.cleanup)
        with self.assertRaises(ValidationError):
            ShaderManifest.load(path)

    def test_rejects_non_object_and_invalid_destination(self):
        for data in ([], BASE | {"materials_destination": ""}, BASE | {"materials_destination": "renderer\\materials"}):
            temporary_directory, path = self.write(data)
            self.addCleanup(temporary_directory.cleanup)
            with self.assertRaises(ValidationError):
                ShaderManifest.load(path)

    def test_title_id(self):
        self.assertEqual(validate_title_id("0123456789abcdef"), "0123456789ABCDEF")

    def test_bad_title_id(self):
        with self.assertRaises(ValidationError):
            validate_title_id("../bad")
