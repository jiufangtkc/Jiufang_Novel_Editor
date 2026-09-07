"""
硬體偵測轉發模組（向後相容）
底層實作已整合至 services/hardware_detector.py。
"""

from services.hardware_detector import get_available_memory_mb as _get_mem_mb


class HardwareDetector:
    """硬體與記憶體狀態偵測相容包裝類別"""

    @staticmethod
    def get_available_memory_mb(hw_type: str = "nvidia") -> int:
        return int(_get_mem_mb())

