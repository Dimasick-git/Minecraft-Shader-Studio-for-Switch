import os, stat, tempfile, unittest
from pathlib import Path
from mss.nvn import ShaderStage, compile_glsl, inspect_nvn, graft_nvn_prefix
from mss.errors import ValidationError
class NvnTests(unittest.TestCase):
    def setUp(self): self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name)
    def tearDown(self): self.t.cleanup()
    def fake_compiler(self):
        p=self.root/"uam-nvn"
        p.write_text("#!/usr/bin/env python3\nimport pathlib,sys\na=sys.argv\nraw=pathlib.Path(a[a.index('-r')+1]);out=pathlib.Path(a[a.index('-o')+1]);raw.write_bytes(b'R'*128);out.write_bytes(b'DKSH')\n")
        p.chmod(p.stat().st_mode|stat.S_IXUSR);return p
    def test_compile_real_subprocess_contract(self):
        src=self.root/"sky.vert";src.write_text("#version 450\nvoid main(){gl_Position=vec4(0.0);}\n")
        a=compile_glsl(src,ShaderStage.VERTEX,self.root/"out",compiler=self.fake_compiler())
        self.assertEqual(a.size,128);self.assertTrue(a.dksh.is_file());self.assertEqual(len(a.sha256),64)
    def test_inspect(self):
        p=self.root/"shader.bin";p.write_bytes(b'P'*48+b'R'*128);i=inspect_nvn(p);self.assertTrue(i.has_nvn_prefix);self.assertEqual(i.sph_offset,48)
    def test_graft_preserves_prefix(self):
        t=self.root/"base.bin";r=self.root/"raw.bin";o=self.root/"out.bin";t.write_bytes(b'P'*48+b'B'*128);r.write_bytes(b'R'*128)
        graft_nvn_prefix(t,r,o);self.assertEqual(o.read_bytes(),b'P'*48+b'R'*128);self.assertTrue(Path(str(o)+'.json').is_file())
    def test_reject_unaligned(self):
        t=self.root/"base.bin";r=self.root/"raw.bin";t.write_bytes(b'P'*48+b'B'*128);r.write_bytes(b'bad')
        with self.assertRaises(ValidationError):graft_nvn_prefix(t,r,self.root/"out")
