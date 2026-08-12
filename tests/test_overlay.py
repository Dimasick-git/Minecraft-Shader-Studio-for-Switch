import tempfile
import unittest
from pathlib import Path
from mss.overlay import OverlayManager
from mss.errors import ValidationError

class OverlayTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        
        # Setup fake RomFS dump
        self.romfs = self.root / "romfs_dump"
        self.materials_dir = self.romfs / "renderer" / "materials"
        self.materials_dir.mkdir(parents=True)
        
        (self.materials_dir / "Sky.material.bin").write_bytes(b"sky_vanilla")
        (self.materials_dir / "SunMoon.material.bin").write_bytes(b"sunmoon_vanilla")
        (self.materials_dir / "RenderChunk.material.bin").write_bytes(b"chunk_vanilla")
        
    def tearDown(self):
        self.tempdir.cleanup()
        
    def test_extract_all_materials(self):
        manager = OverlayManager()
        dest = self.root / "extracted"
        extracted = manager.extract_materials(self.romfs, dest)
        
        self.assertEqual(len(extracted), 3)
        self.assertTrue((dest / "Sky.material.bin").exists())
        self.assertEqual((dest / "Sky.material.bin").read_bytes(), b"sky_vanilla")
        
    def test_extract_with_pattern(self):
        manager = OverlayManager()
        dest = self.root / "extracted_filtered"
        extracted = manager.extract_materials(self.romfs, dest, patterns=["Sky", "Sun"])
        
        self.assertEqual(len(extracted), 2)
        filenames = [f.name for f in extracted]
        self.assertIn("Sky.material.bin", filenames)
        self.assertIn("SunMoon.material.bin", filenames)
        self.assertNotIn("RenderChunk.material.bin", filenames)
        
    def test_prepare_layeredfs_structure(self):
        manager = OverlayManager(title_id="0100D71004694000")
        source = self.root / "built_materials"
        source.mkdir()
        (source / "Sky.material.bin").write_bytes(b"sky_modded")
        
        out = self.root / "sd_card"
        manager.prepare_layeredfs(source, out)
        
        target_file = out / "atmosphere" / "contents" / "0100D71004694000" / "romfs" / "renderer" / "materials" / "Sky.material.bin"
        self.assertTrue(target_file.exists())
        self.assertEqual(target_file.read_bytes(), b"sky_modded")
        
    def test_invalid_romfs_raises(self):
        manager = OverlayManager()
        with self.assertRaises(ValidationError):
            manager.extract_materials(self.root / "non_existent", self.root / "out")
            
    def test_invalid_title_id_raises(self):
        with self.assertRaises(ValidationError):
            OverlayManager(title_id="invalid-id")
