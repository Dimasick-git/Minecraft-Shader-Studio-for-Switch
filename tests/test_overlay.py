import tempfile
import unittest
from pathlib import Path

from mss.errors import ValidationError
from mss.overlay import OverlayManager


class OverlayTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.romfs = self.root / "romfs_dump"
        self.materials_dir = self.romfs / "renderer" / "materials"
        self.materials_dir.mkdir(parents=True)
        (self.materials_dir / "Sky.material.bin").write_bytes(b"sky_vanilla")
        (self.materials_dir / "SunMoon.material.bin").write_bytes(b"sunmoon_vanilla")
        (self.materials_dir / "RenderChunk.material.bin").write_bytes(b"chunk_vanilla")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_extract_all_materials_is_sorted(self):
        manager = OverlayManager()
        destination = self.root / "extracted"
        extracted = manager.extract_materials(self.romfs, destination)
        self.assertEqual([path.name for path in extracted], [
            "RenderChunk.material.bin", "Sky.material.bin", "SunMoon.material.bin"
        ])
        self.assertEqual((destination / "Sky.material.bin").read_bytes(), b"sky_vanilla")

    def test_extract_with_pattern(self):
        extracted = OverlayManager().extract_materials(
            self.romfs, self.root / "filtered", patterns=["Sky", "Sun"]
        )
        self.assertEqual([path.name for path in extracted], ["Sky.material.bin", "SunMoon.material.bin"])

    def test_extract_with_no_match_raises(self):
        with self.assertRaises(ValidationError):
            OverlayManager().extract_materials(self.romfs, self.root / "empty", patterns=["Missing"])

    def test_prepare_layeredfs_structure_and_stale_cleanup(self):
        manager = OverlayManager(title_id="0100D71004694000")
        source = self.root / "built"
        source.mkdir()
        (source / "Sky.material.bin").write_bytes(b"sky_modded")
        output = self.root / "sd_card"
        destination = output / "atmosphere" / "contents" / "0100D71004694000" / "romfs" / "renderer" / "materials"
        destination.mkdir(parents=True)
        (destination / "Old.material.bin").write_bytes(b"stale")

        manager.prepare_layeredfs(source, output)

        self.assertEqual((destination / "Sky.material.bin").read_bytes(), b"sky_modded")
        self.assertFalse((destination / "Old.material.bin").exists())

    def test_prepare_rejects_empty_or_non_material_source(self):
        manager = OverlayManager()
        empty = self.root / "empty"
        empty.mkdir()
        with self.assertRaises(ValidationError):
            manager.prepare_layeredfs(empty, self.root / "out")
        not_material = self.root / "notes.txt"
        not_material.write_text("not a material")
        with self.assertRaises(ValidationError):
            manager.prepare_layeredfs(not_material, self.root / "out")

    def test_invalid_romfs_and_title_id_raise(self):
        with self.assertRaises(ValidationError):
            OverlayManager().extract_materials(self.root / "missing", self.root / "out")
        with self.assertRaises(ValidationError):
            OverlayManager(title_id="invalid-id")
