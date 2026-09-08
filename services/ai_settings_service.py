import json
import os
from services.app_settings_service import AppSettingsService

SETTINGS_FILENAME = "ai_settings.json"

DEFAULT_SETTINGS = {
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
    "prompts": {
        "impression": "你是一位專業的小說編輯與文學評論家。請閱讀以下小說文本，分析其整體基調、文學風格、敘事結構、核心主題與情節張力，並提供具體的寫作最佳化建議。",
        "character": "你是一位專業的小說角色分析師。請閱讀以下小說文本，為文本中登場的每一位角色獨立建立詳細角色設定，並在最後梳理一份獨立的角色關係網。\n\n請嚴格依下列結構化標籤輸出：\n===CHARACTER_START===\n【角色姓名】角色名字\n【外觀年齡】外觀推測年齡（例如：約 20~25 歲青年）\n【外觀特徵】文字中猜測或描寫的外貌特徵、著裝與氣質神態\n【人物側寫】個性、核心人格特質、價值觀與人物小傳\n【已知行動】在選定範圍內已知的具體行動軌跡與事蹟\n【人事物關聯】與該角色有關係的人、事、物（請使用直觀繁體中文或「⟷」、「➔」表達關聯，嚴禁輸出 LaTeX 語法如 $\\leftrightarrow$、$\\rightarrow$ 等）\n===CHARACTER_END===\n（有多位角色時請重複輸出上述 ===CHARACTER_START=== 區塊）\n\n===RELATIONSHIP_START===\n【卡片標題】全景角色關係網梳理\n【關係梳理】陣營勢力、角色間的核心矛盾、情感牽絆與互動脈絡深度分析（關聯請使用「⟷」、「➔」或文字說明，嚴禁使用 LaTeX 數學符號）\n===RELATIONSHIP_END===",
        "world": "你是一位小說世界觀架構師。請閱讀以下小說文本，分析並提取出文本中涉及的世界觀設定、歷史背景、地理環境、勢力組織、力量體系或特殊術語，並進行系統化的整理。",
        "timeline": "你是一位專業的小說時間線規劃師。請閱讀以下小說文本，梳理出故事發生的時間線，按先後順序提取出關鍵事件、場景轉換及發生的具體時間節點。",
        "chat": "你是一位資深的小說寫作顧問與編輯助手。請以繁體中文與作者深入探討小說情節、人物塑造、世界觀設定、伏筆鋪陳與文字潤飾，提供具創意且具體可行的寫作建議。",
        "continuation": "你是一位小說創作者助手。請根據上方提供的小說上文情節、語氣與人物性格，緊接著自然續寫故事段落。請直接輸出續寫的小說正文，不要包含任何開場白、問候語、解釋或標題。"
    }
}


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
                    merged = dict(DEFAULT_SETTINGS)
                    for k, v in data.items():
                        if isinstance(v, dict) and k in merged:
                            merged[k].update(v)
                        else:
                            merged[k] = v
                    return merged
            except Exception as e:
                print(f"讀取 AI 設定檔失敗: {e}")
        return dict(DEFAULT_SETTINGS)

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
