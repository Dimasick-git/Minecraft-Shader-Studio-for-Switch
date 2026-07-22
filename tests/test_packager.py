import json, tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
from mss.packager import build, validate_pack
from mss.errors import ValidationError
class PackagerTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory(); self.root=Path(self.t.name); self.pack=self.root/"pack"; (self.pack/"materials").mkdir(parents=True)
        (self.pack/"shader.json").write_text(json.dumps({"schema":1,"id":"vibrant-lite","name":"Vibrant Lite","version":"0.1.0","author":"Dimasick-git","description":"test","materials_destination":"data/renderer/materials"}),encoding="utf-8")
        (self.pack/"materials"/"Sky.material.bin").write_bytes(b"MSS-TEST-FIXTURE")
    def tearDown(self): self.t.cleanup()
    def test_validate(self): self.assertEqual(validate_pack(self.pack).id,"vibrant-lite")
    def test_build_layout_and_hash_manifest(self):
        with patch("mss.packager.assert_supported",return_value={"status":"verified"}):
            folder,archive=build(self.pack,self.root/"dist","26.32","1.11.2","0123456789ABCDEF")
        self.assertTrue(archive.is_file()); meta=json.loads((folder/"MSS-MANIFEST.json").read_text())
        self.assertEqual(meta["author"],"Dimasick-git"); self.assertEqual(len(meta["files"][0]["sha256"]),64)
        with zipfile.ZipFile(archive) as z: self.assertIn("atmosphere/contents/0123456789ABCDEF/romfs/data/renderer/materials/Sky.material.bin",z.namelist())
    def test_requires_material(self):
        (self.pack/"materials"/"Sky.material.bin").unlink()
        with self.assertRaises(ValidationError): validate_pack(self.pack)
    def test_rejects_symlink(self):
        try: (self.pack/"link").symlink_to(self.pack/"shader.json")
        except OSError: self.skipTest("symlink unavailable")
        with self.assertRaises(ValidationError): validate_pack(self.pack)
