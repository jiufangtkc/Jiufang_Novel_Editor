import json
import threading
from collections import defaultdict
from PyQt6.QtCore import QThread, pyqtSignal
from services.ai_settings_service import AISettingsService
from utils.text_splitter import chunk_text_with_overlap

class _AIServiceProxy:
    """延遲代理 AIService，避免循環引用"""
    def __getattr__(self, name):
        from services.ai_service import AIService
        return getattr(AIService, name)

AIService = _AIServiceProxy()

class LongTextPipelineWorker(QThread):
    """
    為本地小模型設計的四階段滾動式長文分析背景執行緒。
    階段：分段 (Chunking) -> 預掃描 (Discovery) -> 滾動抽取 (Rolling Update) -> 收尾 (Reduce)
    """
    finished_signal = pyqtSignal(dict)
    progress_signal = pyqtSignal(int, int, str)
    error_signal = pyqtSignal(str)

    def __init__(self, task_type: str, text_content: str, chapter_title: str = "",
                 custom_prompt: str = "", threshold: int = 3):
        super().__init__()
        self.task_type = task_type
        self.text_content = text_content
        self.chapter_title = chapter_title
        self.custom_prompt = custom_prompt
        self.threshold = threshold
        self._is_cancelled = False
        self._active_response = None
        self._cancel_lock = threading.Lock()

    def _set_active_response(self, response):
        with self._cancel_lock:
            self._active_response = response

    def cancel(self):
        """主動中斷任務並立即關閉底層 HTTP 連線與 Socket"""
        self._is_cancelled = True
        with self._cancel_lock:
            if self._active_response is not None:
                try:
                    if hasattr(self._active_response, "raw") and self._active_response.raw:
                        try:
                            self._active_response.raw.close()
                        except Exception:
                            pass
                    self._active_response.close()
                except Exception:
                    pass
                self._active_response = None

    def run(self):
        try:
            settings = AIService.load_settings()
            provider = settings.get("provider", "Ollama")
            timeout = int(settings.get("timeout", 300))
            api_url = settings.get("api_urls", {}).get(provider, "")
            api_key = settings.get("api_keys", {}).get(provider, "")
            model = settings.get("models", {}).get(provider, "")
            prompts = settings.get("prompts", {})

            if not api_url:
                raise ValueError(f"尚未設定 {provider} 的 API 網址，請先至 AI 設定中進行設定。")
            if provider not in ("Ollama", "LM Studio") and not api_key:
                raise ValueError(f"尚未填寫 {provider} 的 API Key，請先至 AI 設定填寫。")

            # 階段 0: 分段 (Chunking)
            self.progress_signal.emit(0, 4, "階段 0/4：正在對長篇文本進行智慧分段...")
            chunks = chunk_text_with_overlap(self.text_content, chunk_size=1500, overlap_size=200)
            total_chunks = len(chunks)

            if total_chunks == 0:
                raise ValueError("文本內容為空，無法進行分析。")

            # 為了簡化第一次迭代，我們為各任務提供不同的預掃描與更新 prompt
            # 未來可以將這些 prompt 獨立成專門的配置檔
            
            # 階段 1: 預掃描 (Candidate Discovery)
            candidates = defaultdict(int)
            for i, chunk in enumerate(chunks):
                if self._is_cancelled:
                    return
                self.progress_signal.emit(1, 4, f"階段 1/4：預掃描候選關鍵字 (段落 {i+1}/{total_chunks})...")
                
                sys_prompt_stage1 = f"請僅列出以下文本中出現的所有實體名詞（例如人名、地名或關鍵事件），以逗號分隔，不要輸出其他任何文字。任務類型：{self.task_type}"
                result_text = AIService.call_api(
                    provider=provider, api_url=api_url, api_key=api_key, model=model,
                    system_prompt=sys_prompt_stage1, user_content=chunk, timeout=timeout,
                    is_cancelled_callback=lambda: self._is_cancelled,
                    on_response_ready=self._set_active_response
                )
                if self._is_cancelled:
                    return
                
                # 簡單處理逗號分隔的結果
                items = [x.strip() for x in result_text.replace("、", ",").split(",") if x.strip()]
                for item in items:
                    candidates[item] += 1

            # 篩選超過閾值的候選者
            valid_candidates = [name for name, count in candidates.items() if count >= self.threshold]
            if not valid_candidates:
                # 假如沒有超過閾值的，退回保留出現次數最多的前 5 個
                valid_candidates = [k for k, v in sorted(candidates.items(), key=lambda item: item[1], reverse=True)[:5]]

            # 階段 2: 滾動式抽取 (Rolling Extraction)
            state_db = {}
            for i, chunk in enumerate(chunks):
                if self._is_cancelled:
                    return
                self.progress_signal.emit(2, 4, f"階段 2/4：滾動式增量抽取 (段落 {i+1}/{total_chunks})...")
                
                # 將目前的 state 摘要化放入 prompt 之中
                state_summary = json.dumps(state_db, ensure_ascii=False) if state_db else "{}"
                candidates_str = ", ".join(valid_candidates)
                
                sys_prompt_stage2 = (
                    f"目前正在進行 {self.task_type} 分析。\n"
                    f"已知重要實體候選：{candidates_str}\n"
                    f"目前的內部狀態庫為：{state_summary}\n\n"
                    "請根據以下最新段落，更新或追加上述實體的屬性、設定與事件。\n"
                    "請嚴格以 JSON 格式輸出更新後的內部狀態庫（不要包含 Markdown 代碼塊）。"
                )
                
                diff_result = AIService.call_api(
                    provider=provider, api_url=api_url, api_key=api_key, model=model,
                    system_prompt=sys_prompt_stage2, user_content=chunk, timeout=timeout,
                    is_cancelled_callback=lambda: self._is_cancelled,
                    on_response_ready=self._set_active_response
                )
                if self._is_cancelled:
                    return
                
                try:
                    # 清理可能的 markdown code block
                    clean_json = diff_result.strip()
                    if clean_json.startswith("```json"):
                        clean_json = clean_json[7:-3].strip()
                    elif clean_json.startswith("```"):
                        clean_json = clean_json[3:-3].strip()
                        
                    new_state = json.loads(clean_json)
                    if isinstance(new_state, dict):
                        # 合併狀態
                        for k, v in new_state.items():
                            if k in state_db and isinstance(state_db[k], dict) and isinstance(v, dict):
                                state_db[k].update(v)
                            else:
                                state_db[k] = v
                except Exception as e:
                    # JSON 解析失敗則跳過此段更新
                    print(f"Stage 2 JSON 解析警告 (Chunk {i}): {e}")
            if self._is_cancelled:
                return

            # 階段 3: 收尾整合 (Reduce)
            self.progress_signal.emit(3, 4, "階段 3/4：收尾與最終格式轉換...")
            
            # 使用原有的 _parse_raw_result 邏輯來把整合完的字串 (或 JSON) 轉為最終卡片陣列
            # 為了與原程式碼相容，我們將 state_db 轉回可讀字串，再過一次既有 Parser，
            # 或直接把狀態庫組裝成卡片結構。
            
            final_text = json.dumps(state_db, indent=2, ensure_ascii=False)
            
            category_map = {
                "impression": "summary",
                "character": "character",
                "world": "world",
                "timeline": "timeline"
            }
            default_category = category_map.get(self.task_type, "summary")

            prefix_map = {
                "impression": "【評語建議】",
                "character": "【角色分析】",
                "world": "【世界觀設定】",
                "timeline": "【時間事件】"
            }
            prefix = prefix_map.get(self.task_type, "【AI分析】")
            title = f"{prefix} {self.chapter_title}".strip() if self.chapter_title else f"{prefix} 文本分析"

            summary_clean = final_text.strip().replace("\n", " ")
            summary = summary_clean[:100] + "..." if len(summary_clean) > 100 else summary_clean

            if self.task_type == "character":
                # 把 state_db 中的角色轉為角色卡格式
                characters = []
                for name, info in state_db.items():
                    if isinstance(info, dict):
                        age = info.get("外觀年齡") or info.get("年齡", "未提及")
                        appearance = info.get("外觀特徵") or info.get("外貌", "未提及")
                        profile = info.get("人物側寫") or info.get("性格", "未提及")
                        actions = info.get("已知行動") or info.get("行動", "未提及")
                        relations = info.get("人事物關聯") or info.get("關係", "未提及")
                        
                        card_content = (
                            f"【標籤】#AI角色 #人物設定 #{name}\n\n"
                            f"### 【外觀年齡】\n{age}\n\n"
                            f"### 【外觀特徵】\n{appearance}\n\n"
                            f"### 【人物側寫】\n{profile}\n\n"
                            f"### 【已知行動】\n{actions}\n\n"
                            f"### 【人事物關聯】\n{relations}"
                        )
                        
                        characters.append({
                            "name": name,
                            "title": f"【角色】{name}",
                            "age": age,
                            "appearance": appearance,
                            "profile": profile,
                            "actions": actions,
                            "relations": relations,
                            "content": card_content,
                            "tags": ["AI角色", "人物設定", name],
                            "summary": f"{age} | {profile[:60]}...",
                            "selected": True
                        })
                rel_card = None
            else:
                characters = []
                rel_card = None

            parsed_result = {
                "task_type": self.task_type,
                "title": title,
                "category": default_category,
                "content": final_text,
                "summary": summary,
                "tags": [f"AI分析", default_category],
                "characters": characters,
                "relationship_card": rel_card
            }
            
            if self._is_cancelled:
                return

            self.progress_signal.emit(4, 4, "✅ 分析完成！")
            self.finished_signal.emit(parsed_result)

        except Exception as e:
            if not self._is_cancelled:
                self.error_signal.emit(str(e))
