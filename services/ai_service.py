import json
import os
import urllib.request
import urllib.error
import urllib.parse
from PyQt6.QtCore import QThread, pyqtSignal

SETTINGS_FILE = "ai_settings.json"

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
    "prompts": {
        "impression": "你是一位專業的小說編輯與文學評論家。請閱讀以下小說文本，分析其整體基調、文學風格、敘事結構、核心主題與情節張力，並提供具體的寫作最佳化建議。",
        "character": "你是一位專業的小說角色分析師。請閱讀以下小說文本，為文本中登場的每一位角色獨立建立詳細角色設定，並在最後梳理一份獨立的角色關係網。\n\n請嚴格依下列結構化標籤輸出：\n===CHARACTER_START===\n【角色姓名】角色名字\n【外觀年齡】外觀推測年齡（例如：約 20~25 歲青年）\n【外觀特徵】文字中猜測或描寫的外貌特徵、著裝與氣質神態\n【人物側寫】個性、核心人格特質、價值觀與人物小傳\n【已知行動】在選定範圍內已知的具體行動軌跡與事蹟\n【人事物關聯】與該角色有關係的人、事、物（請使用直觀繁體中文或「⟷」、「➔」表達關聯，嚴禁輸出 LaTeX 語法如 $\\leftrightarrow$、$\\rightarrow$ 等）\n===CHARACTER_END===\n（有多位角色時請重複輸出上述 ===CHARACTER_START=== 區塊）\n\n===RELATIONSHIP_START===\n【卡片標題】全景角色關係網梳理\n【關係梳理】陣營勢力、角色間的核心矛盾、情感牽絆與互動脈絡深度分析（關聯請使用「⟷」、「➔」或文字說明，嚴禁使用 LaTeX 數學符號）\n===RELATIONSHIP_END===",
        "world": "你是一位小說世界觀架構師。請閱讀以下小說文本，分析並提取出文本中涉及的世界觀設定、歷史背景、地理環境、勢力組織、力量體系或特殊術語，並進行系統化的整理。",
        "timeline": "你是一位專業的小說時間線規劃師。請閱讀以下小說文本，梳理出故事發生的時間線，按先後順序提取出關鍵事件、場景轉換及發生的具體時間節點。",
        "chat": "你是一位資深的小說寫作顧問與編輯助手。請以繁體中文與作者深入探討小說情節、人物塑造、世界觀設定、伏筆鋪陳與文字潤飾，提供具創意且具體可行的寫作建議。",
        "continuation": "你是一位小說創作者助手。請根據上方提供的小說上文情節、語氣與人物性格，緊接著自然續寫故事段落。請直接輸出續寫的小說正文，不要包含任何開場白、問候語、解釋或標題。"
    }
}


class AIService:
    @staticmethod
    def load_settings(file_path=SETTINGS_FILE) -> dict:
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
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

    @staticmethod
    def save_settings(settings: dict, file_path=SETTINGS_FILE):
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"儲存 AI 設定檔失敗: {e}")

    @classmethod
    def call_api(cls, provider: str, api_url: str, api_key: str, model: str,
                 system_prompt: str = "", user_content: str = "",
                 messages: list = None, timeout=300) -> str:
        """發送請求至 LLM API 並回傳純文字結果（支援單次 prompt 或 messages 多輪歷史）"""
        headers = {"Content-Type": "application/json"}

        # 整理訊息陣列
        if messages is not None and len(messages) > 0:
            formatted_messages = list(messages)
        else:
            formatted_messages = []
            if system_prompt:
                formatted_messages.append({"role": "system", "content": system_prompt})
            if user_content:
                formatted_messages.append({"role": "user", "content": user_content})

        if provider == "Anthropic":
            if api_key:
                headers["x-api-key"] = api_key
            headers["anthropic-version"] = "2023-06-01"

            # Anthropic 需要將 system 獨立提出
            sys_text = ""
            chat_msgs = []
            for m in formatted_messages:
                if m.get("role") == "system":
                    sys_text = m.get("content", "")
                else:
                    chat_msgs.append({"role": m.get("role"), "content": m.get("content")})

            payload = {
                "model": model,
                "max_tokens": 4096,
                "messages": chat_msgs if chat_msgs else [{"role": "user", "content": user_content}]
            }
            if sys_text or system_prompt:
                payload["system"] = sys_text or system_prompt

        elif provider == "Ollama":
            # Ollama /api/chat 格式
            payload = {
                "model": model,
                "messages": formatted_messages,
                "stream": False
            }
        else:
            # OpenAI 相容介面 (Google, Grok, LM Studio, 標準 OpenAI)
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            elif provider == "LM Studio":
                headers["Authorization"] = "Bearer not-needed"

            payload = {
                "model": model or "local-model",
                "messages": formatted_messages
            }

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(api_url, data=req_data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                resp_bytes = response.read()
                resp_json = json.loads(resp_bytes.decode("utf-8"))

                if provider == "Anthropic":
                    contents = resp_json.get("content", [])
                    texts = [c.get("text", "") for c in contents if c.get("type") == "text"]
                    return "\n".join(texts)
                elif provider == "Ollama":
                    return resp_json.get("message", {}).get("content", "")
                else:
                    # OpenAI 相容
                    choices = resp_json.get("choices", [])
                    if choices:
                        msg = choices[0].get("message", {})
                        content = msg.get("content", "")
                        # 若模型為思考型模型且 content 為空，嘗試讀取 reasoning_content
                        if not content and "reasoning_content" in msg:
                            content = msg.get("reasoning_content", "")
                        return content or ""
                    return ""
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"HTTP 錯誤 {e.code}: {err_msg}")
        except urllib.error.URLError as e:
            err_str = str(e.reason)
            if "timed out" in err_str.lower():
                raise RuntimeError(f"連線/生成超時（{timeout} 秒）。本地大型或思考型模型處理耗時較長，請確認服務狀態或調高逾時上限後重試。")
            raise RuntimeError(f"連線失敗: {e.reason}")
        except Exception as e:
            err_str = str(e)
            if "timed out" in err_str.lower():
                raise RuntimeError(f"連線/生成超時（{timeout} 秒）。本地大型或思考型模型處理耗時較長，請確認服務狀態或調高逾時上限後重試。")
            raise RuntimeError(f"API 請求異常: {err_str}")

    @classmethod
    def call_api_stream(cls, provider: str, api_url: str, api_key: str, model: str,
                 system_prompt: str = "", user_content: str = "",
                 messages: list = None, timeout=300):
        """發送請求至 LLM API 並以 Generator 形式回傳文字片段"""
        headers = {"Content-Type": "application/json"}

        # 整理訊息陣列
        if messages is not None and len(messages) > 0:
            formatted_messages = list(messages)
        else:
            formatted_messages = []
            if system_prompt:
                formatted_messages.append({"role": "system", "content": system_prompt})
            if user_content:
                formatted_messages.append({"role": "user", "content": user_content})

        if provider == "Anthropic":
            if api_key:
                headers["x-api-key"] = api_key
            headers["anthropic-version"] = "2023-06-01"

            sys_text = ""
            chat_msgs = []
            for m in formatted_messages:
                if m.get("role") == "system":
                    sys_text = m.get("content", "")
                else:
                    chat_msgs.append({"role": m.get("role"), "content": m.get("content")})

            payload = {
                "model": model,
                "max_tokens": 4096,
                "stream": True,
                "messages": chat_msgs if chat_msgs else [{"role": "user", "content": user_content}]
            }
            if sys_text or system_prompt:
                payload["system"] = sys_text or system_prompt

        elif provider == "Ollama":
            payload = {
                "model": model,
                "messages": formatted_messages,
                "stream": True
            }
        else:
            # OpenAI 相容介面
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            elif provider == "LM Studio":
                headers["Authorization"] = "Bearer not-needed"

            payload = {
                "model": model or "local-model",
                "messages": formatted_messages,
                "stream": True
            }

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(api_url, data=req_data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                for line in response:
                    line = line.decode('utf-8').strip()
                    if not line:
                        continue
                    
                    if provider == "Ollama":
                        try:
                            data = json.loads(line)
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            pass
                    else:
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                if provider == "Anthropic":
                                    if data.get("type") == "content_block_delta":
                                        text = data.get("delta", {}).get("text", "")
                                        if text:
                                            yield text
                                else:
                                    choices = data.get("choices", [])
                                    if choices:
                                        delta = choices[0].get("delta", {})
                                        content = delta.get("content", "")
                                        if content:
                                            yield content
                            except json.JSONDecodeError:
                                pass
        except urllib.error.URLError as e:
            err_str = str(e.reason)
            if "timed out" in err_str.lower():
                raise RuntimeError(f"連線/生成超時（{timeout} 秒）。")
            raise RuntimeError(f"連線失敗: {e.reason}")
        except Exception as e:
            raise RuntimeError(f"串流 API 請求異常: {str(e)}")

    @classmethod
    def test_connection(cls, provider: str, api_url: str, api_key: str, model: str, timeout=90) -> str:
        """測試連線功能"""
        return cls.call_api(
            provider=provider,
            api_url=api_url,
            api_key=api_key,
            model=model,
            system_prompt="你是一個連線測試助手。請直接回答『連線成功。』，無須輸出額外推理過程或多餘文字。",
            user_content="請簡短回答：連線成功。",
            timeout=timeout
        )

    @classmethod
    def detect_local_models(cls, provider: str, api_url: str, timeout=5) -> list[str]:
        """向本地服務（Ollama / LM Studio）端點查詢可用模型清單"""
        if not api_url:
            return []

        parsed = urllib.parse.urlparse(api_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else api_url

        try:
            if provider == "Ollama":
                tags_url = f"{base_url}/api/tags"
                req = urllib.request.Request(tags_url, headers={"User-Agent": "Jiufang-Novel-Editor"})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
                    return models
            elif provider == "LM Studio" or "1234" in api_url or "models" in api_url:
                models_url = f"{base_url}/v1/models"
                req = urllib.request.Request(models_url, headers={"User-Agent": "Jiufang-Novel-Editor"})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
                    return models
            else:
                # 嘗試通用 OpenAI /v1/models 端點
                models_url = f"{base_url}/v1/models"
                req = urllib.request.Request(models_url, headers={"User-Agent": "Jiufang-Novel-Editor"})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
                    return models
        except Exception as e:
            print(f"偵測本機模型失敗 ({provider}): {e}")
            return []

    @classmethod
    def parse_character_extraction_result(cls, raw_text: str, scope_title: str = "") -> dict:
        """
        解析 AI 角色提取結果，將其拆解為個別角色卡與獨立角色關係卡。
        支援 ===CHARACTER_START=== / ===RELATIONSHIP_START=== 結構化標籤與 Markdown 標題 fallback。
        """
        import re

        clean_text = raw_text.strip()
        characters = []
        relationship_card = None

        # 1. 嘗試解析 ===CHARACTER_START=== 區塊
        char_blocks = re.findall(r'===CHARACTER_START===([\s\S]*?)===CHARACTER_END===', clean_text)
        if char_blocks:
            for block in char_blocks:
                c_data = cls._parse_single_character_block(block)
                if c_data:
                    characters.append(c_data)
        else:
            # Fallback 1: 依據 Markdown 標題 (### 或 #### 或 ##) 切分
            # 尋找如 ### 1. 莫庸 或 ### 莫庸 或 #### 莫庸
            sub_sections = re.split(r'\n(?=#{2,4}\s+(?:\d+[\.、\s]+)?(?:[^\n]+))', clean_text)
            for sec in sub_sections:
                sec_clean = sec.strip()
                if not sec_clean:
                    continue
                # 排除純關係網或大標題
                if any(kw in sec_clean[:40] for kw in ["關係網", "角色關係", "總結報告", "登場角色", "主要角色"]):
                    continue
                c_data = cls._parse_fallback_character_block(sec_clean)
                if c_data and c_data.get("name"):
                    characters.append(c_data)

        # 2. 嘗試解析 ===RELATIONSHIP_START=== 區塊
        rel_match = re.search(r'===RELATIONSHIP_START===([\s\S]*?)===RELATIONSHIP_END===', clean_text)
        if rel_match:
            rel_content = rel_match.group(1).strip()
            rel_title = f"【角色關係網】{scope_title}" if scope_title else "【角色關係網】全景梳理"
            title_m = re.search(r'【卡片標題】\s*([^\n]+)', rel_content)
            if title_m:
                rel_title = title_m.group(1).strip()
                rel_content = re.sub(r'【卡片標題】\s*[^\n]+\n*', '', rel_content).strip()

            rel_content = cls.clean_latex_and_symbols(rel_content)
            # 若 rel_content 已有標籤行則不重複添加
            if rel_content.startswith("【標籤】"):
                formatted_rel = rel_content
            else:
                formatted_rel = f"【標籤】#AI角色關係 #關係網\n\n{rel_content}"

            relationship_card = {
                "title": rel_title,
                "content": formatted_rel,
                "tags": ["AI角色關係", "關係網"],
                "summary": rel_content.replace('\n', ' ')[:90] + "...",
                "selected": True
            }
        else:
            # Fallback 2: 尋找文本中提及角色關係的段落
            rel_m = re.search(r'(?:#{2,4}\s*.*?關係.*?\n|【角色關係.*?】)([\s\S]*)', clean_text)
            if rel_m:
                rel_content = rel_m.group(1).strip()
                if rel_content:
                    rel_title = f"【角色關係網】{scope_title}" if scope_title else "【角色關係網】全景梳理"
                    rel_content = cls.clean_latex_and_symbols(rel_content)
                    if rel_content.startswith("【標籤】"):
                        formatted_rel = rel_content
                    else:
                        formatted_rel = f"【標籤】#AI角色關係 #關係網\n\n{rel_content}"

                    relationship_card = {
                        "title": rel_title,
                        "content": formatted_rel,
                        "tags": ["AI角色關係", "關係網"],
                        "summary": rel_content.replace('\n', ' ')[:90] + "...",
                        "selected": True
                    }

        # 若仍無任何角色被解析出，將整篇文本作為一張角色總結卡
        if not characters:
            clean_summary_text = cls.clean_latex_and_symbols(clean_text)
            if clean_summary_text.startswith("【標籤】"):
                formatted_summary = clean_summary_text
            else:
                formatted_summary = f"【標籤】#AI角色 #人物設定\n\n{clean_summary_text}"

            characters.append({
                "name": "登場角色總結",
                "title": f"【角色分析】{scope_title}" if scope_title else "【角色分析】登場人物",
                "age": "詳見內文",
                "appearance": "詳見內文",
                "profile": "詳見內文",
                "actions": "詳見內文",
                "relations": "詳見內文",
                "content": formatted_summary,
                "tags": ["AI角色", "人物設定"],
                "summary": clean_summary_text.replace('\n', ' ')[:90] + "...",
                "selected": True
            })

        return {
            "characters": characters,
            "relationship_card": relationship_card,
            "raw_text": raw_text
        }

    @classmethod
    def clean_latex_and_symbols(cls, text: str) -> str:
        """清理文字中殘留的 LaTeX 數學指令與不友善符號，轉為繁體中文直觀符號"""
        if not text:
            return ""
        import re
        replacements = [
            (r'\$\\leftrightarrow\$|\\leftrightarrow|\$<->\$|<->|<-->', ' ⟷ '),
            (r'\$\\Leftrightarrow\$|\\Leftrightarrow', ' ⟺ '),
            (r'\$\\rightarrow\$|\\rightarrow|\$\\to\$|\\to|(?<=\s)->|(?<=\s)-->', ' ➔ '),
            (r'\$\\leftarrow\$|\\leftarrow|(?<=\s)<-|(?<=\s)<--', ' ← '),
            (r'\$\\Rightarrow\$|\\Rightarrow|(?<=\s)=>|(?<=\s)==>', ' ⇒ '),
            (r'\$\\Leftarrow\$|\\Leftarrow', ' ⇐ '),
            (r'\\cdot|\\bullet', ' • '),
            (r'\\times', ' × '),
        ]
        res = text
        for pat, rep in replacements:
            res = re.sub(pat, rep, res)
        # 移除純文字殘留的行內 $ 符號
        res = re.sub(r'\$([^\$\n]+)\$', r'\1', res)
        return res.strip()

    @classmethod
    def _parse_single_character_block(cls, block_text: str) -> dict:
        import re

        clean = block_text.strip()
        if not clean:
            return None

        def extract_field(field_name, alt_names=None):
            names = [field_name] + (alt_names or [])
            pattern = r'(?:' + '|'.join([re.escape(f'【{n}】') for n in names]) + r')\s*([^\n]+(?:\n(?!【)[^\n]+)*)'
            m = re.search(pattern, clean)
            if m:
                return cls.clean_latex_and_symbols(m.group(1).strip())
            # 支援冒號格式
            pattern_colon = r'(?:' + '|'.join([re.escape(n) for n in names]) + r')[：:]\s*([^\n]+(?:\n(?!【)[^\n]+)*)'
            m_col = re.search(pattern_colon, clean)
            return cls.clean_latex_and_symbols(m_col.group(1).strip()) if m_col else ""

        name = extract_field("角色姓名", ["姓名", "角色名稱", "人物姓名"])
        if not name:
            # 取第一行
            first_line = clean.split('\n')[0].strip()
            name = re.sub(r'^[#\s\d\.、\-\*【】]+', '', first_line).strip("【】:： ")

        age = extract_field("外觀年齡", ["年齡", "推測年齡", "外貌年齡"]) or "未在選定範圍內具體提及"
        appearance = extract_field("外觀特徵", ["外貌", "外貌特徵", "著裝氣質", "外觀描述"]) or "未在選定範圍內具體提及"
        profile = extract_field("人物側寫", ["性格特點", "個性特質", "人物小傳", "側寫與性格"]) or "未在選定範圍內具體提及"
        actions = extract_field("已知行動", ["核心行為", "行為動機", "事件軌跡", "在故事中的行動"]) or "未在選定範圍內具體提及"
        relations = extract_field("人事物關聯", ["關聯人事物", "關係網", "與他有關係的人事物"]) or "未在選定範圍內具體提及"

        card_title = f"【角色】{name}"
        card_content = (
            f"【標籤】#AI角色 #人物設定 #{name}\n\n"
            f"### 【外觀年齡】\n{age}\n\n"
            f"### 【外觀特徵】\n{appearance}\n\n"
            f"### 【人物側寫】\n{profile}\n\n"
            f"### 【已知行動】\n{actions}\n\n"
            f"### 【人事物關聯】\n{relations}"
        )

        return {
            "name": name,
            "title": card_title,
            "age": age,
            "appearance": appearance,
            "profile": profile,
            "actions": actions,
            "relations": relations,
            "content": card_content,
            "tags": ["AI角色", "人物設定", name],
            "summary": f"{age} | {profile[:60]}...",
            "selected": True
        }

    @classmethod
    def _parse_fallback_character_block(cls, block_text: str) -> dict:
        import re

        clean = block_text.strip()
        lines = [line.strip() for line in clean.split('\n') if line.strip()]
        if not lines:
            return None

        # 從標題提取名字
        first_line = lines[0]
        name = re.sub(r'^[#\s\d\.、\-\*]+', '', first_line).strip("【】:： ")
        name = re.sub(r'^(?:角色|主要角色|次要角色)\s*[\d\.、]*\s*', '', name).strip()
        # 移除括號英文如 (Mo Yong)
        name_clean = re.sub(r'\s*\([^)]*\)', '', name).strip()
        if not name_clean or len(name_clean) > 30:
            return None

        def extract_pattern(keywords):
            p = r'(?:' + '|'.join([re.escape(k) for k in keywords]) + r')[：:\s*]+([^\n]+(?:\n(?!\*|\#|\d\.)[^\n]+)*)'
            m = re.search(p, clean)
            return cls.clean_latex_and_symbols(m.group(1).strip()) if m else ""

        age = extract_pattern(["外觀年齡", "年齡", "外貌年齡"]) or "未在選定範圍內具體提及"
        appearance = extract_pattern(["外貌特徵", "外觀特徵", "外貌", "外觀"]) or "未在選定範圍內具體提及"
        profile = extract_pattern(["性格特點", "人物側寫", "性格", "個性"]) or "未在選定範圍內具體提及"
        actions = extract_pattern(["行為動機", "核心行為", "已知行動", "行動"]) or "未在選定範圍內具體提及"
        relations = extract_pattern(["人事物關聯", "關係", "人際關係", "關係網"]) or "未在選定範圍內具體提及"

        # 若完全無欄位匹配，則保留原文本內容
        cleaned_body = cls.clean_latex_and_symbols(clean)
        # 避免重複標籤
        if cleaned_body.startswith("【標籤】"):
            card_content = cleaned_body
        elif appearance == profile == actions == relations == "未在選定範圍內具體提及":
            card_content = f"【標籤】#AI角色 #人物設定 #{name_clean}\n\n{cleaned_body}"
        else:
            card_content = (
                f"【標籤】#AI角色 #人物設定 #{name_clean}\n\n"
                f"### 【外觀年齡】\n{age}\n\n"
                f"### 【外觀特徵】\n{appearance}\n\n"
                f"### 【人物側寫】\n{profile}\n\n"
                f"### 【已知行動】\n{actions}\n\n"
                f"### 【人事物關聯】\n{relations}"
            )

        return {
            "name": name_clean,
            "title": f"【角色】{name_clean}",
            "age": age,
            "appearance": appearance,
            "profile": profile,
            "actions": actions,
            "relations": relations,
            "content": card_content,
            "tags": ["AI角色", "人物設定", name_clean],
            "summary": f"{age} | {profile[:60]}...",
            "selected": True
        }


class AIWorker(QThread):
    """通用 AI 分析背景執行緒（評語、角色、世界觀、時間線，支援長文捲動壓縮 HRCI）"""
    finished_signal = pyqtSignal(dict)
    progress_signal = pyqtSignal(int, int, str)  # (current_step, total_steps, message)
    error_signal = pyqtSignal(str)

    def __init__(self, task_type: str, text_content: str, chapter_title: str = "",
                 custom_prompt: str = "", chunk_threshold: int = 4000):
        super().__init__()
        self.task_type = task_type  # 'impression', 'character', 'world', 'timeline'
        self.text_content = text_content
        self.chapter_title = chapter_title
        self.custom_prompt = custom_prompt
        self.chunk_threshold = chunk_threshold
        self._is_cancelled = False

    def cancel(self):
        """取消背景分析任務"""
        self._is_cancelled = True

    def run(self):
        try:
            settings = AIService.load_settings()
            provider = settings.get("provider", "Google")
            timeout = int(settings.get("timeout", 300))
            api_url = settings.get("api_urls", {}).get(provider, "")
            api_key = settings.get("api_keys", {}).get(provider, "")
            model = settings.get("models", {}).get(provider, "")
            prompts = settings.get("prompts", {})

            if not api_url:
                raise ValueError(f"尚未設定 {provider} 的 API 網址，請先至 AI 設定中進行設定。")
            if provider not in ("Ollama", "LM Studio") and not api_key:
                raise ValueError(f"尚未填寫 {provider} 的 API Key，請先至 AI 設定填寫。")

            system_prompt = self.custom_prompt or prompts.get(self.task_type, "")

            # 判斷是否為長文（字數大於門檻）
            text_len = len(self.text_content)
            if text_len > self.chunk_threshold:
                from services.long_text_analyzer import LongTextAnalyzer

                def api_caller(sys_p: str, user_p: str) -> str:
                    return AIService.call_api(
                        provider=provider,
                        api_url=api_url,
                        api_key=api_key,
                        model=model,
                        system_prompt=sys_p,
                        user_content=user_p,
                        timeout=timeout
                    )

                def on_progress(cur: int, tot: int, msg: str):
                    self.progress_signal.emit(cur, tot, msg)

                def check_cancelled() -> bool:
                    return self._is_cancelled

                analyzer = LongTextAnalyzer(ai_caller=api_caller)
                analysis_result = analyzer.analyze_long_text(
                    text=self.text_content,
                    task_type=self.task_type,
                    custom_prompt=self.custom_prompt,
                    progress_callback=on_progress,
                    is_cancelled_callback=check_cancelled
                )
                result_text = analysis_result.final_synthesis
            else:
                self.progress_signal.emit(1, 1, "✨ AI 正在分析中，請稍候...")
                # 呼叫單次 API
                result_text = AIService.call_api(
                    provider=provider,
                    api_url=api_url,
                    api_key=api_key,
                    model=model,
                    system_prompt=system_prompt,
                    user_content=self.text_content,
                    timeout=timeout
                )

            # 解析結構與卡片預設對應類別
            category_map = {
                "impression": "summary",
                "character": "character",
                "world": "world",
                "timeline": "timeline"
            }
            default_category = category_map.get(self.task_type, "summary")

            # 生成預設標題
            prefix_map = {
                "impression": "【評語建議】",
                "character": "【角色分析】",
                "world": "【世界觀設定】",
                "timeline": "【時間事件】"
            }
            prefix = prefix_map.get(self.task_type, "【AI分析】")
            title = f"{prefix} {self.chapter_title}".strip() if self.chapter_title else f"{prefix} 文本分析"

            # 產生簡短摘要（前 100 字）
            summary_clean = result_text.strip().replace("\n", " ")
            summary = summary_clean[:97] + "..." if len(summary_clean) > 100 else summary_clean

            # 預設標籤
            tag_map = {
                "impression": ["AI評語", "寫作建議"],
                "character": ["AI角色", "人物設定"],
                "world": ["AI世界觀", "設定資料"],
                "timeline": ["AI時間線", "劇情事件"]
            }
            tags = tag_map.get(self.task_type, ["AI生成"])

            result_dict = {
                "task_type": self.task_type,
                "category": default_category,
                "title": title,
                "summary": summary,
                "tags": tags,
                "content": result_text,
                "raw_response": result_text
            }

            if self.task_type == "character":
                parsed_res = AIService.parse_character_extraction_result(result_text, self.chapter_title)
                result_dict["parsed_characters"] = parsed_res.get("characters", [])
                result_dict["parsed_relationship"] = parsed_res.get("relationship_card")

            self.finished_signal.emit(result_dict)
        except Exception as e:
            self.error_signal.emit(str(e))


class AIChatWorker(QThread):
    """AI 多輪對話背景執行緒"""
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, messages: list, custom_system_prompt: str = ""):
        super().__init__()
        self.messages = list(messages)
        self.custom_system_prompt = custom_system_prompt

    def run(self):
        try:
            settings = AIService.load_settings()
            provider = settings.get("provider", "Google")
            timeout = int(settings.get("timeout", 300))
            api_url = settings.get("api_urls", {}).get(provider, "")
            api_key = settings.get("api_keys", {}).get(provider, "")
            model = settings.get("models", {}).get(provider, "")
            prompts = settings.get("prompts", {})

            if not api_url:
                raise ValueError(f"尚未設定 {provider} 的 API 網址，請先至 AI 設定中進行設定。")
            if provider not in ("Ollama", "LM Studio") and not api_key:
                raise ValueError(f"尚未填寫 {provider} 的 API Key，請先至 AI 設定填寫。")

            sys_prompt = self.custom_system_prompt or prompts.get("chat", "")

            # 組合完整訊息清單
            full_messages = []
            if sys_prompt:
                full_messages.append({"role": "system", "content": sys_prompt})
            full_messages.extend(self.messages)

            resp_text = AIService.call_api(
                provider=provider,
                api_url=api_url,
                api_key=api_key,
                model=model,
                messages=full_messages,
                timeout=timeout
            )
            self.finished_signal.emit(resp_text)
        except Exception as e:
            self.error_signal.emit(str(e))


class AIContinuationWorker(QThread):
    """AI 智慧續寫背景執行緒"""
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, context_text: str, custom_prompt: str = ""):
        super().__init__()
        self.context_text = context_text
        self.custom_prompt = custom_prompt

    def run(self):
        try:
            settings = AIService.load_settings()
            provider = settings.get("provider", "Google")
            timeout = int(settings.get("timeout", 300))
            api_url = settings.get("api_urls", {}).get(provider, "")
            api_key = settings.get("api_keys", {}).get(provider, "")
            model = settings.get("models", {}).get(provider, "")
            prompts = settings.get("prompts", {})

            if not api_url:
                raise ValueError(f"尚未設定 {provider} 的 API 網址，請先至 AI 設定中進行設定。")
            if provider not in ("Ollama", "LM Studio") and not api_key:
                raise ValueError(f"尚未填寫 {provider} 的 API Key，請先至 AI 設定填寫。")

            sys_prompt = self.custom_prompt or prompts.get("continuation", "")

            user_prompt = f"【小說上文】\n{self.context_text}\n\n【請依據上文情節與風格，緊接著續寫正文】"

            resp_text = AIService.call_api(
                provider=provider,
                api_url=api_url,
                api_key=api_key,
                model=model,
                system_prompt=sys_prompt,
                user_content=user_prompt,
                timeout=timeout
            )
            self.finished_signal.emit(resp_text)
        except Exception as e:
            self.error_signal.emit(str(e))


class AIStreamWorker(QThread):
    """通用 AI 流式生成背景執行緒"""
    chunk_received_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    first_token_signal = pyqtSignal()

    def __init__(self, system_prompt: str, user_content: str):
        super().__init__()
        self.system_prompt = system_prompt
        self.user_content = user_content
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            settings = AIService.load_settings()
            provider = settings.get("provider", "Google")
            timeout = int(settings.get("timeout", 300))
            api_url = settings.get("api_urls", {}).get(provider, "")
            api_key = settings.get("api_keys", {}).get(provider, "")
            model = settings.get("models", {}).get(provider, "")

            if not api_url:
                raise ValueError(f"尚未設定 {provider} 的 API 網址，請先至 AI 設定中進行設定。")
            if provider not in ("Ollama", "LM Studio") and not api_key:
                raise ValueError(f"尚未填寫 {provider} 的 API Key，請先至 AI 設定填寫。")

            full_text = []
            first_token_emitted = False

            generator = AIService.call_api_stream(
                provider=provider,
                api_url=api_url,
                api_key=api_key,
                model=model,
                system_prompt=self.system_prompt,
                user_content=self.user_content,
                timeout=timeout
            )

            for chunk in generator:
                if self._is_cancelled:
                    break
                if not first_token_emitted:
                    self.first_token_signal.emit()
                    first_token_emitted = True
                
                full_text.append(chunk)
                self.chunk_received_signal.emit(chunk)

            if self._is_cancelled:
                self.error_signal.emit("使用者已取消生成")
            else:
                self.finished_signal.emit("".join(full_text))

        except Exception as e:
            if not self._is_cancelled:
                self.error_signal.emit(str(e))
