"""tests/test_hardware.py — Unit tests for the hardware detection module."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from hardware.detector import (
    HardwareProfile,
    GPUDevice,
    ModelCompatibility,
    ModelCompatibilityLabel,
    check_model_compatibility,
    get_compatibility_label,
    _lookup_requirements,
)


# ── Fixture: profile helpers ──────────────────────────────────────────────────

def _make_profile(ram_gb=32.0, vram_gb=24.0, gpus=1) -> HardwareProfile:
    gpu_list = [
        GPUDevice(index=0, name="NVIDIA RTX 4090", vram_gb=vram_gb, vendor="nvidia")
    ] if gpus > 0 else []
    return HardwareProfile(
        cpu_model="Intel Core i9-13900K",
        cpu_cores=24,
        cpu_threads=32,
        ram_total_gb=ram_gb,
        ram_available_gb=ram_gb * 0.7,
        gpus=gpu_list,
        platform="Linux-6.1",
    )


# ── Requirement lookup ─────────────────────────────────────────────────────────

class TestModelRequirements:

    def test_llama3_8b_spec(self):
        spec = _lookup_requirements("llama3:8b")
        assert spec["ram_gb"] >= 6
        assert spec["vram_gb"] >= 4

    def test_qwen3_coder_30b(self):
        spec = _lookup_requirements("qwen3-coder:30b")
        assert spec["ram_gb"] >= 20
        assert spec["vram_gb"] >= 16

    def test_deepseek_r1_32b(self):
        spec = _lookup_requirements("deepseek-r1:32b")
        assert spec["ram_gb"] >= 24
        assert spec["vram_gb"] >= 20

    def test_unknown_model_gets_default(self):
        spec = _lookup_requirements("my-custom-model:latest")
        assert spec["ram_gb"] > 0

    def test_generic_param_size_parsing(self):
        spec = _lookup_requirements("some-model:70b")
        assert spec.get("param_b") == 70 or spec["ram_gb"] >= 40


# ── Compatibility checks ───────────────────────────────────────────────────────

class TestModelCompatibility:

    def test_small_model_on_rtx4090_is_compatible(self):
        profile = _make_profile(ram_gb=64, vram_gb=24)
        compat  = check_model_compatibility("llama3:8b", profile)
        assert compat.label == ModelCompatibilityLabel.COMPATIBLE

    def test_large_model_exceeds_vram_is_degraded(self):
        profile = _make_profile(ram_gb=64, vram_gb=4)
        compat  = check_model_compatibility("deepseek-r1:70b", profile)
        assert compat.label in (ModelCompatibilityLabel.DEGRADED, ModelCompatibilityLabel.INCOMPATIBLE)

    def test_huge_model_exceeds_all_memory_is_incompatible(self):
        profile = _make_profile(ram_gb=16, vram_gb=8)
        compat  = check_model_compatibility("llama3.1:405b", profile)
        assert compat.label == ModelCompatibilityLabel.INCOMPATIBLE

    def test_no_gpu_cpu_fallback_gives_degraded(self):
        profile = _make_profile(ram_gb=32, vram_gb=0, gpus=0)
        compat  = check_model_compatibility("llama3:8b", profile)
        assert compat.label in (ModelCompatibilityLabel.COMPATIBLE, ModelCompatibilityLabel.DEGRADED)

    def test_no_gpu_not_enough_ram_is_incompatible(self):
        profile = _make_profile(ram_gb=4, vram_gb=0, gpus=0)
        compat  = check_model_compatibility("deepseek-r1:32b", profile)
        assert compat.label == ModelCompatibilityLabel.INCOMPATIBLE

    def test_compatibility_has_reason(self):
        profile = _make_profile(ram_gb=64, vram_gb=24)
        compat  = check_model_compatibility("qwen3-coder:30b", profile)
        assert len(compat.reason) > 0

    def test_as_dict_has_required_fields(self):
        profile = _make_profile()
        compat  = check_model_compatibility("mistral:7b", profile)
        d = compat.as_dict()
        assert "label" in d
        assert "reason" in d
        assert "ram_required_gb" in d
        assert "vram_required_gb" in d

    def test_get_compatibility_label_helper(self):
        profile = _make_profile(ram_gb=64, vram_gb=24)
        label   = get_compatibility_label("llama3:8b", profile)
        assert isinstance(label, ModelCompatibilityLabel)


# ── HardwareProfile ────────────────────────────────────────────────────────────

class TestHardwareProfile:

    def test_total_vram_sums_gpus(self):
        gpus = [GPUDevice(0, "RTX 4090", 24.0, "nvidia"), GPUDevice(1, "RTX 4090", 24.0, "nvidia")]
        profile = HardwareProfile("Intel", 8, 16, 64.0, 48.0, gpus=gpus, platform="test")
        assert profile.total_vram_gb == 48.0

    def test_has_gpu_true_when_gpus_present(self):
        gpus    = [GPUDevice(0, "RTX 3080", 10.0, "nvidia")]
        profile = HardwareProfile("AMD", 6, 12, 32.0, 20.0, gpus=gpus, platform="test")
        assert profile.has_gpu is True

    def test_has_gpu_false_when_no_gpus(self):
        profile = HardwareProfile("Intel", 4, 8, 16.0, 12.0, gpus=[], platform="test")
        assert profile.has_gpu is False

    def test_as_dict_has_required_fields(self):
        profile = _make_profile()
        d = profile.as_dict()
        assert "cpu_model" in d
        assert "ram_total_gb" in d
        assert "total_vram_gb" in d
        assert "has_gpu" in d
        assert "gpus" in d
        assert isinstance(d["gpus"], list)
