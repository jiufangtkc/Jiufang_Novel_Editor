import json
import os
import urllib.parse
import requests

from services.ai_settings_service import AISettingsService, DEFAULT_SETTINGS, SETTINGS_FILENAME


class AIService:
    @classmethod
    def get_settings_file_path(cls, custom_dir: str = None) -> str:
        """取得本機儲存 AI 設定檔的完整絕對路徑（委派給 AISettingsService）。"""
        return AISettingsService.get_settings_file_path(custom_dir)

    @classmethod
    def load_settings(cls, file_path: str = None) -> dict:
        """讀取 AI 設定檔（委派給 AISettingsService）。"""
        return AISettingsService.load_settings(file_path)

    @classmethod
    def save_settings(cls, settings: dict, file_path: str = None):
        """儲存 AI 設定檔（委派給 AISettingsService）。"""
        AISettingsService.save_settings(settings, file_path)

    @classmethod
    def call_api(cls, provider: str, api_url: str, api_key: str, model: str,
                 system_prompt: str = "", user_content: str = "",
                 messages: list = None, timeout=300, is_cancelled_callback=None,
                 on_response_ready=None) -> str:
        """發送請求至 LLM API 並回傳純文字結果（底層全面使用串流以支援立即中斷）"""
        generator = cls.call_api_stream(
            provider=provider,
            api_url=api_url,
            api_key=api_key,
            model=model,
            system_prompt=system_prompt,
            user_content=user_content,
            messages=messages,
            timeout=timeout,
            is_cancelled_callback=is_cancelled_callback,
            on_response_ready=on_response_ready
        )
        
        full_text = []
        try:
            for chunk in generator:
                if is_cancelled_callback and is_cancelled_callback():
                    break
                full_text.append(chunk)
                
            if is_cancelled_callback and is_cancelled_callback():
                raise RuntimeError("API 請求已被取消")
                
            return "".join(full_text)
        finally:
            if hasattr(generator, "close"):
                generator.close()

    @classmethod
    def call_api_stream(cls, provider: str, api_url: str, api_key: str, model: str,
                 system_prompt: str = "", user_content: str = "",
                 messages: list = None, timeout=300, is_cancelled_callback=None,
                 on_response_ready=None):
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

        try:
            with requests.post(api_url, json=payload, headers=headers, stream=True, timeout=timeout) as response:
                if on_response_ready:
                    on_response_ready(response)
                response.raise_for_status()
                for line in response.iter_lines():
                    if is_cancelled_callback and is_cancelled_callback():
                        break
                        
                    if not line:
                        continue
                        
                    line_str = line.decode('utf-8').strip()
                    if not line_str:
                        continue
                        
                    if provider == "Ollama":
                        try:
                            data = json.loads(line_str)
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            pass
                    else:
                        if line_str.startswith("data: "):
                            data_str = line_str[6:]
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
                                        reasoning = delta.get("reasoning_content", "")
                                        content = delta.get("content", "")
                                        if reasoning:
                                            yield reasoning
                                        if content:
                                            yield content
                            except json.JSONDecodeError:
                                pass
        except requests.exceptions.Timeout:
            if is_cancelled_callback and is_cancelled_callback():
                return
            raise RuntimeError(f"連線/生成超時（{timeout} 秒）。本地大型或思考型模型處理耗時較長，請確認服務狀態或調高逾時上限後重試。")
        except requests.exceptions.RequestException as e:
            if is_cancelled_callback and is_cancelled_callback():
                return
            raise RuntimeError(f"API 請求連線異常: {e}")
        except Exception as e:
            if is_cancelled_callback and is_cancelled_callback():
                return
            raise RuntimeError(f"串流 API 請求解析異常: {str(e)}")
        finally:
            if on_response_ready:
                on_response_ready(None)

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
    def count_tokens(cls, provider: str, api_url: str, text: str, timeout=5) -> int:
        """
        向推理引擎查詢精確的 token 數量。
        若不支援，則 fallback 到保守估算值（長度 * 2.5）。
        """
        if not text:
            return 0
            
        fallback_tokens = int(len(text) * 2.5)
        
        if not api_url:
            return fallback_tokens

        parsed = urllib.parse.urlparse(api_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else api_url

        try:
            if provider == "Ollama":
                # Ollama 0.2+ 支援 /api/tokenize，嘗試呼叫後取得精確 token 數
                # payload 格式：{"model": <model>, "prompt": <text>}
                # 回應格式：{"tokens": [...]}，tokens 列表長度即為 token 數
                tokenize_url = f"{base_url}/api/tokenize"
                try:
                    resp = requests.post(
                        tokenize_url,
                        json={"prompt": text},
                        headers={"Content-Type": "application/json"},
                        timeout=timeout
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        tokens_list = data.get("tokens", None)
                        if isinstance(tokens_list, list):
                            return len(tokens_list)
                except Exception:
                    pass
                # 端點不存在或連線失敗時靜默 fallback
                return fallback_tokens
            elif provider == "LM Studio" or "1234" in api_url or "v1" in api_url:
                tokenize_url = f"{base_url}/v1/tokenize"
                payload = {"content": text}
                # LM Studio v1/tokenize 只需要 content (或 prompt)
                resp = requests.post(tokenize_url, json=payload, headers={"Content-Type": "application/json"}, timeout=timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    # 依據 LM Studio 格式 (通常返回 {"count": xxx})
                    if "count" in data:
                        return int(data["count"])
                    elif "total_tokens" in data:
                        return int(data["total_tokens"])
                    # 若為 embedding 介面可能在 usage 裡面
                    elif "usage" in data and "total_tokens" in data["usage"]:
                        return int(data["usage"]["total_tokens"])
                
            return fallback_tokens
        except Exception as e:
            return fallback_tokens
            
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
                resp = requests.get(tags_url, headers={"User-Agent": "Jiufang-Novel-Editor"}, timeout=timeout)
                resp.raise_for_status()
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
                return models
            elif provider == "LM Studio" or "1234" in api_url or "models" in api_url:
                models_url = f"{base_url}/v1/models"
                resp = requests.get(models_url, headers={"User-Agent": "Jiufang-Novel-Editor"}, timeout=timeout)
                resp.raise_for_status()
                data = resp.json()
                models = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
                return models
            else:
                # 嘗試通用 OpenAI /v1/models 端點
                models_url = f"{base_url}/v1/models"
                resp = requests.get(models_url, headers={"User-Agent": "Jiufang-Novel-Editor"}, timeout=timeout)
                resp.raise_for_status()
                data = resp.json()
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



# 為了向後相容性，在此 re-export 背景執行緒類別
from services.ai_worker import AIWorker, AIChatWorker, AIContinuationWorker, AIStreamWorker
