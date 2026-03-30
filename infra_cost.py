"""
Local infrastructure cost model for true TCO analysis.

This module computes the *real* cost of running an inference request on local
hardware — electricity consumed, amortised hardware cost, and storage overhead.
These values are emitted alongside the commercial-equivalent estimate in Langfuse,
giving you an honest break-even comparison versus AWS Bedrock or any cloud API.

Configuration (all via environment variables, with sensible defaults):

    INFRA_GPU_ACTIVE_WATTS    GPU power draw during active inference (W)
    INFRA_GPU_IDLE_WATTS      GPU power draw when loaded but idle (W)
    INFRA_SYSTEM_WATTS        CPU + RAM + storage overhead (W)
    INFRA_ELECTRICITY_USD_KWH Electricity cost in USD per kWh
    INFRA_HARDWARE_COST_USD   Total hardware cost to amortise (USD)
    INFRA_AMORTIZATION_MONTHS Amortisation period (months)
    INFRA_MODEL_STORAGE_GB    Model file size on disk (GB) [informational]
    INFRA_STORAGE_USD_GB_MO   Storage cost per GB per month (USD)

Measurement guidance:
  - GPU watts:    GPU-Z, nvidia-smi dmon, or HWiNFO64 during inference
  - System watts: Wall-meter (smart plug like TP-Link Kasa) during a 30min run
  - Electricity:  Check your electricity bill (kWh rate)
  - Hardware:     Purchase price (don't forget SSD and RAM if dedicated)
"""

from __future__ import annotations

import os
from dataclasses import dataclass


# ─── Configuration ─────────────────────────────────────────────────────────────

def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, "").strip() or default)
    except (ValueError, TypeError):
        return default


@dataclass(frozen=True)
class InfraConfig:
    # Power draw
    gpu_active_watts: float   # GPU during active inference
    gpu_idle_watts: float     # GPU when model loaded, no request
    system_watts: float       # CPU + RAM + storage overhead

    # Electricity
    electricity_usd_kwh: float

    # Hardware amortization
    hardware_cost_usd: float
    amortization_months: float

    # Storage (informational / per-request)
    model_storage_gb: float
    storage_usd_gb_month: float

    @property
    def total_active_watts(self) -> float:
        return self.gpu_active_watts + self.system_watts

    @property
    def total_idle_watts(self) -> float:
        return self.gpu_idle_watts + self.system_watts

    @property
    def hardware_cost_per_second(self) -> float:
        """Amortised hardware cost in USD per second of operation."""
        amort_seconds = self.amortization_months * 30 * 24 * 3600
        return self.hardware_cost_usd / amort_seconds if amort_seconds > 0 else 0.0


def load_infra_config() -> InfraConfig:
    """Load infrastructure config from environment variables.

    All values have conservative defaults suitable for a mid-range gaming PC.
    For Intel AI PC (Arc iGPU): set gpu_active_watts ~ 30-50 and system_watts ~ 25.
    For RTX 4090: set gpu_active_watts ~ 250 and system_watts ~ 80.
    """
    return InfraConfig(
        gpu_active_watts=_float_env("INFRA_GPU_ACTIVE_WATTS", 150.0),
        gpu_idle_watts=_float_env("INFRA_GPU_IDLE_WATTS", 20.0),
        system_watts=_float_env("INFRA_SYSTEM_WATTS", 50.0),
        electricity_usd_kwh=_float_env("INFRA_ELECTRICITY_USD_KWH", 0.12),
        hardware_cost_usd=_float_env("INFRA_HARDWARE_COST_USD", 2000.0),
        amortization_months=_float_env("INFRA_AMORTIZATION_MONTHS", 36.0),
        model_storage_gb=_float_env("INFRA_MODEL_STORAGE_GB", 20.0),
        storage_usd_gb_month=_float_env("INFRA_STORAGE_USD_GB_MO", 0.023),
    )


_CONFIG: InfraConfig | None = None


def get_infra_config() -> InfraConfig:
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = load_infra_config()
    return _CONFIG


# ─── Cost calculation ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RequestInfraCost:
    electricity_usd: float      # Electricity for this request
    hardware_usd: float         # Amortised hardware for this request
    total_usd: float            # Electricity + hardware
    energy_kwh: float           # Energy consumed
    inference_seconds: float    # Wall-clock inference time

    def as_dict(self) -> dict[str, float]:
        return {
            "infra_electricity_usd": round(self.electricity_usd, 8),
            "infra_hardware_usd": round(self.hardware_usd, 8),
            "infra_total_usd": round(self.total_usd, 8),
            "infra_energy_kwh": round(self.energy_kwh, 8),
            "infra_inference_seconds": round(self.inference_seconds, 3),
        }


def compute_request_cost(latency_ms: int) -> RequestInfraCost:
    """Compute infrastructure cost for a single request given its latency."""
    cfg = get_infra_config()
    inference_seconds = latency_ms / 1000.0

    # Electricity: (watts * seconds) / 3600 / 1000 = kWh
    energy_kwh = (cfg.total_active_watts * inference_seconds) / 3_600_000
    electricity_usd = energy_kwh * cfg.electricity_usd_kwh

    # Amortised hardware
    hardware_usd = cfg.hardware_cost_per_second * inference_seconds

    total_usd = electricity_usd + hardware_usd

    return RequestInfraCost(
        electricity_usd=electricity_usd,
        hardware_usd=hardware_usd,
        total_usd=total_usd,
        energy_kwh=energy_kwh,
        inference_seconds=inference_seconds,
    )


# ─── Session and aggregate cost projections ────────────────────────────────────

@dataclass(frozen=True)
class SessionCostProjection:
    """Estimated cost for a typical coding session and daily/monthly projections."""
    cost_per_session_usd: float
    daily_cost_usd: float          # at sessions_per_day
    monthly_cost_usd: float
    idle_cost_per_hour_usd: float
    breakeven_vs_bedrock_months: float | None

    def summary(self, sessions_per_day: int = 8) -> str:
        lines = [
            f"Local infra cost estimate (assumptions — measure to refine):",
            f"  Per session:    ${self.cost_per_session_usd:.4f}",
            f"  Daily ({sessions_per_day} sess): ${self.daily_cost_usd:.4f}",
            f"  Monthly:        ${self.monthly_cost_usd:.4f}",
            f"  Idle per hour:  ${self.idle_cost_per_hour_usd:.5f}",
        ]
        if self.breakeven_vs_bedrock_months is not None:
            lines.append(
                f"  Break-even vs Bedrock Claude 3.5 Sonnet: "
                f"{self.breakeven_vs_bedrock_months:.1f} months"
            )
        return "\n".join(lines)


def project_session_cost(
    avg_session_latency_ms: int = 120_000,
    sessions_per_day: int = 8,
    bedrock_cost_per_session_usd: float = 0.24,
) -> SessionCostProjection:
    """
    Project costs for a typical coding session.

    Args:
        avg_session_latency_ms: Total active inference time per session (ms).
                                 120s = a 40-turn session with ~3s per turn average.
        sessions_per_day:       How many coding sessions per working day.
        bedrock_cost_per_session_usd: Reference Bedrock cost to compute break-even.
                                       $0.24 = Claude 3.5 Sonnet at ~20K input + 12K output tokens.
    """
    cfg = get_infra_config()
    session_cost = compute_request_cost(avg_session_latency_ms)
    daily = session_cost.total_usd * sessions_per_day
    monthly = daily * 30

    idle_kwh_per_hour = (cfg.total_idle_watts) / 1000
    idle_per_hour = idle_kwh_per_hour * cfg.electricity_usd_kwh

    bedrock_monthly = bedrock_cost_per_session_usd * sessions_per_day * 30
    local_monthly = monthly
    monthly_savings = bedrock_monthly - local_monthly
    if monthly_savings > 0:
        breakeven = cfg.hardware_cost_usd / monthly_savings
    else:
        breakeven = None

    return SessionCostProjection(
        cost_per_session_usd=session_cost.total_usd,
        daily_cost_usd=daily,
        monthly_cost_usd=monthly,
        idle_cost_per_hour_usd=idle_per_hour,
        breakeven_vs_bedrock_months=breakeven,
    )


if __name__ == "__main__":
    cfg = get_infra_config()
    print("=== Infrastructure Config ===")
    print(f"  GPU active: {cfg.gpu_active_watts}W  idle: {cfg.gpu_idle_watts}W")
    print(f"  System:     {cfg.system_watts}W")
    print(f"  Total active: {cfg.total_active_watts}W")
    print(f"  Electricity: ${cfg.electricity_usd_kwh}/kWh")
    print(f"  Hardware: ${cfg.hardware_cost_usd} over {cfg.amortization_months} months")
    print()
    proj = project_session_cost()
    print(proj.summary())
