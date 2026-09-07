import pytest
import sys
from unittest.mock import patch, MagicMock
from services.hardware_detector import get_available_memory_mb, FALLBACK_MEMORY_MB

class TestHardwareDetector:
    
    def test_nvidia_gpu_detected(self):
        """測試 NVIDIA GPU 偵測成功的情境"""
        mock_pynvml = MagicMock()
        mock_pynvml.nvmlDeviceGetCount.return_value = 1
        
        # 模擬 8GB VRAM
        mock_info = MagicMock()
        mock_info.free = 8 * 1024 * 1024 * 1024
        mock_pynvml.nvmlDeviceGetMemoryInfo.return_value = mock_info
        
        with patch.dict("sys.modules", {"pynvml": mock_pynvml}):
            result = get_available_memory_mb()
            
            assert result == 8192.0
            mock_pynvml.nvmlInit.assert_called_once()
            mock_pynvml.nvmlShutdown.assert_called_once()

    def test_psutil_fallback_when_pynvml_fails(self):
        """測試沒有 NVIDIA GPU 或 pynvml 報錯時，成功降級使用 psutil 偵測系統 RAM"""
        mock_pynvml = MagicMock()
        mock_pynvml.nvmlInit.side_effect = ImportError("No module named pynvml")
        
        mock_psutil = MagicMock()
        # 模擬 16GB System RAM available
        mock_mem_info = MagicMock()
        mock_mem_info.available = 16 * 1024 * 1024 * 1024
        mock_psutil.virtual_memory.return_value = mock_mem_info
        
        with patch.dict("sys.modules", {"pynvml": mock_pynvml, "psutil": mock_psutil}):
            result = get_available_memory_mb()
            
            assert result == 16384.0
            mock_psutil.virtual_memory.assert_called_once()

    def test_complete_fallback(self):
        """測試 pynvml 和 psutil 皆失敗時，回傳最保守的預設值"""
        mock_pynvml = MagicMock()
        mock_pynvml.nvmlInit.side_effect = Exception("pynvml crash")
        
        mock_psutil = MagicMock()
        mock_psutil.virtual_memory.side_effect = Exception("psutil crash")
        
        with patch.dict("sys.modules", {"pynvml": mock_pynvml, "psutil": mock_psutil}):
            result = get_available_memory_mb()
            
            assert result == FALLBACK_MEMORY_MB
