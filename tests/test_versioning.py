import unittest
from mss.versioning import Version
from mss.errors import ValidationError
class VersionTests(unittest.TestCase):
    def test_order(self): self.assertLess(Version.parse("1.11.1"), Version.parse("1.11.2"))
    def test_2026_scheme(self): self.assertEqual(str(Version.parse("26.33")), "26.33")
    def test_rejects_injection(self):
        for bad in ("v1.2", "1.2;rm -rf /", "1..2", "01.2", ""):
            with self.subTest(bad=bad), self.assertRaises(ValidationError): Version.parse(bad)
