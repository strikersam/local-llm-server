"""hardware/detector.py — Hardware detection and model compatibility.

Detects the host machine's CPU, RAM, and GPU/VRAM configuration, then
evaluates each known Ollama model against hardware requirements to produce
a compatibility label:

  COMPATIBLE   — model will run at recommended speed on this machine
  DEGRADED     — model will run but slower than expected (CPU only or low VRAM)
  INCOMPATIBLE — model requires more RAM/VRAM than available

Used by:
  - The routing engine to avoid dispatching to incompatible models
  - The Models Hub UI to show per-machine labels
  - The Setup Wizard to recommend appropriate default models

Detection strategy:
  1. psutil  → CPU count, total system RAM
  2. subprocess nvidia-smi → NVIDIA VRAM
  3. subprocess rocm-smi   → AMD VRAM (optional)
  4. torch (optional import) → cross-vendor GPU memory
  5. platform                → Apple Silicon MPS memory estimate from psutil
"""

from __future__ import annotations

import asyncio
import functools
import json
import logging
import platform
import re
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import psutil
from fastapi import APIRouter

log = logging.getLogger("qwen-proxy")


# ── Compatibility label ────────────────────────────────────────────────────────

class ModelCompatibilityLabel(str, Enum):
    COMPATIBLE   = "compatible"     # Runs well on this machine
    DEGRADED     = "degraded"       # Runs but slower (CPU fallback, partial VRAM)
    INCOMPATIBLE = "incompatible"   # Not enough RAM/VRAM to load


# ── Hardware profile ───────────────────────────────────────────────────────────

@dataclass
class GPUDevice:
    index:      int
    name:       str
    vram_gb:    float
    vendor:     str          # nvidia | amd | apple | intel | unknown
    driver:     str = ""


@dataclass
class HardwareProfile:
    # CPU
    cpu_model:      str
    cpu_cores:      int           # physical cores
    cpu_threads:    int           # logical CPUs

    # RAM
    ram_total_gb:   float
    ram_available_gb: float

    # GPU
    gpus:           list[GPUDevice] = field(default_factory=list)

    # Derived
    detected_at:    float = field(default_factory=time.time)
    platform:       str = ""

    @property
    def total_vram_gb(self) -> float:
        return sum(g.vram_gb for g in self.gpus)

    @property
    def has_gpu(self) -> bool:
        return len(self.gpus) > 0

    @property
    def best_gpu(self) -> GPUDevice | None:
        if not self.gpus:
            return None
        return max(self.gpus, key=lambda g: g.vram_gb)

    def as_dict(self) -> dict[str, Any]:
        return {
            "cpu_model":       self.cpu_model,
            "cpu_cores":       self.cpu_cores,
            "cpu_threads":     self.cpu_threads,
            "ram_total_gb":    round(self.ram_total_gb, 1),
            "ram_available_gb": round(self.ram_available_gb, 1),
            "gpus": [
                {
                    "index":   g.index,
                    "name":    g.name,
                    "vram_gb": round(g.vram_gb, 1),
                    "vendor":  g.vendor,
                    "driver":  g.driver,
                }
                for g in self.gpus
            ],
            "total_vram_gb": round(self.total_vram_gb, 1),
            "has_gpu":       self.has_gpu,
            "platform":      self.platform,
            "detected_at":   self.detected_at,
        }


# ── Model requirements database ───────────────────────────────────────────────
# Format: model_name_pattern → {ram_gb, vram_gb, notes}
# vram_gb = 0 means CPU-only is acceptable

_MODEL_REQUIREMENTS: list[dict[str, Any]] = [
    # Tiny / embedding models
    {"pattern": r"nomic-embed|all-minilm|mxbai-embed",   "ram_gb": 2,  "vram_gb": 1,  "param_b": 0.1},
    {"pattern": r"phi3:mini|phi-3-mini|phi3\.5:mini",     "ram_gb": 4,  "vram_gb": 3,  "param_b": 3.8},
    {"pattern": r"llama3\.2:1b|llama3\.2-1b",             "ram_gb": 4,  "vram_gb": 2,  "param_b": 1},
    {"pattern": r"gemma2:2b|gemma-2-2b",                  "ram_gb": 4,  "vram_gb": 3,  "param_b": 2},
    {"pattern": r"qwen2\.5:0\.5b|qwen2\.5:1\.5b",         "ram_gb": 4,  "vram_gb": 2,  "param_b": 1.5},
    # Small models (3–8B)
    {"pattern": r"llama3\.2:3b|llama3\.2-3b",             "ram_gb": 8,  "vram_gb": 4,  "param_b": 3},
    {"pattern": r"qwen2\.5:3b",                           "ram_gb": 8,  "vram_gb": 4,  "param_b": 3},
    {"pattern": r"mistral:7b|mistral-7b",                 "ram_gb": 8,  "vram_gb": 6,  "param_b": 7},
    {"pattern": r"llama3(:8b|\.1:8b|\.2:8b|-8b|-8B)",    "ram_gb": 8,  "vram_gb": 6,  "param_b": 8},
    {"pattern": r"qwen2\.5:7b|qwen3:7b|qwen3:8b",        "ram_gb": 8,  "vram_gb": 6,  "param_b": 8},
    {"pattern": r"gemma2:9b|gemma-2-9b",                  "ram_gb": 12, "vram_gb": 8,  "param_b": 9},
    {"pattern": r"deepseek-r1:7b",                        "ram_gb": 8,  "vram_gb": 6,  "param_b": 7},
    {"pattern": r"phi4:14b",                              "ram_gb": 16, "vram_gb": 10, "param_b": 14},
    # Medium models (14–32B)
    {"pattern": r"qwen2\.5:14b|qwen3:14b",               "ram_gb": 16, "vram_gb": 12, "param_b": 14},
    {"pattern": r"llama3\.1:70b|llama3-70b",              "ram_gb": 48, "vram_gb": 40, "param_b": 70},
    {"pattern": r"mistral:22b|mixtral:8x7b",              "ram_gb": 32, "vram_gb": 24, "param_b": 22},
    {"pattern": r"qwen2\.5:32b|qwen3:32b|qwen3-coder:32b", "ram_gb": 24, "vram_gb": 20, "param_b": 32},
    {"pattern": r"deepseek-r1:14b",                       "ram_gb": 16, "vram_gb": 12, "param_b": 14},
    {"pattern": r"deepseek-r1:32b",                       "ram_gb": 32, "vram_gb": 24, "param_b": 32},
    # Large models (30B+)
    {"pattern": r"qwen3-coder:30b|qwen2\.5-coder:32b",    "ram_gb": 24, "vram_gb": 20, "param_b": 30},
    {"pattern": r"deepseek-r1:70b",                       "ram_gb": 64, "vram_gb": 48, "param_b": 70},
    {"pattern": r"llama3\.1:405b",                        "ram_gb": 256,"vram_gb": 200,"param_b": 405},
    # Generic fallback by parameter count in name
    {"pattern": r":(\d+)b",                               "ram_gb": 0,  "vram_gb": 0,  "param_b": None},
]


def _lookup_requirements(model_name: str) -> dict[str, Any]:
    """Return the best-matching requirement spec for a model name."""
    model_lower = model_name.lower()
    for spec in _MODEL_REQUIREMENTS:
        if re.search(spec["pattern"], model_lower, re.IGNORECASE):
            if spec["param_b"] is None:
                # Generic rule: parse param count from name
                m = re.search(r":(\d+)b", model_lower)
                if m:
                    p = int(m.group(1))
                    return {
                        "ram_gb":  max(4, p * 0.7),
                        "vram_gb": max(2, p * 0.55),
                        "param_b": p,
                    }
            return spec
    # Unknown model — conservative default
    return {"ram_gb": 8, "vram_gb": 6, "param_b": None}


# ── Compatibility check ────────────────────────────────────────────────────────

@dataclass
class ModelCompatibility:
    model:       str
    label:       ModelCompatibilityLabel
    reason:      str
    ram_required_gb:  float
    vram_required_gb: float
    ram_available_gb: float
    vram_available_gb: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "model":              self.model,
            "label":              self.label.value,
            "reason":             self.reason,
            "ram_required_gb":    round(self.ram_required_gb, 1),
            "vram_required_gb":   round(self.vram_required_gb, 1),
            "ram_available_gb":   round(self.ram_available_gb, 1),
            "vram_available_gb":  round(self.vram_available_gb, 1),
        }


def check_model_compatibility(
    model_name: str,
    profile: HardwareProfile,
) -> ModelCompatibility:
    """Evaluate whether *model_name* can run on *profile*."""
    spec         = _lookup_requirements(model_name)
    req_ram      = spec["ram_gb"]
    req_vram     = spec["vram_gb"]
    avail_ram    = profile.ram_total_gb
    avail_vram   = profile.total_vram_gb

    # Check VRAM first
    if avail_vram > 0 and req_vram > 0:
        if req_vram > avail_vram * 1.05:        # allow 5% slack
            if req_ram <= avail_ram * 0.9:
                label  = ModelCompatibilityLabel.DEGRADED
                reason = (
                    f"Model needs {req_vram:.0f} GB VRAM but only "
                    f"{avail_vram:.0f} GB available — will use CPU (slow)."
                )
            else:
                label  = ModelCompatibilityLabel.INCOMPATIBLE
                reason = (
                    f"Model needs {req_vram:.0f} GB VRAM / {req_ram:.0f} GB RAM; "
                    f"only {avail_vram:.0f} GB VRAM / {avail_ram:.0f} GB RAM available."
                )
        else:
            label  = ModelCompatibilityLabel.COMPATIBLE
            reason = f"Fits in GPU VRAM ({avail_vram:.0f} GB available)."
    elif avail_vram == 0 and req_vram > 0:
        # No GPU detected
        if req_ram <= avail_ram * 0.85:
            label  = ModelCompatibilityLabel.DEGRADED
            reason = (
                f"No GPU detected — will run on CPU only (slow). "
                f"RAM: {avail_ram:.0f} GB available ≥ {req_ram:.0f} GB required."
            )
        else:
            label  = ModelCompatibilityLabel.INCOMPATIBLE
            reason = (
                f"No GPU and insufficient RAM: {avail_ram:.0f} GB < {req_ram:.0f} GB required."
            )
    else:
        # Embedding or CPU-only model
        if req_ram <= avail_ram * 0.9:
            label  = ModelCompatibilityLabel.COMPATIBLE
            reason = f"CPU model — RAM {avail_ram:.0f} GB ≥ {req_ram:.0f} GB required."
        else:
            label  = ModelCompatibilityLabel.INCOMPATIBLE
            reason = (
                f"Insufficient RAM: {avail_ram:.0f} GB < {req_ram:.0f} GB required."
            )

    return ModelCompatibility(
        model=model_name,
        label=label,
        reason=reason,
        ram_required_gb=req_ram,
        vram_required_gb=req_vram,
        ram_available_gb=avail_ram,
        vram_available_gb=avail_vram,
    )


def get_compatibility_label(model_name: str, profile: HardwareProfile | None = None) -> ModelCompatibilityLabel:
    """Quick helper — returns just the label."""
    if profile is None:
        profile = get_hardware_profile()
    return check_model_compatibility(model_name, profile).label


# ── Hardware detection ─────────────────────────────────────────────────────────

def _detect_cpu() -> tuple[str, int, int]:
    """Return (model_name, physical_cores, logical_threads)."""
    try:
        import cpuinfo  # optional: pip install py-cpuinfo
        info = cpuinfo.get_cpu_info()
        brand = info.get("brand_raw", platform.processor() or "Unknown CPU")
    except Exception:
        brand = platform.processor() or "Unknown CPU"
    cores   = psutil.cpu_count(logical=False) or 1
    threads = psutil.cpu_count(logical=True)  or 1
    return brand, cores, threads


def _detect_ram() -> tuple[float, float]:
    """Return (total_gb, available_gb)."""
    vm = psutil.virtual_memory()
    return vm.total / 1e9, vm.available / 1e9


def _detect_nvidia_gpus() -> list[GPUDevice]:
    """Query nvidia-smi for VRAM info."""
    devices: list[GPUDevice] = []
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=index,name,memory.total,driver_version",
                "--format=csv,noheader,nounits",
            ],
            timeout=5,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        for line in out.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 4:
                continue
            idx, name, vram_mib, driver = parts[0], parts[1], parts[2], parts[3]
            devices.append(GPUDevice(
                index=int(idx),
                name=name,
                vram_gb=float(vram_mib) / 1024.0,
                vendor="nvidia",
                driver=driver,
            ))
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass
    return devices


def _detect_amd_gpus() -> list[GPUDevice]:
    """Query rocm-smi for AMD VRAM info."""
    devices: list[GPUDevice] = []
    try:
        out = subprocess.check_output(
            ["rocm-smi", "--showmeminfo", "vram", "--json"],
            timeout=5,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        data = json.loads(out)
        for idx, (card, info) in enumerate(data.items()):
            vram_bytes = int(info.get("VRAM Total Memory (B)", 0))
            name       = info.get("Card SKU", f"AMD GPU {idx}")
            devices.append(GPUDevice(
                index=idx,
                name=name,
                vram_gb=vram_bytes / 1e9,
                vendor="amd",
            ))
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        pass
    return devices


def _detect_apple_silicon_gpu() -> list[GPUDevice]:
    """On Apple Silicon, unified memory is shared — return an estimate."""
    if platform.system() != "Darwin":
        return []
    try:
        import subprocess as sp
        out = sp.check_output(
            ["system_profiler", "SPHardwareDataType", "-json"],
            timeout=5, stderr=sp.DEVNULL, text=True,
        )
        data = json.loads(out)
        hw = data.get("SPHardwareDataType", [{}])[0]
        chip_type = hw.get("chip_type", "")
        machine   = hw.get("machine_model", "")
        # Apple Silicon MPS can use all unified memory; practical limit is ~75%
        vm = psutil.virtual_memory()
        usable_vram_gb = (vm.total / 1e9) * 0.75
        if any(x in chip_type for x in ("M1", "M2", "M3", "M4")):
            return [GPUDevice(
                index=0,
                name=f"Apple {chip_type} (Unified Memory)",
                vram_gb=usable_vram_gb,
                vendor="apple",
                driver="Metal",
            )]
    except Exception:
        pass
    return []


def _detect_intel_arc_gpu() -> list[GPUDevice]:
    """Attempt Intel Arc GPU detection via sycl-ls or xpu-smi."""
    devices: list[GPUDevice] = []
    try:
        out = subprocess.check_output(
            ["xpu-smi", "discovery", "--json"],
            timeout=5, stderr=subprocess.DEVNULL, text=True,
        )
        data = json.loads(out)
        for d in data.get("device_list", []):
            mem_mib = d.get("device_memory_physical_size_byte", 0) / (1024 * 1024)
            devices.append(GPUDevice(
                index=d.get("device_id", 0),
                name=d.get("device_name", "Intel Arc GPU"),
                vram_gb=mem_mib / 1024.0,
                vendor="intel",
            ))
    except Exception:
        pass
    return devices


def detect_hardware() -> HardwareProfile:
    """Detect all hardware on the host machine.

    Never raises — returns a profile with safe defaults if any detection fails.
    """
    cpu_model, cpu_cores, cpu_threads = _detect_cpu()
    ram_total, ram_available          = _detect_ram()

    gpus: list[GPUDevice] = []
    gpus.extend(_detect_nvidia_gpus())
    if not gpus:
        gpus.extend(_detect_amd_gpus())
    if not gpus:
        gpus.extend(_detect_apple_silicon_gpu())
    if not gpus:
        gpus.extend(_detect_intel_arc_gpu())

    return HardwareProfile(
        cpu_model=cpu_model,
        cpu_cores=cpu_cores,
        cpu_threads=cpu_threads,
        ram_total_gb=ram_total,
        ram_available_gb=ram_available,
        gpus=gpus,
        platform=platform.platform(),
    )


# ── Cached singleton ──────────────────────────────────────────────────────────

_PROFILE: HardwareProfile | None = None
_PROFILE_TTL = 300.0   # re-detect every 5 min (RAM availability changes)


def get_hardware_profile(force_refresh: bool = False) -> HardwareProfile:
    """Return the cached hardware profile, refreshing if stale."""
    global _PROFILE
    now = time.time()
    if (
        _PROFILE is None
        or force_refresh
        or (now - _PROFILE.detected_at) > _PROFILE_TTL
    ):
        _PROFILE = detect_hardware()
        log.info(
            "Hardware detected: %s, %.0f GB RAM, %.0f GB VRAM (%d GPU(s))",
            _PROFILE.cpu_model,
            _PROFILE.ram_total_gb,
            _PROFILE.total_vram_gb,
            len(_PROFILE.gpus),
        )
    return _PROFILE


# ── FastAPI router ─────────────────────────────────────────────────────────────

hardware_router = APIRouter(prefix="/api/hardware", tags=["hardware"])


@hardware_router.get("/profile")
async def get_hardware_profile_endpoint():
    """Return the current machine's hardware profile."""
    profile = await asyncio.get_event_loop().run_in_executor(None, get_hardware_profile)
    return profile.as_dict()


@hardware_router.get("/profile/refresh")
async def refresh_hardware_profile():
    """Force re-detection of hardware (useful after hardware changes)."""
    profile = await asyncio.get_event_loop().run_in_executor(
        None, functools.partial(get_hardware_profile, force_refresh=True)
    )
    return profile.as_dict()


@hardware_router.get("/compatibility/{model_name:path}")
async def model_compatibility(model_name: str):
    """Check if a specific model is compatible with this machine."""
    profile = await asyncio.get_event_loop().run_in_executor(None, get_hardware_profile)
    compat  = check_model_compatibility(model_name, profile)
    return compat.as_dict()


@hardware_router.post("/compatibility/batch")
async def batch_compatibility(body: dict):
    """Check compatibility for multiple models at once.

    Body: {"models": ["model1", "model2", ...]}
    """
    models  = body.get("models", [])
    profile = await asyncio.get_event_loop().run_in_executor(None, get_hardware_profile)
    results = []
    for m in models:
        compat = check_model_compatibility(str(m), profile)
        results.append(compat.as_dict())
    return {"hardware": profile.as_dict(), "compatibility": results}
