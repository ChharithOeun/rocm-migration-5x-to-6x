<p align="center"><img src="assets/banner.png" alt="Banner" width="100%"></p>
# ROCm 5.x → 6.x Migration Guide

> **The guide AMD should have written.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![ROCm](https://img.shields.io/badge/ROCm-6.3.3-red.svg)](https://rocm.docs.amd.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.6%2B-orange.svg)](https://pytorch.org)

Migrating from ROCm 5.x to 6.x is **not backwards compatible**. Users upgrading from 5.7 face version mismatch errors, broken PyTorch wheels, and driver conflicts. AMD's official docs are 40 pages of theory with no practical examples.

This guide gives you everything in one place: parallel installs, a PyTorch compatibility matrix, every breaking change with before/after examples, and a full rollback procedure.

---

## Table of Contents

1. [Why This Guide Exists](#why-this-guide-exists)
2. [Version Comparison](#version-comparison)
3. [Parallel Installation — Keep Both 5.x and 6.x](#parallel-installation)
4. [PyTorch Wheel Compatibility Matrix](#pytorch-wheel-compatibility-matrix)
5. [Breaking Changes Checklist](#breaking-changes-checklist)
6. [Step-by-Step Migration](#step-by-step-migration)
   - [Ubuntu 22.04](#ubuntu-2204)
   - [WSL2 on Windows](#wsl2-on-windows)
   - [Docker Containers](#docker-containers)
7. [Rollback Procedure](#rollback-procedure)
8. [Troubleshooting](#troubleshooting)
9. [Verification Script](#verification-script)

---

## Why This Guide Exists

ROCm 6.0 introduced a **hard filesystem reorganization** — backward-compat symlinks were removed, library paths changed, and several packages were restructured. If you `apt upgrade` without reading the release notes, your ML stack silently breaks.

The three most common failure modes:

| Failure | Cause |
|---------|-------|
| `hipErrorNoBinaryForGpu` | PyTorch wheel built for wrong ROCm version |
| `MIOpen: Unable to load library` | Library path changed from `/opt/rocm-5.x/<component>/lib` to `/opt/rocm/lib` |
| GPU not detected after upgrade | Kernel module mismatch, user not in `render` group, or wrong AMDGPU installer version |

AMD's official documentation is thorough but scattered across 8+ pages and written for first-time installs, not migrations. This guide focuses on the delta.

---

## Version Comparison

Full matrix in [compatibility_matrix.md](compatibility_matrix.md).

| Feature / Change | ROCm 5.7 | ROCm 6.0 | ROCm 6.1 | ROCm 6.2 | ROCm 6.3 |
|---|---|---|---|---|---|
| **Status** | EOL (security only) | Stable | Stable | Stable | Latest 6.x |
| **PyTorch stable** | 2.1, 2.2 | 2.3 | 2.3, 2.4 | 2.4, 2.5 | 2.6, 2.7 |
| **gfx906 (MI50)** | Supported | Maintenance | EOL | EOL | EOL |
| **gfx1100 (RX 7900)** | Limited | Full | Full | Full | Full |
| **gfx1101/1102 (RX 7600/7700)** | No | Beta | Beta | Full | Full |
| **WSL2 support** | No | No | Beta | Beta | Stable |
| **Filesystem layout** | Legacy paths + symlinks | FHS-compliant, **symlinks removed** | FHS | FHS | FHS |
| **Default compiler** | hipcc | hipcc | hipcc | **amdclang++** | amdclang++ |
| **LLVM path** | `/opt/rocm/llvm` | `/opt/rocm/lib/llvm` | same | same | same |
| **MIOpen find mode default** | 1 | **3** | 3 | 3 | 3 |
| **rocRAND/hipRAND** | Combined | Split packages | Split | Split | Split |

### What Changed in Each Release

**ROCm 6.0** (the hard break):
- Filesystem Hierarchy Standard fully adopted, backward-compat symlinks **deleted**
- `LLVM` path moved: `/opt/rocm/llvm` → `/opt/rocm/lib/llvm`
- rocRAND and hipRAND split into separate packages
- HIP runtime struct members and deprecated enum values removed
- gfx906 (MI50/Vega 20) enters maintenance-only mode
- `MIOPEN_FIND_MODE` default changed from `1` to `3`

**ROCm 6.1**:
- Beta WSL2 support added
- HIP graph improvements
- ROCm SMI library renamed to `amdsmi`

**ROCm 6.2**:
- Default compiler switches from `hipcc` to `amdclang++` for math libraries
- `HIPCC_COMPILE_FLAGS_APPEND` bug: flags get prepended instead of appended (known issue)

**ROCm 6.3** (latest 6.x as of Feb 2025):
- Kernel fusion API for convolution added to MIOpen
- Improved post-install udev rules
- Stable WSL2 support

---

## Parallel Installation

You can keep ROCm 5.7 and 6.x installed simultaneously and switch between them. Each version installs to its own versioned directory.

### How It Works

ROCm installs into `/opt/rocm-<version>/` (e.g., `/opt/rocm-5.7.1/`, `/opt/rocm-6.3.3/`). A symlink `/opt/rocm` points to the active version.

```
/opt/rocm-5.7.1/    ← ROCm 5.7 (kept intact)
/opt/rocm-6.3.3/    ← ROCm 6.3 (new install)
/opt/rocm           → symlink to whichever is active
```

### Install ROCm 6.3 Alongside 5.7

```bash
# Download the ROCm 6.3 amdgpu-install package
wget https://repo.radeon.com/amdgpu-install/6.3/ubuntu/jammy/amdgpu-install_6.3.60300-1_all.deb
sudo apt install ./amdgpu-install_6.3.60300-1_all.deb
sudo apt update

# Install ROCm 6.3 WITHOUT removing existing ROCm 5.7
# The --no-dkms flag prevents kernel module conflicts during install
sudo amdgpu-install --usecase=rocm --no-dkms

# At this point both /opt/rocm-5.7.x and /opt/rocm-6.3.x exist
ls /opt/rocm-*/bin/rocminfo
```

### Switching Between Versions

```bash
# Switch to ROCm 6.3
sudo ln -sfn /opt/rocm-6.3.3 /opt/rocm
source ~/.bashrc
rocminfo | grep "ROCm Version"

# Switch back to ROCm 5.7
sudo ln -sfn /opt/rocm-5.7.1 /opt/rocm
source ~/.bashrc
rocminfo | grep "ROCm Version"
```

### Shell Environment Per-Version

Add a helper function to `~/.bashrc`:

```bash
rocm-use() {
    local ver=$1
    local path="/opt/rocm-${ver}"
    if [ ! -d "$path" ]; then
        echo "ROCm $ver not found at $path"
        return 1
    fi
    sudo ln -sfn "$path" /opt/rocm
    export PATH="/opt/rocm/bin:$PATH"
    export LD_LIBRARY_PATH="/opt/rocm/lib:$LD_LIBRARY_PATH"
    echo "Switched to ROCm $ver ($(rocminfo 2>/dev/null | grep 'ROCm Version' | head -1))"
}

# Usage:
# rocm-use 5.7.1
# rocm-use 6.3.3
```

### Python Virtual Environments Per-Version

Keep separate venvs for each ROCm version to avoid PyTorch wheel conflicts:

```bash
# ROCm 5.7 environment
python3 -m venv ~/venvs/rocm57
source ~/venvs/rocm57/bin/activate
pip install torch==2.2.2 --index-url https://download.pytorch.org/whl/rocm5.7

# ROCm 6.3 environment
python3 -m venv ~/venvs/rocm63
source ~/venvs/rocm63/bin/activate
pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/rocm6.3
```

---

## PyTorch Wheel Compatibility Matrix

> **The #1 pain point.** PyTorch wheels are compiled against a specific ROCm version. Installing the wrong one silently degrades to CPU or crashes with `hipErrorNoBinaryForGpu`.

### Stable Release Matrix

| PyTorch Version | ROCm Version | Install Command |
|---|---|---|
| 2.1.x | ROCm 5.6 | `pip install torch==2.1.2 --index-url https://download.pytorch.org/whl/rocm5.6` |
| 2.1.x | ROCm 5.7 | `pip install torch==2.1.2 --index-url https://download.pytorch.org/whl/rocm5.7` |
| 2.2.x | ROCm 5.7 | `pip install torch==2.2.2 --index-url https://download.pytorch.org/whl/rocm5.7` |
| 2.3.x | ROCm 6.0 | `pip install torch==2.3.1 --index-url https://download.pytorch.org/whl/rocm6.0` |
| 2.4.x | ROCm 6.1 | `pip install torch==2.4.1 --index-url https://download.pytorch.org/whl/rocm6.1` |
| 2.5.x | ROCm 6.2 | `pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/rocm6.2` |
| **2.6.x** | **ROCm 6.3** | `pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/rocm6.3` |
| **2.7.x** | **ROCm 6.3** | `pip install torch==2.7.0 --index-url https://download.pytorch.org/whl/rocm6.3` |

> Always check [pytorch.org/get-started/locally](https://pytorch.org/get-started/locally) for the latest — wheel availability changes between releases.

### Full Install Command (with torchvision + torchaudio)

```bash
# ROCm 6.3 + PyTorch 2.6 (recommended as of early 2026)
pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 \
    --index-url https://download.pytorch.org/whl/rocm6.3

# ROCm 6.3 + PyTorch 2.7 (latest)
pip install torch==2.7.0 torchvision==0.22.0 torchaudio==2.7.0 \
    --index-url https://download.pytorch.org/whl/rocm6.3
```

### Nightly / Pre-release (for cutting-edge ROCm 6.4+)

```bash
pip install --pre torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/nightly/rocm6.3
```

### Verify the Correct Wheel Was Installed

```python
import torch
print(torch.__version__)           # e.g. 2.6.0+rocm6.3
print(torch.version.hip)           # e.g. 6.3.42134
print(torch.cuda.is_available())   # True (HIP maps to CUDA API)
print(torch.cuda.get_device_name(0))
```

If `torch.__version__` shows `+cpu` instead of `+rocm6.x`, you installed the wrong wheel.

---

## Breaking Changes Checklist

### 1. Filesystem / Library Paths

**What changed:** ROCm 5.x used per-component directories with symlinks. ROCm 6.0 enforces flat layout, symlinks removed.

| Component | ROCm 5.x path | ROCm 6.x path |
|---|---|---|
| Libraries | `/opt/rocm/hip/lib/*.so` | `/opt/rocm/lib/*.so` |
| Headers | `/opt/rocm/hip/include/` | `/opt/rocm/include/hip/` |
| LLVM | `/opt/rocm/llvm/bin/` | `/opt/rocm/lib/llvm/bin/` |
| CMake configs | `/opt/rocm/<component>/lib/cmake/` | `/opt/rocm/lib/cmake/<component>/` |
| Binaries | `/opt/rocm/<component>/bin/` | `/opt/rocm/bin/` |

**Migration actions:**

```bash
# Find all scripts/configs referencing old paths
grep -r "/opt/rocm/hip/lib" ~/.local ~/.config /etc 2>/dev/null
grep -r "/opt/rocm/llvm/bin" ~/.local ~/.config /etc 2>/dev/null

# Update LD_LIBRARY_PATH in ~/.bashrc
# OLD:
export LD_LIBRARY_PATH=/opt/rocm/hip/lib:/opt/rocm/opencl/lib
# NEW:
export LD_LIBRARY_PATH=/opt/rocm/lib

# Update PATH
# OLD:
export PATH=/opt/rocm/bin:/opt/rocm/hip/bin:/opt/rocm/llvm/bin:$PATH
# NEW:
export PATH=/opt/rocm/bin:/opt/rocm/lib/llvm/bin:$PATH
```

### 2. MIOpen API Changes

**What changed in 6.0:**
- Default `MIOPEN_FIND_MODE` changed from `1` (Normal) to `3` (Fast)
- Mode 3 uses a heuristics-based algorithm selector — faster first run, potentially suboptimal kernels

**If you relied on exhaustive kernel search:**

```bash
# Restore old behavior (exhaustive search — slow but optimal kernels)
export MIOPEN_FIND_MODE=1

# Or: mode 2 = Normal + heuristics fallback
export MIOPEN_FIND_MODE=2
```

**MIOpen cache location changed:**

```bash
# 5.x cache
~/.cache/miopen/2/

# 6.x cache
~/.cache/miopen/3/

# Clear stale cache after upgrade (prevents kernel mismatch crashes)
rm -rf ~/.cache/miopen/
```

**Kernel Fusion API (new in 6.3):** If you're using custom MIOpen fusion plans, the API is now stable. See `miopenFusionPlanDescriptor` in the updated headers.

### 3. Environment Variables

| Variable | ROCm 5.x | ROCm 6.x | Notes |
|---|---|---|---|
| `HSA_OVERRIDE_GFX_VERSION` | Single value | Single OR per-GPU (`_0`, `_1`, ...) | Format: `MAJOR.MINOR.PATCH` e.g. `10.3.0` |
| `ROCM_PATH` | `/opt/rocm` | `/opt/rocm` | No change, but now required for some tools |
| `HIP_PATH` | `/opt/rocm/hip` | `/opt/rocm` | **Changed** — HIP merged into main tree |
| `MIOPEN_FIND_MODE` | Default `1` | Default `3` | Set to `1` to restore old behavior |
| `AMD_LOG_LEVEL` | Available | Available | `0`=none, `1`=error, `4`=debug |

**HSA_OVERRIDE_GFX_VERSION per-GPU (new in 6.x):**

```bash
# All GPUs (old behavior, still works)
export HSA_OVERRIDE_GFX_VERSION=10.3.0

# Per-GPU overrides (new in 6.x)
export HSA_OVERRIDE_GFX_VERSION_0=10.3.0   # GPU 0 → gfx1030
export HSA_OVERRIDE_GFX_VERSION_1=11.0.0   # GPU 1 → gfx1100
```

**GFX version lookup table:**

| AMD GPU | Architecture | GFX | HSA Override Value |
|---|---|---|---|
| RX 5700 XT | RDNA 1 | gfx1010 | `10.1.0` |
| RX 6700 XT | RDNA 2 | gfx1031 | `10.3.1` |
| RX 6800/6900 XT | RDNA 2 | gfx1030 | `10.3.0` |
| RX 7600 | RDNA 3 | gfx1102 | `11.0.2` |
| RX 7700/7800 XT | RDNA 3 | gfx1101 | `11.0.1` |
| RX 7900 XTX | RDNA 3 | gfx1100 | `11.0.0` |
| MI250X | CDNA 2 | gfx90a | `9.0.10` |
| MI300X | CDNA 3 | gfx942 | `9.4.2` |

### 4. hipcc Compiler Flag Changes

**What changed in 6.2:** Default compiler for math libraries switched from `hipcc` to `amdclang++`.

```bash
# Check which compiler is being used
which hipcc        # /opt/rocm/bin/hipcc (wrapper script)
which amdclang++   # /opt/rocm/bin/amdclang++ (actual compiler)

# ROCm 6.2+ recommended: use amdclang++ directly
amdclang++ -x hip -O3 --offload-arch=gfx1100 mykernel.hip -o mykernel

# Flag that changed behavior
# OLD (5.x): hipcc auto-detected --offload-arch
# NEW (6.x): specify explicitly or use cmake/rocbuild
```

**Known bug in 6.2 (`HIPCC_COMPILE_FLAGS_APPEND`):**

```bash
# Bug: HIPCC_COMPILE_FLAGS_APPEND prepends instead of appends
# Workaround: pass flags directly
export HIPCC_COMPILE_FLAGS_APPEND="-D MY_DEFINE"  # May not work as expected
# Instead: add flags directly in your CMakeLists.txt or Makefile
```

### 5. Removed Packages / Renamed Libraries

```bash
# rocRAND and hipRAND are now separate packages
# OLD (5.x): sudo apt install rocrand
# NEW (6.x):
sudo apt install rocrand hiprand

# ROCm SMI renamed
# OLD (5.x): rocm-smi
# NEW (6.x): amdsmi (rocm-smi still works as an alias but deprecated)
amdsmi monitor   # new command
```

---

## Step-by-Step Migration

### Ubuntu 22.04

#### Pre-Migration Checklist

```bash
# 1. Note your current ROCm version
cat /opt/rocm/.info/version 2>/dev/null || rocminfo | grep "ROCm Version"

# 2. Export your current Python environments
pip freeze > ~/rocm5-requirements.txt

# 3. Back up ROCm-related environment variables
env | grep -E "(ROCm|ROCM|HSA|HIP|AMD|MIOPEN)" > ~/rocm5-env-backup.txt

# 4. Check your GPU model — verify it's supported in ROCm 6.x
rocminfo | grep "Name:" | head -5
```

#### Install ROCm 6.3 on Ubuntu 22.04

```bash
# Step 1: Add ROCm signing key
sudo mkdir -p /etc/apt/keyrings
wget -q -O - https://repo.radeon.com/rocm/rocm.gpg.key | \
    gpg --dearmor | sudo tee /etc/apt/keyrings/rocm.gpg > /dev/null

# Step 2: Add repository
echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/rocm.gpg] \
    https://repo.radeon.com/rocm/apt/6.3 jammy main" | \
    sudo tee /etc/apt/sources.list.d/rocm.list

# Step 3: Update and install
sudo apt update
sudo apt install rocm

# Or use the amdgpu-install script (recommended for driver + ROCm combo):
wget https://repo.radeon.com/amdgpu-install/6.3/ubuntu/jammy/amdgpu-install_6.3.60300-1_all.deb
sudo apt install ./amdgpu-install_6.3.60300-1_all.deb
sudo apt update
sudo amdgpu-install --usecase=rocm

# Step 4: Add user to required groups
sudo usermod -a -G render,video $USER

# Step 5: Reload udev rules
sudo udevadm control --reload-rules && sudo udevadm trigger

# Step 6: Log out and back in (group membership requires new session)
# Then verify:
groups | grep -E "(render|video)"
rocminfo | grep "ROCm Version"
```

#### Migrate Python / PyTorch

```bash
# Create new virtual environment for ROCm 6.3
python3 -m venv ~/venvs/rocm63
source ~/venvs/rocm63/bin/activate

# Install PyTorch for ROCm 6.3
pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 \
    --index-url https://download.pytorch.org/whl/rocm6.3

# Reinstall your other packages
pip install -r ~/rocm5-requirements.txt  # Review this — some may need ROCm-specific versions

# Run the verification script
python verify_rocm.py
```

#### Update ~/.bashrc

```bash
# Remove old ROCm 5.x entries, add new ones:
# OLD — remove these:
# export PATH=/opt/rocm/hip/bin:$PATH
# export LD_LIBRARY_PATH=/opt/rocm/hip/lib:$LD_LIBRARY_PATH
# export HIP_PATH=/opt/rocm/hip

# NEW — add these:
export ROCM_PATH=/opt/rocm
export PATH=/opt/rocm/bin:/opt/rocm/lib/llvm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:$LD_LIBRARY_PATH
# HIP_PATH is now same as ROCM_PATH in 6.x:
export HIP_PATH=/opt/rocm
```

---

### WSL2 on Windows

> ROCm 6.1+ has beta WSL2 support. ROCm 6.3 is the recommended version for WSL2.

#### Requirements

- Windows 11 with WSL2 enabled
- **AMD Adrenalin Edition driver 25.8.1+** installed on Windows host
- Ubuntu 22.04 WSL distribution

> **Critical:** The Windows AMD driver version must match or exceed what the ROCm version expects. Driver mismatch is the #1 WSL2 setup failure.

#### Install

```bash
# In WSL2 Ubuntu terminal:

# 1. Verify WSL2 GPU passthrough is working
ls /dev/dxg   # Must exist — this is the paravirtualized GPU interface
ls /dev/dri/  # May show renderD128 if driver bridge is active

# 2. Install ROCm 6.3 (same Ubuntu steps as above)
wget https://repo.radeon.com/amdgpu-install/6.3/ubuntu/jammy/amdgpu-install_6.3.60300-1_all.deb
sudo apt install ./amdgpu-install_6.3.60300-1_all.deb
sudo apt update

# WSL2: use --no-dkms (no kernel module installation in WSL2)
sudo amdgpu-install --usecase=rocm --no-dkms

# 3. Add user to groups
sudo usermod -a -G render,video $USER
# Log out of WSL2 (wsl --terminate Ubuntu && wsl) then back in

# 4. Test
rocminfo
```

#### WSL2-Specific Environment Variables

```bash
# Add to ~/.bashrc in WSL2:
export HSA_OVERRIDE_GFX_VERSION=11.0.0   # For RX 7000 series; adjust for your GPU
export DISPLAY=:0                          # If using GUI tools

# WSL2 uses /dev/dxg instead of /dev/kfd in some configurations
# If rocminfo fails, try:
export ROC_ENABLE_PRE_VEGA=1   # For older RDNA GPUs
```

#### Common WSL2 Issues

| Error | Fix |
|-------|-----|
| `No GPU agent found` | Check `/dev/dxg` exists; update Windows AMD driver |
| `HSA_STATUS_ERROR_OUT_OF_RESOURCES` | Set `HSA_OVERRIDE_GFX_VERSION` for your GPU |
| `Cannot open /dev/kfd` | `sudo chmod 666 /dev/kfd` or add user to `video` group |
| PyTorch detects CPU only | Wrong PyTorch wheel; reinstall with `--index-url ...rocm6.3` |

---

### Docker Containers

AMD publishes official ROCm Docker images. These are the safest migration path.

#### Official Images

```bash
# ROCm 6.3 base
docker pull rocm/rocm-terminal:6.3

# PyTorch with ROCm 6.3
docker pull rocm/pytorch:rocm6.3_ubuntu22.04_py3.10_pytorch_2.6.0

# Check available tags:
# https://hub.docker.com/r/rocm/pytorch/tags
```

#### Run with GPU Access

```bash
# Linux
docker run -it \
    --device=/dev/kfd \
    --device=/dev/dri \
    --group-add=video \
    --group-add=render \
    --ipc=host \
    rocm/pytorch:rocm6.3_ubuntu22.04_py3.10_pytorch_2.6.0 \
    bash

# Inside container — verify:
python3 -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

#### Dockerfile for Custom ROCm 6.3 Image

```dockerfile
FROM rocm/rocm-terminal:6.3

RUN apt-get update && apt-get install -y \
    python3-pip python3-venv git \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 \
    --index-url https://download.pytorch.org/whl/rocm6.3

# Optional: set default GFX version for RX 7900 XTX
ENV HSA_OVERRIDE_GFX_VERSION=11.0.0
```

---

## Rollback Procedure

If ROCm 6.x breaks your setup, here's how to safely revert to 5.7.

### Quick Rollback (Symlink Method — if you did parallel install)

```bash
# Just point /opt/rocm back to the 5.7 directory
sudo ln -sfn /opt/rocm-5.7.1 /opt/rocm

# Verify
rocminfo | grep "ROCm Version"

# Reactivate your 5.7 Python environment
source ~/venvs/rocm57/bin/activate
```

### Full Uninstall of ROCm 6.x

```bash
# Remove ROCm 6.x packages while keeping 5.x
sudo amdgpu-install --uninstall  # if you used amdgpu-install
# Or:
sudo apt remove --purge rocm-core rocm-hip-runtime rocm-opencl-runtime
sudo apt autoremove

# Reinstall ROCm 5.7 if fully removed
wget https://repo.radeon.com/amdgpu-install/5.7/ubuntu/jammy/amdgpu-install_5.7.50700-1_all.deb
sudo apt install ./amdgpu-install_5.7.50700-1_all.deb
sudo apt update
sudo amdgpu-install --usecase=rocm
```

### Restore Python Environment

```bash
# Activate the old venv you saved before migration
source ~/venvs/rocm57/bin/activate

# Or recreate from backup
python3 -m venv ~/venvs/rocm57-restored
source ~/venvs/rocm57-restored/bin/activate
pip install -r ~/rocm5-requirements.txt
```

---

## Troubleshooting

### `hipErrorNoBinaryForGpu`

**Cause:** PyTorch wheel compiled for a different ROCm version, or GPU not in the supported architecture list for that wheel.

```bash
# Check what ROCm version PyTorch was built with
python3 -c "import torch; print(torch.version.hip)"

# Check what GPU you have
rocminfo | grep "Name:" | head -5

# Check if your GFX version is supported by this PyTorch build
python3 -c "import torch; print(torch._C._cuda_getArchFlags())"  # shows supported archs

# Fix: reinstall PyTorch for your ROCm version
pip uninstall torch torchvision torchaudio
pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/rocm6.3

# If GPU is unsupported (e.g., RDNA 1), use HSA override:
export HSA_OVERRIDE_GFX_VERSION=10.3.0  # Treat as gfx1030
```

### `MIOpen: Unable to load library`

**Cause:** MIOpen library not found at expected path. Usually a path migration issue from 5.x to 6.x.

```bash
# Find where MIOpen is actually installed
find /opt/rocm* -name "libMIOpen.so*" 2>/dev/null

# Check what path MIOpen is looking in
AMD_LOG_LEVEL=4 python3 -c "import torch; torch.zeros(1).cuda()" 2>&1 | grep -i miopen

# Fix: update LD_LIBRARY_PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:$LD_LIBRARY_PATH

# If still failing, clear MIOpen cache (stale compiled kernels from 5.x):
rm -rf ~/.cache/miopen/
```

### PyTorch Not Detecting GPU After Upgrade

```bash
# Step-by-step diagnosis:

# 1. Is rocminfo working?
rocminfo | grep -E "(Name|ROCm Version)"

# 2. Are you in the render group?
groups | grep render
# If not: sudo usermod -a -G render,video $USER && log out/in

# 3. Check /dev/kfd permissions
ls -la /dev/kfd
# Should be: crw-rw---- ... video ... /dev/kfd
# Fix: sudo chmod 660 /dev/kfd

# 4. Check ROCm/PyTorch version match
python3 -c "import torch; print(torch.version.hip)"
rocminfo | grep "ROCm Version"
# These should match major.minor

# 5. Verify HIP is finding the device
python3 -c "
import torch
print('CUDA/HIP available:', torch.cuda.is_available())
print('Device count:', torch.cuda.device_count())
if torch.cuda.device_count() > 0:
    print('Device name:', torch.cuda.get_device_name(0))
"
```

### Version Mismatch Between ROCm and PyTorch

```bash
# Identify the mismatch
python3 -c "import torch; print('PyTorch ROCm:', torch.version.hip)"
rocminfo | head -20 | grep -i rocm

# Example mismatch:
# PyTorch ROCm: 5.7.31921  ← compiled against 5.7
# ROCm installed: 6.3.3    ← but system has 6.3

# Fix: reinstall PyTorch for system ROCm version
pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/rocm6.3
```

### Kernel Module / Driver Issues

```bash
# Check if amdgpu kernel module is loaded
lsmod | grep amdgpu

# Check dmesg for AMD GPU errors
sudo dmesg | grep -i "amdgpu\|radeon" | tail -20

# If module not loading:
sudo modprobe amdgpu
# Check for errors:
sudo dmesg | tail -30

# Reinstall kernel module
sudo amdgpu-install --usecase=dkms
sudo reboot
```

---

## Verification Script

Save as `verify_rocm.py` — or use the [included script](verify_rocm.py) in this repo.

```python
python3 verify_rocm.py
```

Expected output (healthy ROCm 6.x setup):

```
ROCm Installation Check
=======================
[PASS] ROCm version: 6.3.3
[PASS] GPU detected: AMD Radeon RX 7900 XTX (gfx1100)
[PASS] /dev/kfd accessible
[PASS] /dev/dri/renderD128 accessible
[PASS] User in 'render' group
[PASS] User in 'video' group

PyTorch Check
=============
[PASS] PyTorch version: 2.6.0+rocm6.3
[PASS] ROCm in PyTorch build: 6.3.42134
[PASS] torch.cuda.is_available(): True
[PASS] GPU name: AMD Radeon RX 7900 XTX
[PASS] MIOpen: functional (conv2d test passed)
[PASS] Memory allocation: 1 GB allocated and freed successfully

All checks passed!
```

---

## Contributing

Found a version combination not in the matrix? Hit an error not in the troubleshooting section? PRs welcome.

1. Fork → branch → PR
2. Include your GPU model, ROCm version, and Ubuntu/Windows version in the PR description

---

## Support This Work

If this guide saved you hours of debugging, consider:

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-chharcop-yellow)](https://buymeacoffee.com/chharcop)

---

*Last updated: 2026-03-29 | ROCm 6.3.3 | PyTorch 2.6/2.7*
