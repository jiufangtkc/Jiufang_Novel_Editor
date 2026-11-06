import json
import uuid
import datetime
import threading
from PyQt6.QtCore import QThread, pyqtSignal


class _AIServiceProxy:
    """延遲代理 AIService，避免與 ai_service.py 產生循環引用。"""
    def __getattr__(self, name):
        from services.ai_service import AIService
        return getattr(AIService, name)


AIService = _AIServiceProxy()


class BaseAIWorker(QThread):
    """具備主動中斷與連線 Socket 立即關閉機制的 AI 背景執行緒基類"""
    def __init__(self):
        super().__init__()
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


class AIProofreadWorker(BaseAIWorker):
    """本機 AI 語意校稿背景執行緒（錯漏字、用詞用典、改寫建議）

    具備段落切片（Chunking）、取消機制與結構化 JSON 輸出容錯解析。
    """
    finished_signal = pyqtSignal(list)
    progress_signal = pyqtSignal(int, int, str)  # (current_chunk, total_chunks, message)
    error_signal = pyqtSignal(str)

    def __init__(self, text_content: str, chapter_name: str = "", node_id: str = "",
                 options: dict = None, chunk_size: int = 2000):
        super().__init__()
        self.text_content = text_content
        self.chapter_name = chapter_name
        self.node_id = node_id
        self.options = options or {"typo": True, "usage": True, "suggestion": True}
        self.chunk_size = chunk_size

    @staticmethod
    def _split_into_chunks(text: str, max_chunk_size: int = 2000) -> list:
        """依換行與長度將文本切分為多個區塊，並記錄各自在全文中的字元偏移量。

        回傳格式為 [(start_offset, chunk_text), ...]
        """
        if not text:
            return []
        if len(text) <= max_chunk_size:
            return [(0, text)]

        chunks = []
        current_chunk = []
        current_len = 0
        current_start = 0

        lines = text.splitlines(keepends=True)
        offset = 0
        for line in lines:
            line_len = len(line)
            # 單行本身超出限制時硬切
            if line_len > max_chunk_size:
                if current_chunk:
                    chunks.append((current_start, "".join(current_chunk)))
                    current_chunk = []
                    current_len = 0
                for sub_start in range(0, line_len, max_chunk_size):
                    sub_str = line[sub_start:sub_start + max_chunk_size]
                    chunks.append((offset + sub_start, sub_str))
                offset += line_len
                current_start = offset
                continue

            if current_len + line_len > max_chunk_size and current_chunk:
                chunks.append((current_start, "".join(current_chunk)))
                current_chunk = [line]
                current_start = offset
                current_len = line_len
            else:
                current_chunk.append(line)
                current_len += line_len
            offset += line_len

        if current_chunk:
            chunks.append((current_start, "".join(current_chunk)))

        return chunks

    def _build_system_prompt(self) -> str:
        """依據 options 勾選設定，動態建立結構化 JSON 輸出之提示詞。"""
        check_items = []
        allowed_cats = []
        if self.options.get("typo", True):
            check_items.append("- 「typo」（錯漏字與別字）：找出字詞拼寫錯誤、同音異字、漏字、多字、顛倒字。")
            allowed_cats.append('"typo"')
        if self.options.get("usage", True):
            check_items.append("- 「usage」（用詞與用典）：找出成語誤用、典故混淆、詞彙搭配不當、語意矛盾。")
            allowed_cats.append('"usage"')
        if self.options.get("suggestion", True):
            check_items.append("- 「suggestion」（改寫建議）：找出語法病句、冗言贅字、語意不清之處，提供潤飾建議。")
            allowed_cats.append('"suggestion"')

        items_str = "\n".join(check_items) if check_items else "- 「typo」：錯別字檢查"
        allowed_cats_str = "、".join(allowed_cats) if allowed_cats else '"typo"'

        prompt = f"""你是一位專業的小說編輯與校對專家，專門校稿台灣繁體中文小說文字。
請針對提供的文本進行嚴格的文字校對。本次檢查項目如下：
{items_str}

【嚴格約束】：
1. 僅針對客觀確鑿的錯別字、詞彙誤用或明顯病句，嚴禁大幅改寫作者的創作文風與修辭習慣。
2. 輸出格式必須是純 JSON 陣列（Array），嚴禁使用 Markdown 標籤（如 ```json ... ```），亦不可包含任何開場白或結尾說明。
3. 若未發現任何需要修改的問題，必須回傳空陣列：[]。
4. 陣列中每個物件必須具備以下欄位：
   - "category": 類別，必須為 {allowed_cats_str} 之一。
   - "original_text": 文本中出現問題的原始字詞（必須與輸入文本完全一致）。
   - "suggestion": 建議替換的正確字詞或潤飾後文字。
   - "reason": 簡明扼要的修改理由或語法說明。
   - "char_offset": 該問題原始字詞在提供文本中的起始字元索引（整數，0-indexed）。
   - "match_len": 原始字詞的長度（整數）。

輸出範例：
[
  {{
    "category": "typo",
    "original_text": "在次",
    "suggestion": "再次",
    "reason": "副詞應使用「再次」而非「在次」",
    "char_offset": 12,
    "match_len": 2
  }}
]"""
        return prompt

    @staticmethod
    def _parse_proofread_json(raw_text: str) -> list:
        """強健解析模型回傳的純文字或 Markdown 包覆之 JSON 陣列。"""
        if not raw_text or not raw_text.strip():
            return []
        cleaned = raw_text.strip()
        # 清除 Markdown code block 標籤
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        # 截取外層陣列括號範圍
        start_idx = cleaned.find("[")
        end_idx = cleaned.rfind("]")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            cleaned = cleaned[start_idx:end_idx + 1]

        try:
            data = json.loads(cleaned)
            if isinstance(data, list):
                return [item for item in data if isinstance(item, dict)]
            return []
        except Exception:
            return []

    def run(self):
        try:
            settings = AIService.load_settings()
            provider = settings.get("provider", "Ollama")
            timeout = int(settings.get("timeout", 300))
            api_url = settings.get("api_urls", {}).get(provider, "")
            api_key = settings.get("api_keys", {}).get(provider, "")
            model = settings.get("models", {}).get(provider, "")

            if not api_url:
                raise ValueError(f"尚未設定 {provider} 的 API 網址，請先至 AI 設定中進行設定。")

            chunks = self._split_into_chunks(self.text_content, self.chunk_size)
            if not chunks:
                self.finished_signal.emit([])
                return

            system_prompt = self._build_system_prompt()
            total_chunks = len(chunks)
            all_results = []

            for idx, (chunk_start_offset, chunk_text) in enumerate(chunks, 1):
                if self._is_cancelled:
                    return

                self.progress_signal.emit(idx, total_chunks, f"正在校稿第 {idx}/{total_chunks} 區段...")

                generator = AIService.call_api_stream(
                    provider=provider,
                    api_url=api_url,
                    api_key=api_key,
                    model=model,
                    system_prompt=system_prompt,
                    user_content=chunk_text,
                    timeout=timeout,
                    is_cancelled_callback=lambda: self._is_cancelled,
                    on_response_ready=self._set_active_response
                )

                chunk_pieces = []
                try:
                    for piece in generator:
                        if self._is_cancelled:
                            break
                        chunk_pieces.append(piece)
                finally:
                    if hasattr(generator, "close"):
                        generator.close()

                if self._is_cancelled:
                    return

                raw_response = "".join(chunk_pieces)
                parsed_items = self._parse_proofread_json(raw_response)

                for item in parsed_items:
                    orig_text = item.get("original_text", "")
                    if not orig_text or not isinstance(orig_text, str):
                        continue

                    cat = item.get("category", "typo")
                    if cat not in ("typo", "usage", "suggestion"):
                        cat = "typo"

                    # 優先在該區段文字中搜尋真實位置以校正偏移量
                    local_idx = chunk_text.find(orig_text)
                    if local_idx != -1:
                        actual_offset = chunk_start_offset + local_idx
                        match_len = len(orig_text)
                    else:
                        model_offset = item.get("char_offset", 0)
                        if not isinstance(model_offset, int) or model_offset < 0:
                            model_offset = 0
                        actual_offset = chunk_start_offset + model_offset
                        match_len = item.get("match_len", len(orig_text))
                        if not isinstance(match_len, int) or match_len <= 0:
                            match_len = len(orig_text)

                    entry = {
                        "id": str(uuid.uuid4()),
                        "category": cat,
                        "node_id": self.node_id,
                        "chapter_name": self.chapter_name,
                        "char_offset": actual_offset,
                        "match_len": match_len,
                        "original_text": orig_text,
                        "suggestion": str(item.get("suggestion", "")),
                        "reason": str(item.get("reason", "")),
                        "status": "pending",
                        "created_at": datetime.datetime.now().isoformat()
                    }
                    all_results.append(entry)

            if self._is_cancelled:
                return

            self.finished_signal.emit(all_results)

        except Exception as e:
            if not self._is_cancelled:
                self.error_signal.emit(str(e))
