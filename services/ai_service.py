import json
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
    def call_api(cls, provider: str, api_url: str, api_key: str = "", model: str = "",
                 system_prompt: str = "", user_content: str = "",
                 messages: list = None, timeout=300, is_cancelled_callback=None,
                 on_response_ready=None, max_tokens: int = None) -> str:
        """發送請求至本機 LLM API 並回傳純文字結果（底層全面使用串流以支援立即中斷）"""
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
            on_response_ready=on_response_ready,
            max_tokens=max_tokens
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
    def call_api_stream(cls, provider: str, api_url: str, api_key: str = "", model: str = "",
                        system_prompt: str = "", user_content: str = "",
                        messages: list = None, timeout=300, is_cancelled_callback=None,
                        on_response_ready=None, max_tokens: int = None):
        """發送請求至本機 LLM API（Ollama 或 OpenAI 相容端點如 LM Studio）並以 Generator 形式回傳文字片段"""
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

        if provider == "Ollama":
            payload = {
                "model": model,
                "messages": formatted_messages,
                "stream": True
            }
            if max_tokens:
                payload["options"] = {"num_predict": max_tokens}
        else:
            # LM Studio 等標準本機 OpenAI 相容介面 (/v1/chat/completions)
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            elif provider == "LM Studio":
                headers["Authorization"] = "Bearer not-needed"

            payload = {
                "model": model or "local-model",
                "messages": formatted_messages,
                "stream": True
            }
            if max_tokens:
                payload["max_tokens"] = max_tokens

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

                    line_str = line.decode("utf-8").strip()
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
            raise RuntimeError(f"連線/生成超時（{timeout} 秒）。本機大型或思考型模型處理耗時較長，請確認服務狀態或調高逾時上限後重試。")
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
    def test_connection(cls, provider: str, api_url: str, api_key: str = "", model: str = "", timeout=90) -> str:
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
    def fast_estimate_tokens(cls, text: str) -> int:
        """純本機零延遲 Token 估算。"""
        if not text:
            return 0
        import re
        cjk_count = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]', text))
        non_cjk = re.sub(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]', ' ', text)
        words = len(non_cjk.split())
        estimated = int(cjk_count * 1.25 + words * 1.3)
        return max(1, estimated)

    @classmethod
    def count_tokens(cls, provider: str, api_url: str, text: str, timeout=5) -> int:
        """向推理引擎查詢精確的 token 數量，若為 LM Studio 或連線失敗則使用純本機估算。"""
        if not text:
            return 0

        fallback_tokens = cls.fast_estimate_tokens(text)

        if provider != "Ollama" or not api_url:
            return fallback_tokens

        parsed = urllib.parse.urlparse(api_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else api_url

        try:
            tokenize_url = f"{base_url}/api/tokenize"
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
            elif provider == "LM Studio" or "1234" in api_url:
                try:
                    v0_url = f"{base_url}/api/v0/models"
                    resp = requests.get(v0_url, headers={"User-Agent": "Jiufang-Novel-Editor"}, timeout=timeout)
                    if resp.status_code == 200:
                        data = resp.json().get("data", [])
                        loaded_models = [m.get("id", "") for m in data if m.get("state") == "loaded" and m.get("id")]
                        other_models = [m.get("id", "") for m in data if m.get("state") != "loaded" and m.get("id")]
                        all_models = loaded_models + other_models
                        if all_models:
                            return all_models
                except Exception:
                    pass

                models_url = f"{base_url}/v1/models"
                resp = requests.get(models_url, headers={"User-Agent": "Jiufang-Novel-Editor"}, timeout=timeout)
                resp.raise_for_status()
                data = resp.json()
                models = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
                return models
            else:
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
    def check_local_server_status(cls, provider: str, api_url: str, timeout: float = 1.0) -> tuple[bool, str]:
        """檢查本機推論引擎（LM Studio / Ollama）伺服器是否在線。
        傳回 (is_online, message)。
        """
        if not api_url:
            return False, f"尚未設定 {provider} API 網址"

        parsed = urllib.parse.urlparse(api_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else api_url

        try:
            if provider == "LM Studio" or "1234" in api_url:
                probe_url = f"{base_url}/api/v0/models"
                try:
                    resp = requests.get(probe_url, headers={"User-Agent": "Jiufang-Novel-Editor"}, timeout=timeout)
                    if resp.status_code == 200:
                        return True, "連線正常"
                except requests.exceptions.RequestException:
                    pass
                probe_url = f"{base_url}/v1/models"
                resp = requests.get(probe_url, headers={"User-Agent": "Jiufang-Novel-Editor"}, timeout=timeout)
                if resp.status_code == 200:
                    return True, "連線正常"
                return False, f"伺服器回應異常（HTTP {resp.status_code}）"

            elif provider == "Ollama":
                probe_url = f"{base_url}/api/tags"
                resp = requests.get(probe_url, headers={"User-Agent": "Jiufang-Novel-Editor"}, timeout=timeout)
                if resp.status_code == 200:
                    return True, "連線正常"
                return False, f"伺服器回應異常（HTTP {resp.status_code}）"
        except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout):
            return False, f"{provider} 服務未啟動（連線遭拒或超時）"
        except requests.exceptions.Timeout:
            return False, f"{provider} 服務連線超時"
        except Exception as e:
            return False, f"無法連線至 {provider} ({e})"

        return False, f"{provider} 服務狀態未知"

    @classmethod
    def fetch_context_limit(cls, provider: str, api_url: str, model: str = "", timeout: float = 1.5) -> int | None:
        """主動自本機端點（如 LM Studio / Ollama）查詢目前已載入模型的 Context 上限數值。
        若查詢失敗或不支援動態查詢，則傳回 None。
        """
        if not api_url:
            return None

        parsed = urllib.parse.urlparse(api_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else api_url

        try:
            if provider == "LM Studio" or "1234" in api_url:
                v0_url = f"{base_url}/api/v0/models"
                resp = requests.get(v0_url, headers={"User-Agent": "Jiufang-Novel-Editor"}, timeout=timeout)
                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                    target_item = None
                    if model:
                        for m in data:
                            if m.get("id") == model:
                                target_item = m
                                break
                    if not target_item:
                        for m in data:
                            if m.get("state") == "loaded":
                                target_item = m
                                break
                    if not target_item and len(data) == 1:
                        target_item = data[0]

                    if target_item:
                        loaded_ctx = target_item.get("loaded_context_length")
                        if loaded_ctx and isinstance(loaded_ctx, int) and loaded_ctx > 0:
                            return loaded_ctx
                        max_ctx = target_item.get("max_context_length")
                        if max_ctx and isinstance(max_ctx, int) and max_ctx > 0:
                            return max_ctx

            elif provider == "Ollama":
                if model:
                    show_url = f"{base_url}/api/show"
                    resp = requests.post(show_url, json={"name": model}, headers={"User-Agent": "Jiufang-Novel-Editor"}, timeout=timeout)
                    if resp.status_code == 200:
                        data = resp.json()
                        model_info = data.get("model_info", {})
                        for k, v in model_info.items():
                            if k.endswith(".context_length") and isinstance(v, int) and v > 0:
                                return v
        except Exception:
            pass

        return None


# 向後相容 re-export 背景執行緒類別
from services.ai_worker import BaseAIWorker, AIProofreadWorker
