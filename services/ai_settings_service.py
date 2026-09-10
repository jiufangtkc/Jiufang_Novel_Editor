import json
import os
from services.app_settings_service import AppSettingsService

SETTINGS_FILENAME = "ai_settings.json"

DEFAULT_SETTINGS_BASE = {
    "provider": "Google",
    "timeout": 300,
    "ai_continuation_enabled": False,
    "ai_continuation_agreed": False,
    "api_keys": {
        "OpenAI": "",
        "Google": "",
        "Anthropic": "",
        "Grok": "",
        "Ollama": "",
        "LM Studio": ""
    },
    "api_urls": {
        "OpenAI": "https://api.openai.com/v1/chat/completions",
        "Google": "https://generativelanguage.googleapis.com/v1beta/openai/v1/chat/completions",
        "Anthropic": "https://api.anthropic.com/v1/messages",
        "Grok": "https://api.x.ai/v1/chat/completions",
        "Ollama": "http://localhost:11434/api/chat",
        "LM Studio": "http://localhost:1234/v1/chat/completions"
    },
    "models": {
        "OpenAI": "gpt-4o",
        "Google": "gemini-2.5-flash",
        "Anthropic": "claude-3-5-sonnet-20241022",
        "Grok": "grok-beta",
        "Ollama": "qwen2.5:7b",
        "LM Studio": "local-model"
    },
    "context_limits": {
        "OpenAI": 128000,
        "Google": 1048576,
        "Anthropic": 200000,
        "Grok": 131072,
        "Ollama": 8192,
        "LM Studio": 8192
    },
}

def load_default_prompts() -> dict:
    """從 resources/prompts/ 目錄動態讀取預設的 AI 提示詞模板。"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompts_dir = os.path.join(base_dir, "resources", "prompts")
    prompts = {
        "impression": "",
        "character": "",
        "world": "",
        "timeline": "",
        "chat": "",
        "continuation": ""
    }
    for key in prompts.keys():
        file_path = os.path.join(prompts_dir, f"{key}.txt")
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    prompts[key] = f.read().strip()
            except Exception as e:
                print(f"載入預設 Prompt 失敗 ({key}.txt): {e}")
    return prompts

def get_default_settings() -> dict:
    settings = dict(DEFAULT_SETTINGS_BASE)
    settings["prompts"] = load_default_prompts()
    return settings

DEFAULT_SETTINGS = get_default_settings()


class AISettingsService:
    """管理 AI 輔助功能之設定檔讀寫與預設 Prompt 模板。"""

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
