from PyQt6.QtCore import QThread, pyqtSignal
from services.ai_settings_service import AISettingsService


def _get_ai_service():
    from services.ai_service import AIService
    return AIService


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
                self.progress_signal.emit(1, 1, "🧠 正在連線模型並分析文本...")
                chunks = []
                generator = AIService.call_api_stream(
                    provider=provider,
                    api_url=api_url,
                    api_key=api_key,
                    model=model,
                    system_prompt=system_prompt,
                    user_content=self.text_content,
                    timeout=timeout
                )
                chunk_count = 0
                for chunk in generator:
                    if self._is_cancelled:
                        break
                    chunks.append(chunk)
                    chunk_count += 1
                    if chunk_count % 5 == 0:
                        total_len = sum(len(c) for c in chunks)
                        self.progress_signal.emit(1, 1, f"✨ 正在生成分析結果（已產出約 {total_len} 字）...")

                if self._is_cancelled:
                    raise RuntimeError("AI 分析已被使用者取消。")
                result_text = "".join(chunks)

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
    """AI 多輪對話背景執行緒（支援串流輸出與工作階段通知）"""
    chunk_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str, str)  # (status_key, display_message)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, messages: list, custom_system_prompt: str = ""):
        super().__init__()
        self.messages = list(messages)
        self.custom_system_prompt = custom_system_prompt
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            self.status_signal.emit("connecting", "🧠 正在連線模型...")
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

            self.status_signal.emit("thinking", "⏳ 模型思考中...")

            full_chunks = []
            first_chunk_received = False

            generator = AIService.call_api_stream(
                provider=provider,
                api_url=api_url,
                api_key=api_key,
                model=model,
                messages=full_messages,
                timeout=timeout
            )

            for chunk in generator:
                if self._is_cancelled:
                    break
                if not first_chunk_received:
                    first_chunk_received = True
                    self.status_signal.emit("generating", "✍️ 正在生成回覆中...")
                full_chunks.append(chunk)
                self.chunk_signal.emit(chunk)

            if self._is_cancelled:
                self.error_signal.emit("對話生成已被使用者取消。")
            else:
                resp_text = "".join(full_chunks)
                self.status_signal.emit("finished", "✅ 回覆完成")
                self.finished_signal.emit(resp_text)
        except Exception as e:
            if not self._is_cancelled:
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
