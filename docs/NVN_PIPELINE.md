# NVN / Maxwell pipeline

## Upstream components

1. **nvnprogram/uam-nvn** — public fork of UAM modified to compile NVN shaders. Preferred compiler executable: `uam-nvn`.
2. **devkitPro/uam** — GLSL → native Maxwell ISA compiler. Its `-r` option emits raw Maxwell bytecode and `-o` emits DKSH.
3. **devkitPro/deko3d** — open low-level Switch graphics API produced from NVN reverse engineering. It is not a binary-compatible clone of NVN, but documents the GPU model and build-time workflow.
4. **DCNick3/shader-compiler-rs** — NVN binary → GLSL inspection path; accepts the 0x30-byte NVN-specific prefix before NVIDIA SPH.
5. **MaterialBinTool / Lazurite** — RenderDragon material unpack/repack layer.

## Implemented path

```text
GLSL
  │ mss nvn compile (uam-nvn preferred, uam fallback)
  ▼
64-byte-aligned native Maxwell payload + optional DKSH
  │ mss nvn graft --template user-owned-switch-shader.bin
  ▼
experimental NVN blob + provenance sidecar
  │ material adapter / version fixture
  ▼
RenderDragon material.bin
  │ mss build
  ▼
Atmosphère LayeredFS package
```

## Commands

```bash
export MSS_UAM=/path/to/uam-nvn
mss nvn compile examples/nvn/minimal.vert --stage vert --output build/nvn
mss nvn inspect path/to/user-owned-shader.bin
mss nvn graft --template base.nvn.bin --raw build/nvn/minimal.vert.maxwell.bin --output build/nvn/minimal.nvn.bin
```

The graft step preserves the 0x30-byte NVN prefix from a user-owned template and records SHA-256 provenance. It is intentionally marked experimental: RenderDragon variants may encode additional program metadata outside the shader payload. Hardware fixtures determine compatibility; the tool does not silently claim success.

## Licensing strategy

Upstream tools are executed as separate programs and are not copied into this repository. This avoids mixing licenses and makes versions auditable. Pin tool revisions in release notes before publishing verified binaries.

Author: **Dimasick-git**.
