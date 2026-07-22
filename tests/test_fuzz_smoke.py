import random, string, unittest
from mss.versioning import Version
from mss.errors import ValidationError
class FuzzSmokeTests(unittest.TestCase):
    def test_random_garbage_never_crashes_unexpectedly(self):
        rng=random.Random(0xD1555)
        alphabet=string.printable
        for _ in range(2000):
            value="".join(rng.choice(alphabet) for _ in range(rng.randrange(0,40)))
            try: Version.parse(value)
            except ValidationError: pass
