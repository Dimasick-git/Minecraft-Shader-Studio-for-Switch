import json, tempfile, unittest
from pathlib import Path
from mss.models import ShaderManifest, validate_title_id
from mss.errors import ValidationError
BASE={"schema":1,"id":"test-pack","name":"Test","version":"0.1.0","author":"Dimasick-git","description":"x","materials_destination":"data/materials"}
class ModelTests(unittest.TestCase):
    def write(self, data):
        td=tempfile.TemporaryDirectory(); p=Path(td.name); (p/"shader.json").write_text(json.dumps(data),encoding="utf-8"); return td,p
    def test_manifest(self):
        td,p=self.write(BASE); self.addCleanup(td.cleanup); self.assertEqual(ShaderManifest.load(p).author,"Dimasick-git")
    def test_unknown_field(self):
        td,p=self.write(BASE|{"evil":1}); self.addCleanup(td.cleanup)
        with self.assertRaises(ValidationError): ShaderManifest.load(p)
    def test_traversal(self):
        td,p=self.write(BASE|{"materials_destination":"../../escape"}); self.addCleanup(td.cleanup)
        with self.assertRaises(ValidationError): ShaderManifest.load(p)
    def test_title_id(self): self.assertEqual(validate_title_id("0123456789abcdef"),"0123456789ABCDEF")
    def test_bad_title_id(self):
        with self.assertRaises(ValidationError): validate_title_id("../bad")
