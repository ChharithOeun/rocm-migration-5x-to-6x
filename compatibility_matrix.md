# ROCm ↔ PyTorch ↔ GPU Compatibility Matrix

Full reference for version combinations. See README.md for the migration guide.

---

## ROCm ↔ PyTorch Stable Releases

| PyTorch | ROCm | Python | Ubuntu | Status |
|---------|------|--------|--------|--------|
| 2.0.1 | 5.5 | 3.8–3.11 | 20.04, 22.04 | EOL |
| 2.1.0 | 5.6 | 3.8–3.11 | 20.04, 22.04 | EOL |
| 2.1.2 | 5.7 | 3.8–3.11 | 20.04, 22.04 | EOL |
| 2.2.2 | 5.7 | 3.8–3.12 | 20.04, 22.04 | EOL |
| 2.3.1 | 6.0 | 3.8–3.12 | 20.04, 22.04 | Stable |
| 2.4.0 | 6.1 | 3.8–3.12 | 20.04, 22.04 | Stable |
| 2.4.1 | 6.1 | 3.8–3.12 | 20.04, 22.04 | Stable |
| 2.5.1 | 6.2 | 3.9–3.12 | 22.04, 24.04 | Stable |
| **2.6.0** | **6.3** | 3.9–3.12 | 22.04, 24.04 | **Recommended** |
| **2.7.0** | **6.3** | 3.9–3.13 | 22.04, 24.04 | **Latest** |

### Install Commands

```bash
# PyTorch 2.6.0 + ROCm 6.3 (recommended)
pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 \
    --index-url https://download.pytorch.org/whl/rocm6.3

# PyTorch 2.7.0 + ROCm 6.3 (latest)
pip install torch==2.7.0 torchvision==0.22.0 torchaudio==2.7.0 \
    --index-url https://download.pytorch.org/whl/rocm6.3

# PyTorch 2.5.1 + ROCm 6.2
pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 \
    --index-url https://download.pytorch.org/whl/rocm6.2

# PyTorch 2.4.1 + ROCm 6.1
pip install torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 \
    --index-url https://download.pytorch.org/whl/rocm6.1

# PyTorch 2.3.1 + ROCm 6.0
pip install torch==2.3.1 torchvision==0.18.1 torchaudio==2.3.1 \
    --index-url https://download.pytorch.org/whl/rocm6.0

# PyTorch 2.2.2 + ROCm 5.7 (last 5.x)
pip install torch==2.2.2 torchvision==0.17.2 torchaudio==2.2.2 \
    --index-url https://download.pytorch.org/whl/rocm5.7
```

---

## GPU Architecture Support by ROCm Version

| GPU Family | Architecture | GFX ID | 5.7 | 6.0 | 6.1 | 6.2 | 6.3 |
|---|---|---|---|---|---|---|---|
| RX 5500 XT | RDNA 1 | gfx1012 | Partial | Partial | Partial | Partial | Partial |
| RX 5600/5700 XT | RDNA 1 | gfx1010 | Partial | Partial | Partial | Partial | Partial |
| RX 6600 XT | RDNA 2 | gfx1032 | Yes | Yes | Yes | Yes | Yes |
| RX 6700 XT | RDNA 2 | gfx1031 | Yes | Yes | Yes | Yes | Yes |
| RX 6800/6900 XT | RDNA 2 | gfx1030 | Yes | Yes | Yes | Yes | Yes |
| RX 7600 | RDNA 3 | gfx1102 | No | Beta | Beta | Yes | Yes |
| RX 7700/7800 XT | RDNA 3 | gfx1101 | No | Beta | Beta | Yes | Yes |
| RX 7900 GRE/XT/XTX | RDNA 3 | gfx1100 | Limited | Yes | Yes | Yes | Yes |
| RX 9070 XT | RDNA 4 | gfx1201 | No | No | No | No | Beta |
| MI50 (Vega 20) | GCN 5.1 | gfx906 | Yes | Maintenance | EOL | EOL | EOL |
| MI100 | CDNA 1 | gfx908 | Yes | Yes | Yes | Yes | Yes |
| MI200/MI250X | CDNA 2 | gfx90a | Yes | Yes | Yes | Yes | Yes |
| MI300X | CDNA 3 | gfx942 | No | Yes | Yes | Yes | Yes |

**Partial support** = works with `HSA_OVERRIDE_GFX_VERSION` but not officially tested.
**Maintenance** = security fixes only, no new features.
**EOL** = end-of-life, may be removed in future releases.

---

## ROCm Version Release Timeline

| Version | Release Date | Highlights |
|---------|-------------|------------|
| 5.7.0 | Sep 2023 | Last ROCm 5.x release |
| 5.7.1 | Oct 2023 | Bug fixes |
| 6.0.0 | Dec 2023 | Hard FHS migration, symlinks removed |
| 6.0.2 | Jan 2024 | Bug fixes |
| 6.1.0 | Apr 2024 | Beta WSL2 support |
| 6.1.3 | Jun 2024 | WSL2 improvements, bug fixes |
| 6.2.0 | Sep 2024 | Default compiler → amdclang++ |
| 6.2.1 | Oct 2024 | Bug fixes |
| 6.3.0 | Dec 2024 | MIOpen kernel fusion API, stable WSL2 |
| 6.3.1 | Dec 2024 | Bug fixes |
| 6.3.2 | Jan 2025 | Bug fixes |
| 6.3.3 | Feb 2025 | Latest ROCm 6.x |

---

## OS / Distribution Support

| Distribution | ROCm 5.7 | ROCm 6.0 | ROCm 6.1 | ROCm 6.2 | ROCm 6.3 |
|---|---|---|---|---|---|
| Ubuntu 20.04 LTS | Yes | Yes | Yes | Limited | Limited |
| Ubuntu 22.04 LTS | Yes | Yes | Yes | Yes | Yes |
| Ubuntu 24.04 LTS | No | No | Beta | Yes | Yes |
| RHEL 8 | Yes | Yes | Yes | Yes | Yes |
| RHEL 9 | Yes | Yes | Yes | Yes | Yes |
| SLES 15 SP5 | Yes | Yes | Yes | Yes | Yes |
| WSL2 (Ubuntu 22.04) | No | No | Beta | Beta | Yes |
| WSL2 (Ubuntu 24.04) | No | No | No | Beta | Yes |

---

## Docker Image Tags

```bash
# Official ROCm images
rocm/rocm-terminal:6.3
rocm/rocm-terminal:6.2
rocm/rocm-terminal:6.1
rocm/rocm-terminal:6.0.2

# PyTorch + ROCm (official AMD-built images)
rocm/pytorch:rocm6.3_ubuntu22.04_py3.10_pytorch_2.6.0
rocm/pytorch:rocm6.3_ubuntu22.04_py3.10_pytorch_2.7.0
rocm/pytorch:rocm6.2_ubuntu22.04_py3.10_pytorch_2.5.1
rocm/pytorch:rocm6.1_ubuntu22.04_py3.10_pytorch_2.4.1
rocm/pytorch:rocm6.0_ubuntu22.04_py3.10_pytorch_2.3.1

# Check current tags: https://hub.docker.com/r/rocm/pytorch/tags
```

---

## Key Environment Variables Reference

| Variable | Default | Purpose | Changed in 6.x? |
|---|---|---|---|
| `ROCM_PATH` | `/opt/rocm` | Root ROCm install path | No |
| `HIP_PATH` | `/opt/rocm` | HIP install path | Yes — merged into ROCM_PATH |
| `LD_LIBRARY_PATH` | (user-set) | Shared library search path | Must update: `/opt/rocm/lib` |
| `PATH` | (user-set) | Binary search path | Must update: `/opt/rocm/lib/llvm/bin` |
| `HSA_OVERRIDE_GFX_VERSION` | (not set) | Override GPU architecture | Per-GPU support added (suffix `_0`, `_1`) |
| `MIOPEN_FIND_MODE` | `3` | Convolution search mode | Changed from `1` to `3` |
| `AMD_LOG_LEVEL` | `0` | Debug verbosity (0=off, 4=max) | No |
| `MIOPEN_USER_DB_PATH` | `~/.config/miopen` | MIOpen user database | No |
| `GPU_MAX_HW_QUEUES` | (driver default) | Hardware queue count | No |
| `HCC_AMDGPU_TARGET` | (auto) | Target GPU for HIP (legacy) | Deprecated in 6.x |

---

*Last updated: 2026-03-29 | Covers ROCm 5.7 through 6.3.3*
