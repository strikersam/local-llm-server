"""hardware/ — Hardware detection and model compatibility module."""

from hardware.detector import (
    HardwareProfile,
    ModelCompatibility,
    ModelCompatibilityLabel,
    detect_hardware,
    get_hardware_profile,
    check_model_compatibility,
    get_compatibility_label,
    hardware_router,
)

__all__ = [
    "HardwareProfile",
    "ModelCompatibility",
    "ModelCompatibilityLabel",
    "detect_hardware",
    "get_hardware_profile",
    "check_model_compatibility",
    "get_compatibility_label",
    "hardware_router",
]
