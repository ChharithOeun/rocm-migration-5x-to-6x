#!/usr/bin/env python3
"""
verify_rocm.py — ROCm + PyTorch health check script
Checks ROCm version, GPU detection, PyTorch compatibility,
MIOpen functionality, and memory allocation.

Usage:
    python3 verify_rocm.py
    python3 verify_rocm.py --verbose
    python3 verify_rocm.py --json

Part of: https://github.com/chharcop/rocm-migration-5x-to-6x
"""

import sys
import os
import argparse
import subprocess
import json
from pathlib import Path


RESET  = "\033[0m"
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"
DIM    = "\033[2m"


def pass_(msg):  return f"{GREEN}[PASS]{RESET} {msg}"
def fail_(msg):  return f"{RED}[FAIL]{RESET} {msg}"
def warn_(msg):  return f"{YELLOW}[WARN]{RESET} {msg}"
def info_(msg):  return f"{DIM}[INFO]{RESET} {msg}"


class CheckResult:
    def __init__(self, name, passed, message, detail=None):
        self.name    = name
        self.passed  = passed
        self.message = message
        self.detail  = detail  # extra debug info

    def __str__(self):
        fn = pass_ if self.passed else fail_
        s = fn(self.message)
        if self.detail:
            s += f"\n       {DIM}{self.detail}{RESET}"
        return s


results = []

def check(name, passed, message, detail=None):
    r = CheckResult(name, passed, message, detail)
    results.append(r)
    return r


# ── Section 1: ROCm Installation ────────────────────────────────────────────

def check_rocm_version():
    print(f"\n{BOLD}ROCm Installation Check{RESET}")
    print("=" * 40)

    # Method 1: /opt/rocm/.info/version
    version_file = Path("/opt/rocm/.info/version")
    if version_file.exists():
        version = version_file.read_text().strip()
        r = check("rocm_version", True, f"ROCm version: {version}")
        print(r)
        return version

    # Method 2: rocminfo
    try:
        out = subprocess.check_output(
            ["rocminfo"], stderr=subprocess.DEVNULL, text=True, timeout=10
        )
        for line in out.splitlines():
            if "ROCm Version" in line or "Version" in line:
                version = line.split(":")[-1].strip()
                r = check("rocm_version", True, f"ROCm version: {version}")
                print(r)
                return version
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Method 3: dpkg
    try:
        out = subprocess.check_output(
            ["dpkg", "-l", "rocm-core"], stderr=subprocess.DEVNULL, text=True
        )
        for line in out.splitlines():
            if "rocm-core" in line and line.startswith("ii"):
                version = line.split()[2]
                r = check("rocm_version", True, f"ROCm version (dpkg): {version}")
                print(r)
                return version
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    r = check("rocm_version", False,
              "ROCm not found or version unknown",
              "Tried /opt/rocm/.info/version, rocminfo, dpkg")
    print(r)
    return None


def check_gpu_detected():
    try:
        out = subprocess.check_output(
            ["rocminfo"], stderr=subprocess.DEVNULL, text=True, timeout=15
        )
        gpus = []
        in_agent = False
        name = gfx = None
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("Agent") and line[5:].strip().isdigit():
                if name and gfx:
                    gpus.append((name, gfx))
                in_agent = True
                name = gfx = None
            elif in_agent:
                if line.startswith("Name:"):
                    name = line.split(":", 1)[1].strip()
                elif line.startswith("ISA Info"):
                    pass
                elif "ISA" in line and "gfx" in line.lower():
                    gfx = line.split()[-1] if line.split() else None
        if name and gfx:
            gpus.append((name, gfx))

        # Filter out CPU agents
        gpu_agents = [(n, g) for n, g in gpus
                      if n and not any(x in n.lower() for x in ["cpu", "intel", "epyc", "core"])]

        if gpu_agents:
            for n, g in gpu_agents:
                r = check("gpu_detected", True, f"GPU detected: {n} ({g})")
                print(r)
        else:
            r = check("gpu_detected", False, "No AMD GPU agent found in rocminfo")
            print(r)
        return gpu_agents

    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        r = check("gpu_detected", False, "rocminfo failed", str(e))
        print(r)
        return []


def check_device_files():
    kfd = Path("/dev/kfd")
    dri = Path("/dev/dri")

    if kfd.exists():
        try:
            # Try to open for read access
            with open(kfd, "rb"):
                pass
            r = check("kfd_access", True, "/dev/kfd accessible")
        except PermissionError:
            stat = oct(kfd.stat().st_mode)[-3:]
            r = check("kfd_access", False,
                      "/dev/kfd exists but permission denied",
                      f"Permissions: {stat} — run: sudo usermod -a -G render,video $USER")
    else:
        r = check("kfd_access", False,
                  "/dev/kfd not found",
                  "ROCm driver not loaded or not installed")
    print(r)

    render_nodes = list(dri.glob("renderD*")) if dri.exists() else []
    if render_nodes:
        r = check("dri_access", True,
                  f"{render_nodes[0]} accessible")
    else:
        r = check("dri_access", False,
                  "/dev/dri/renderD* not found",
                  "GPU driver may not be loaded")
    print(r)


def check_groups():
    import grp
    username = os.environ.get("USER", os.environ.get("LOGNAME", ""))
    for group_name in ("render", "video"):
        try:
            grp_info = grp.getgrnam(group_name)
            in_group = username in grp_info.gr_mem
            # Also check via getgroups
            try:
                gid = grp_info.gr_gid
                in_group = in_group or (gid in os.getgroups())
            except Exception:
                pass
            if in_group:
                r = check(f"group_{group_name}", True,
                          f"User '{username}' is in '{group_name}' group")
            else:
                r = check(f"group_{group_name}", False,
                          f"User '{username}' NOT in '{group_name}' group",
                          f"Fix: sudo usermod -a -G {group_name} $USER  then log out/in")
        except KeyError:
            r = check(f"group_{group_name}", False,
                      f"Group '{group_name}' does not exist",
                      "ROCm may not be installed correctly")
        print(r)


# ── Section 2: PyTorch ───────────────────────────────────────────────────────

def check_pytorch():
    print(f"\n{BOLD}PyTorch Check{RESET}")
    print("=" * 40)

    try:
        import torch
    except ImportError:
        r = check("torch_import", False,
                  "PyTorch not installed",
                  "pip install torch --index-url https://download.pytorch.org/whl/rocm6.3")
        print(r)
        return None

    ver = torch.__version__
    if "rocm" in ver.lower():
        r = check("torch_version", True, f"PyTorch version: {ver}")
    elif "cpu" in ver.lower():
        r = check("torch_version", False,
                  f"PyTorch version: {ver} (CPU-only build!)",
                  "Reinstall with: pip install torch --index-url https://download.pytorch.org/whl/rocm6.3")
    else:
        r = check("torch_version", True, f"PyTorch version: {ver}")
    print(r)

    hip_ver = getattr(torch.version, "hip", None)
    if hip_ver:
        r = check("torch_rocm", True, f"ROCm in PyTorch build: {hip_ver}")
    else:
        r = check("torch_rocm", False,
                  "ROCm not found in PyTorch build",
                  "This is a CPU or CUDA build, not a ROCm build")
    print(r)

    return torch


def check_cuda_api(torch):
    """torch.cuda is the HIP/ROCm API in ROCm builds."""
    if torch is None:
        return

    avail = torch.cuda.is_available()
    if avail:
        r = check("cuda_available", True, "torch.cuda.is_available(): True")
        print(r)
        dev_count = torch.cuda.device_count()
        for i in range(dev_count):
            name = torch.cuda.get_device_name(i)
            r = check(f"gpu_name_{i}", True, f"GPU {i}: {name}")
            print(r)
    else:
        r = check("cuda_available", False,
                  "torch.cuda.is_available(): False",
                  "Check ROCm installation, device permissions, and PyTorch wheel version")
        print(r)


def check_miopen(torch):
    """Run a simple conv2d to exercise MIOpen."""
    if torch is None or not torch.cuda.is_available():
        r = check("miopen", False,
                  "MIOpen: skipped (GPU not available)")
        print(r)
        return

    try:
        import torch.nn as nn
        conv = nn.Conv2d(1, 1, 3, padding=1).cuda()
        x = torch.randn(1, 1, 8, 8, device="cuda")
        with torch.no_grad():
            y = conv(x)
        assert y.shape == (1, 1, 8, 8), f"Unexpected output shape: {y.shape}"
        r = check("miopen", True, "MIOpen: functional (conv2d test passed)")
    except Exception as e:
        r = check("miopen", False,
                  "MIOpen: conv2d test FAILED",
                  f"{type(e).__name__}: {e}\nTry: rm -rf ~/.cache/miopen/ and retry")
    print(r)


def check_memory(torch, size_gb=1):
    """Allocate and free GPU memory."""
    if torch is None or not torch.cuda.is_available():
        r = check("memory_alloc", False,
                  "Memory test: skipped (GPU not available)")
        print(r)
        return

    try:
        size_bytes = size_gb * 1024 ** 3
        n_elements = size_bytes // 4  # float32
        t = torch.empty(n_elements, dtype=torch.float32, device="cuda")
        allocated_gb = t.numel() * t.element_size() / 1024**3
        del t
        torch.cuda.empty_cache()
        r = check("memory_alloc", True,
                  f"Memory allocation: {allocated_gb:.1f} GB allocated and freed successfully")
    except Exception as e:
        r = check("memory_alloc", False,
                  f"Memory allocation failed ({size_gb} GB)",
                  f"{type(e).__name__}: {e}")
    print(r)


def check_env_vars():
    print(f"\n{BOLD}Environment Variables{RESET}")
    print("=" * 40)

    important_vars = [
        "ROCM_PATH", "HIP_PATH", "LD_LIBRARY_PATH",
        "HSA_OVERRIDE_GFX_VERSION", "MIOPEN_FIND_MODE", "AMD_LOG_LEVEL"
    ]
    for var in important_vars:
        val = os.environ.get(var)
        if val:
            # Truncate long values
            display = val if len(val) < 80 else val[:77] + "..."
            print(info_(f"{var}={display}"))
        else:
            print(info_(f"{var}=(not set)"))


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ROCm + PyTorch health check"
    )
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show extra detail")
    parser.add_argument("--json", action="store_true",
                        help="Output results as JSON")
    parser.add_argument("--memory-gb", type=int, default=1, metavar="GB",
                        help="GB to allocate in memory test (default: 1)")
    args = parser.parse_args()

    # Run all checks
    check_rocm_version()
    check_gpu_detected()
    check_device_files()
    check_groups()

    torch = check_pytorch()
    check_cuda_api(torch)
    check_miopen(torch)
    check_memory(torch, size_gb=args.memory_gb)

    check_env_vars()

    # Summary
    print(f"\n{BOLD}Summary{RESET}")
    print("=" * 40)
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    total  = len(results)

    if failed == 0:
        print(f"{GREEN}{BOLD}All {total} checks passed!{RESET}")
        exit_code = 0
    else:
        print(f"{RED}{BOLD}{failed} of {total} checks failed:{RESET}")
        for r in results:
            if not r.passed:
                print(f"  - {r.message}")
        exit_code = 1

    if args.json:
        output = {
            "passed": passed,
            "failed": failed,
            "total": total,
            "checks": [
                {
                    "name":    r.name,
                    "passed":  r.passed,
                    "message": r.message,
                    "detail":  r.detail,
                }
                for r in results
            ]
        }
        print("\n" + json.dumps(output, indent=2))

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
