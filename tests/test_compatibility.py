import json, tempfile, unittest
from pathlib import Path
from mss.compatibility import assert_supported
from mss.errors import CompatibilityError
class CompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory(); self.p=Path(self.t.name)/"m.json"
        self.p.write_text(json.dumps({"schema":1,"targets":[{"minecraft":"26.32","atmosphere_min":"1.11.2","status":"verified"},{"minecraft":"26.33","atmosphere_min":"1.11.2","status":"detected"}]}))
    def tearDown(self): self.t.cleanup()
    def test_verified(self): self.assertEqual(assert_supported("26.32","1.11.2",matrix_path=self.p)["status"],"verified")
    def test_old_atmosphere(self):
        with self.assertRaises(CompatibilityError): assert_supported("26.32","1.11.1",matrix_path=self.p)
    def test_detected_is_blocked(self):
        with self.assertRaises(CompatibilityError): assert_supported("26.33","1.11.2",matrix_path=self.p)
    def test_override(self): self.assertEqual(assert_supported("99.1","9.9",allow_untested=True,matrix_path=self.p)["status"],"unsafe-override")
