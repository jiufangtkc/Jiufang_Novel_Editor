"""
Hardware Detector Service
專責判斷當下可用記憶體的模組，區分 NVIDIA 獨立顯卡與 Intel UMA 內顯環境。
此模組在長文分析「啟動前」進行一次性的快照偵測（Snapshot）。
"""

import logging

logger = logging.getLogger(__name__)

# Fallback 預設記憶體 (MB)，給予未知環境最保守的預設值 (4GB)
FALLBACK_MEMORY_MB = 4096.0

def get_available_memory_mb() -> float:
    """
    偵測系統可用的記憶體 (MB)。
    優先順序：
    1. NVIDIA GPU VRAM (透過 pynvml)
    2. System RAM (供 UMA架構 / Intel Arc 等使用，透過 psutil)
    3. Fallback (4096 MB)
    
    Returns:
        float: 可用記憶體大小，單位為 MB。
    """
    
    # 嘗試偵測 NVIDIA GPU VRAM
    try:
        import pynvml
        pynvml.nvmlInit()
        
        try:
            # 取得系統上的 NVIDIA 顯卡數量
            device_count = pynvml.nvmlDeviceGetCount()
            
            if device_count > 0:
                # 預設抓取第一張顯卡 (index 0)
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                
                # byte 轉 MB
                available_vram_mb = info.free / (1024 * 1024)
                logger.info(f"偵測到 NVIDIA GPU，可用 VRAM: {available_vram_mb:.2f} MB")
                
                return available_vram_mb
        finally:
            # 清理，無論是否有偵測到 GPU 或發生例外，都必須關閉以避免 handle leak 造成系統卡頓
            pynvml.nvmlShutdown()
            
    except ImportError:
        logger.debug("未安裝 pynvml 套件，跳過 NVIDIA GPU 偵測。")
    except Exception as e:
        logger.warning(f"pynvml 偵測 NVIDIA GPU 失敗: {e}，切換為系統記憶體偵測。")

    # 嘗試偵測 System RAM (UMA/Intel/AMD APU)
    try:
        import psutil
        # virtual_memory() 返回的 available 是系統當下可配置給應用程式的記憶體位元組數
        mem_info = psutil.virtual_memory()
        available_ram_mb = mem_info.available / (1024 * 1024)
        logger.info(f"偵測系統可用 RAM (供 UMA/CPU 推論參考): {available_ram_mb:.2f} MB")
        return available_ram_mb
        
    except ImportError:
        logger.debug("未安裝 psutil 套件，跳過系統 RAM 偵測。")
    except Exception as e:
        logger.warning(f"psutil 偵測系統 RAM 失敗: {e}。")

    # Fallback
    logger.warning(f"無法偵測硬體可用記憶體，採用最保守預設值: {FALLBACK_MEMORY_MB} MB")
    return FALLBACK_MEMORY_MB
