import copy
import json
import os
from services.app_settings_service import AppSettingsService

SETTINGS_FILENAME = "ai_settings.json"

DEFAULT_SETTINGS_BASE = {
    "provider": "Ollama",
    "timeout": 300,
    "api_keys": {
        "Ollama": "",
        "LM Studio": ""
    },
    "api_urls": {
        "Ollama": "http://localhost:11434/api/chat",
        "LM Studio": "http://localhost:1234/v1/chat/completions"
    },
    "models": {
        "Ollama": "qwen2.5:7b",
        "LM Studio": "local-model"
    },
    "context_limits": {
        "Ollama": 8192,
        "LM Studio": 8192
    },
}


def get_default_settings() -> dict:
    return copy.deepcopy(DEFAULT_SETTINGS_BASE)


DEFAULT_SETTINGS = get_default_settings()


class AISettingsService:
    """管理本機 AI 校稿功能之設定檔讀寫。"""

    @classmethod
    def get_settings_file_path(cls, custom_dir: str = None) -> str:
        """取得本機儲存 AI 設定檔的完整絕對路徑（預設在 AppData/Local/Jiufang_Novel_Editor/）。"""
        if not custom_dir:
            custom_dir = AppSettingsService.get_default_storage_path()
        if not os.path.exists(custom_dir):
            try:
                os.makedirs(custom_dir, exist_ok=True)
            except Exception:
                pass
        return os.path.join(custom_dir, SETTINGS_FILENAME)

    @classmethod
    def load_settings(cls, file_path: str = None) -> dict:
        target_path = file_path if file_path else cls.get_settings_file_path()

        # 若 AppData 路徑檔案不存在，但當前目錄有舊版 ai_settings.json，自動遷移
        if not file_path and not os.path.exists(target_path):
            legacy_path = SETTINGS_FILENAME
            if os.path.exists(legacy_path):
                try:
                    with open(legacy_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    cls.save_settings(data, file_path=target_path)
                except Exception as e:
                    print(f"自動遷移舊版 AI 設定檔失敗: {e}")

        if os.path.exists(target_path):
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # 合併預設值避免缺欄位
                    merged = get_default_settings()
                    for k, v in data.items():
                        if isinstance(v, dict) and k in merged:
                            merged[k].update(v)
                        else:
                            merged[k] = v
                    return merged
            except Exception as e:
                print(f"讀取 AI 設定檔失敗: {e}")
        return get_default_settings()

    @classmethod
    def save_settings(cls, settings: dict, file_path: str = None):
        target_path = file_path if file_path else cls.get_settings_file_path()
        try:
            target_dir = os.path.dirname(target_path)
            if target_dir and not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"儲存 AI 設定檔失敗: {e}")
