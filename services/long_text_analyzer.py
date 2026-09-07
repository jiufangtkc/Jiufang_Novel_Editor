import re
from typing import List, Callable, Optional, Dict
from models.models import CompactState, ChunkAnalysisResult, LongTextAnalysisResult


class LongTextAnalyzer:
    """長文分層捲動壓縮與索引分析器（Hierarchical Rolling Compact & Indexing, HRCI）

    針對 9B 以下本地小模型及長篇小說設計，透過「語義分塊 + 捲動狀態壓縮 + 雙軌索引」機制，
    確保在小模型上下文視窗（Context Window）限制下，能穩定且無遺漏地分析超長小說文本。

    架構約束規範：
    - **絕對無狀態（Stateless）**：LongTextAnalyzer 實例本身不持久化持有特定小說文本或狀態庫，每一次分析呼叫皆為獨立無副作用執行。
    - **單一佇列序列化（Serialized）**：各分段分析與 LLM 推論請求必須依序序列化執行，嚴禁多執行緒並行呼叫本地模型以防 GPU 記憶體崩潰。
    """

    DEFAULT_CHUNK_SIZE = 2800
    DEFAULT_OVERLAP = 200
    MAX_SYNTHESIS_SUMMARY_CHARS = 3200

    TASK_NAME_MAP = {
        "impression": "整體基調與評語建議",
        "character": "登場人物與關係分析",
        "world": "世界觀與設定架構分析",
        "timeline": "故事時間線與關鍵事件梳理"
    }

    def __init__(self, ai_caller: Optional[Callable[[str, str], str]] = None,
                 chunk_size: Optional[int] = None,
                 overlap: int = DEFAULT_OVERLAP,
                 token_counter: Optional[Callable[[str], int]] = None):
        """初始化分析器。

        Args:
            ai_caller: 呼叫 LLM 的函式，簽章為 (system_prompt: str, user_content: str) -> str
            chunk_size: 單一分塊建議目標字數（若為 None 則於分析時依硬體動態推算，預設 2,800 字）
            overlap: 分塊間重疊滑動字數（預設 200 字）
            token_counter: 計算字串 Token 數的函數
        """
        self.ai_caller = ai_caller
        self._custom_chunk_size = chunk_size
        self.chunk_size = chunk_size if chunk_size is not None else self.DEFAULT_CHUNK_SIZE
        self.overlap = overlap
        self.token_counter = token_counter or (lambda x: int(len(x) * 2.5))

    @classmethod
    def calculate_dynamic_chunk_size(cls, max_context_tokens: Optional[int] = None) -> tuple[int, int]:
        """推算最佳分段長度與安全 Token 上限。
        
        依據系統硬體可用記憶體（VRAM / 系統 RAM）動態推算：
        - 若未手動傳入 max_context_tokens，則呼叫 services.hardware_detector.get_available_memory_mb()。
        - 保守策略：每 1GB 可用記憶體約對應 1000 Tokens 上下文，上限截斷為 12000 Tokens。
        - 預留輸出與系統 Prompt 空間（約 2000 Tokens）。
        - 若可用記憶體低於 1500 MB 或安全分塊字數小於 500 字，拋出 MemoryError 以觸發 UI 降級防護。

        Returns:
            tuple[int, int]: (chunk_size, max_context_tokens)
        """
        if max_context_tokens is None:
            from services.hardware_detector import get_available_memory_mb
            free_mem_mb = get_available_memory_mb()

            if free_mem_mb < 1500:
                raise MemoryError("偵測到系統可用記憶體嚴重不足（低於 1.5GB），無法進行有效分析。請關閉其他佔用資源的程式，或於設定中選擇較小的模型。")

            # 保守策略：每 1GB VRAM/RAM 容納約 1000 Token 上下文
            max_context_tokens = int((free_mem_mb / 1024) * 1000)
            if max_context_tokens > 12000:
                max_context_tokens = 12000

        # 預留輸出與系統 Prompt： 1500 輸出 + 300 系統 + 200 緩衝 = 2000
        chunk_size = max_context_tokens - 2000
        if chunk_size < 500:
            raise MemoryError("偵測到系統可用記憶體嚴重不足，無法進行有效分析。請關閉其他佔用資源的程式，或於設定中選擇較小的模型。")

        return chunk_size, max_context_tokens

    def split_into_chunks(self, text: str) -> List[str]:
        """依據自然語義段落將文本切分為具備重疊滑動區間的分塊清單。"""
        clean_text = text.strip()
        if not clean_text:
            return []

        if len(clean_text) <= self.chunk_size:
            return [clean_text]

        # 優先以雙換行（段落）切分，若無則依單換行切分
        raw_paragraphs = [p for p in re.split(r'(\n\s*\n|\n)', clean_text) if p]

        # 展開過長的單一段落（以句子標點符號切分）
        fine_paragraphs = []
        for p in raw_paragraphs:
            if len(p) > self.chunk_size:
                # 依全形標點切割
                sub_parts = re.split(r'([。！？!?]+)', p)
                buffer = ""
                for part in sub_parts:
                    if len(buffer) + len(part) > self.chunk_size and buffer:
                        fine_paragraphs.append(buffer)
                        buffer = part
                    else:
                        buffer += part
                if buffer:
                    fine_paragraphs.append(buffer)
            else:
                fine_paragraphs.append(p)

        chunks = []
        current_chunk_parts = []
        current_length = 0

        for p in fine_paragraphs:
            p_len = len(p)
            if current_length + p_len > self.chunk_size and current_chunk_parts:
                chunk_str = "".join(current_chunk_parts).strip()
                if chunk_str:
                    chunks.append(chunk_str)

                # 計算重疊區域（取當前 chunk 尾端約 overlap 長度）
                overlap_text = ""
                if len(chunk_str) > self.overlap:
                    # 尋找重疊起始點（盡量以標點或換行開始）
                    raw_overlap = chunk_str[-self.overlap:]
                    match = re.search(r'[。\n！？!?]', raw_overlap)
                    if match and match.end() < len(raw_overlap):
                        overlap_text = raw_overlap[match.end():]
                    else:
                        overlap_text = raw_overlap
                else:
                    overlap_text = chunk_str

                if overlap_text:
                    current_chunk_parts = [f"【接續上文片段】\n{overlap_text}\n\n", p]
                    current_length = len(current_chunk_parts[0]) + p_len
                else:
                    current_chunk_parts = [p]
                    current_length = p_len
            else:
                current_chunk_parts.append(p)
                current_length += p_len

        if current_chunk_parts:
            final_chunk = "".join(current_chunk_parts).strip()
            if final_chunk:
                chunks.append(final_chunk)

        return chunks

    def build_chunk_prompt(self, task_type: str, chunk_text: str,
                           chunk_index: int, total_chunks: int,
                           state: CompactState, custom_prompt: str = "",
                           token_budget: int = 600) -> tuple[str, str]:
        """建構分塊分析的 System Prompt 與 User Prompt。"""
        task_name = self.TASK_NAME_MAP.get(task_type, "小說文本分析")

        system_prompt = (
            f"你是一位專業嚴謹的小說分析編輯與文學顧問。現在正在對一部長篇小說進行「{task_name}」。\n"
            f"本分析採用捲動壓縮管線進行，這是一篇包含 {total_chunks} 個分段的長篇作品。\n"
            f"你必須嚴格基於提供的前文「歷史摘要索引」與「當前片段」，進行客觀結構化分析，並輸出更新後的索引供下一階段使用。"
        )

        history_summary = state.get_dynamic_summary(chunk_text=chunk_text, token_budget=token_budget, token_counter=self.token_counter)

        specific_guideline = custom_prompt if custom_prompt else self._get_task_guidelines(task_type)

        user_content = (
            f"### 【長篇進度】：第 {chunk_index} / {total_chunks} 段（本段長度約 {len(chunk_text)} 字）\n\n"
            f"### 【前文累積之歷史摘要索引】：\n{history_summary}\n\n"
            f"### 【當前分析指引】：\n{specific_guideline}\n\n"
            f"### 【當前小說正文片段】：\n```text\n{chunk_text}\n```\n\n"
            f"### 【強制輸出格式要求】：\n"
            f"請嚴格依據以下兩大標題格式輸出，不要有任何多餘開場白或閒聊：\n\n"
            f"### 【本段分析結論】\n"
            f"（請精簡扼要針對本段核心情節推進、角色互動與關鍵細節提出深入分析，字數嚴格控制在 300 至 500 字以內，切勿冗長發散）\n\n"
            f"### 【更新後摘要索引】\n"
            f"- 人物狀態更新：[角色名：當前動態/性格表現/關係變化]（每位角色說明不超過 35 字）\n"
            f"- 世界觀設定增量：[新出現的名詞/規則/背景]\n"
            f"- 關鍵里程碑事件：[本段確定發生的重大情節]\n"
            f"- 當前未解懸念：[本段留下或仍在持續的伏筆]\n"
            f"- 結尾場景與局勢：[本段結束時人物所處的具體情境與狀態]\n"
        )

        return system_prompt, user_content

    def _get_task_guidelines(self, task_type: str) -> str:
        """取得特定分析任務的詳細指引"""
        if task_type == "impression":
            return "分析本段的情節張力、節奏起伏、敘事風格與主題表達，並評估寫作亮點與改進空間。"
        elif task_type == "character":
            return "提取本段登場角色的言行舉止、性格特徵、心理動機與彼此間的關係變化。"
        elif task_type == "world":
            return "提取本段中展現的地理環境、社會背景、勢力組織、力量體系或專有名詞設定。"
        elif task_type == "timeline":
            return "梳理本段事件發生的時間順序、場景轉換節點與重大因果關係。"
        return "深入分析本段文本的核心內容、文學表現與結構細節。"

    def parse_chunk_response(self, response_text: str, current_state: CompactState) -> tuple[str, CompactState]:
        """解析 LLM 對單一分塊的回應，分離出局部結論並捲動更新狀態索引。"""
        clean_resp = response_text.strip()

        # 分離【本段分析結論】與【更新後摘要索引】
        analysis_part = ""
        index_part = ""

        # 使用正則搜尋標題
        pattern = r'###\s*【本段分析結論】([\s\S]*?)(?=###\s*【更新後摘要索引】|$)'
        match_analysis = re.search(pattern, clean_resp)

        pattern_index = r'###\s*【更新後摘要索引】([\s\S]*)'
        match_index = re.search(pattern_index, clean_resp)

        if match_analysis:
            analysis_part = match_analysis.group(1).strip()
        if match_index:
            index_part = match_index.group(1).strip()

        # Fallback 容錯處理：若模型沒有依格式分段
        if not analysis_part and not index_part:
            analysis_part = clean_resp
            index_part = clean_resp[:400]

        # 更新 CompactState（複製現有狀態並加入增量）
        new_state = CompactState(
            characters=dict(current_state.characters),
            character_mentions=dict(current_state.character_mentions),
            world_elements=dict(current_state.world_elements),
            timeline_events=list(current_state.timeline_events),
            unresolved_threads=list(current_state.unresolved_threads),
            current_scene_context=""
        )

        if index_part:
            self._update_state_from_text(new_state, index_part)

        return analysis_part if analysis_part else clean_resp, new_state

    def _update_state_from_text(self, state: CompactState, index_text: str):
        """從結構化索引文字中解析並更新狀態物件"""
        lines = index_text.split("\n")
        current_section = None

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            if "人物" in line_str:
                current_section = "characters"
                # 若同在一行包含冒號
                content = re.sub(r'^.*?人物[^\s：:]*[：:]', '', line_str).strip()
                if content and "：" in content:
                    self._parse_kv_line(state.characters, content, state.character_mentions)
                continue
            elif "世界觀" in line_str or "設定" in line_str:
                current_section = "world"
                content = re.sub(r'^.*?設定[^\s：:]*[：:]', '', line_str).strip()
                if content and "：" in content:
                    self._parse_kv_line(state.world_elements, content)
                continue
            elif "事件" in line_str or "情節" in line_str or "時間" in line_str:
                current_section = "timeline"
                content = re.sub(r'^.*?事件[^\s：:]*[：:]', '', line_str).strip()
                if content:
                    state.timeline_events.append(content)
                continue
            elif "懸念" in line_str or "伏筆" in line_str:
                current_section = "threads"
                content = re.sub(r'^.*?伏筆[^\s：:]*[：:]', '', line_str).strip()
                if content:
                    state.unresolved_threads.append(content)
                continue
            elif "場景" in line_str or "局勢" in line_str or "結尾" in line_str:
                current_section = "scene"
                content = re.sub(r'^.*?局勢[^\s：:]*[：:]', '', line_str).strip()
                if content:
                    state.current_scene_context = content
                continue

            # 處理條列內容（- 或數字）
            item_text = re.sub(r'^[-*•\d\.\s]+', '', line_str).strip()
            if not item_text:
                continue

            if current_section == "characters":
                self._parse_kv_line(state.characters, item_text, state.character_mentions)
            elif current_section == "world":
                self._parse_kv_line(state.world_elements, item_text)
            elif current_section == "timeline":
                if item_text not in state.timeline_events:
                    state.timeline_events.append(item_text)
            elif current_section == "threads":
                if item_text not in state.unresolved_threads:
                    state.unresolved_threads.append(item_text)
            elif current_section == "scene":
                state.current_scene_context = (state.current_scene_context + " " + item_text).strip()

        # 狀態長度上限保護（防止小模型索引膨脹）
        if len(state.timeline_events) > 20:
            state.timeline_events = state.timeline_events[-20:]
        if len(state.unresolved_threads) > 10:
            state.unresolved_threads = state.unresolved_threads[-10:]

    def _parse_kv_line(self, target_dict: Dict[str, str], text: str,
                       mentions_dict: Optional[Dict[str, int]] = None):
        """解析如『[張三：主角]、[李四：反派]』或『張三：主角，受傷撤退』之鍵值對"""
        bracket_matches = re.findall(r'\[\s*([^:：\]]+?)\s*[：:]\s*([^\]]+?)\s*\]', text)
        if bracket_matches:
            for k, v in bracket_matches:
                k_clean = k.strip().strip("*_#[] ")
                v_clean = v.strip()
                if k_clean and v_clean:
                    target_dict[k_clean] = v_clean
                    if mentions_dict is not None:
                        mentions_dict[k_clean] = mentions_dict.get(k_clean, 0) + 1
            return

        if "：" in text:
            parts = text.split("：", 1)
            k = parts[0].strip().strip("*_#[]【】 ")
            v = parts[1].strip().strip("[]【】 ")
            if k and v:
                target_dict[k] = v
                if mentions_dict is not None:
                    mentions_dict[k] = mentions_dict.get(k, 0) + 1
        elif ":" in text:
            parts = text.split(":", 1)
            k = parts[0].strip().strip("*_#[]【】 ")
            v = parts[1].strip().strip("[]【】 ")
            if k and v:
                target_dict[k] = v
                if mentions_dict is not None:
                    mentions_dict[k] = mentions_dict.get(k, 0) + 1

    def build_synthesis_prompt(self, task_type: str, final_state: CompactState,
                               chunk_results: List[ChunkAnalysisResult],
                               total_chars: int, custom_prompt: str = "") -> tuple[str, str]:
        """建構長文捲動結束後的全局綜合整合 Prompt（具備動態上下文預算與保護機制）。"""
        task_name = self.TASK_NAME_MAP.get(task_type, "長篇小說綜合分析")

        system_prompt = (
            f"你是一位頂尖的小說主編與文學總監。請根據整部小說的各章節分析紀錄與最終全景索引，"
            f"撰寫一份全面、深入且具備高度洞察力的「{task_name}總結報告」。"
        )

        # 動態分配摘要預算，防止超長篇（如十幾段至數十段）累計文本灌爆 Context Window
        num_chunks = len(chunk_results)
        header_reserve = 35  # 每段標題與格式保留字數
        per_chunk_content_budget = max(50, (self.MAX_SYNTHESIS_SUMMARY_CHARS // max(num_chunks, 1)) - header_reserve)

        summaries = []
        for r in chunk_results:
            analysis_text = r.partial_analysis.strip()
            if len(analysis_text) > per_chunk_content_budget:
                short_analysis = analysis_text[:per_chunk_content_budget].rstrip() + "..."
            else:
                short_analysis = analysis_text
            summaries.append(f"#### 第 {r.chunk_index}/{r.total_chunks} 階段核心要點：\n{short_analysis}\n")

        all_summaries_text = "\n".join(summaries)
        if len(all_summaries_text) > self.MAX_SYNTHESIS_SUMMARY_CHARS:
            all_summaries_text = all_summaries_text[:self.MAX_SYNTHESIS_SUMMARY_CHARS] + "\n...（以下各階段要點已在全景索引中彙整）"

        # 輸出高密度、全景式人物與設定清單
        state_text = self._format_final_state_summary(final_state)

        extra_req = ""
        if task_type == "character":
            extra_req = (
                "4. 針對登場核心角色，依據全景索引嚴格使用以下格式獨立輸出角色卡：\n"
                "===CHARACTER_START===\n"
                "【角色姓名】角色名字\n"
                "【外觀年齡】推測的外觀年齡\n"
                "【外觀特徵】外貌特徵與著裝氣質描述\n"
                "【人物側寫】個性、人格特質與背景小傳\n"
                "【已知行動】已知的行動軌跡與決策事蹟\n"
                "【人事物關聯】相關的人、事、物\n"
                "===CHARACTER_END===\n"
                "（重複上述區塊輸出多位主要角色）\n\n"
                "5. 在所有角色輸出完畢後，獨立輸出角色關係網：\n"
                "===RELATIONSHIP_START===\n"
                "【卡片標題】全景角色關係網梳理\n"
                "【關係梳理】陣營勢力、角色核心矛盾、情感牽絆與互動脈絡深度分析\n"
                "===RELATIONSHIP_END===\n"
            )

        user_content = (
            f"### 【長篇總結任務】：整篇共計約 {total_chars} 字，分為 {len(chunk_results)} 階段完成逐段分析。\n\n"
            f"### 【各階段核心分析精華】：\n{all_summaries_text}\n\n"
            f"### 【最終全域完整索引（人物全景與世界觀）】：\n{state_text}\n\n"
            f"### 【報告撰寫要求】：\n"
            f"請結合上述所有分析與全景索引，產出最終的完整結構化報告。要求：\n"
            f"1. 宏觀全局視野，避免單純重複各段細節。\n"
            f"2. 結構清晰分明，使用明確小標題與條列。\n"
            f"3. 提供具體深入的文學評論、關鍵洞察與實質最佳化建議。\n"
            f"{extra_req}"
        )

        return system_prompt, user_content

    def _format_final_state_summary(self, state: CompactState) -> str:
        """將最終全域狀態格式化為高密度索引，展示完整人物庫與設定庫。"""
        lines = []
        if state.characters:
            lines.append("【登場人物全景索引】")
            # 依提及次數降冪排序，確保高頻核心角色優先
            sorted_chars = sorted(
                state.characters.items(),
                key=lambda x: state.character_mentions.get(x[0].strip("*_#[] "), 1),
                reverse=True
            )
            for name, desc in sorted_chars:
                clean_name = name.strip("*_#[] ")
                freq = state.character_mentions.get(clean_name, 1)
                short_desc = desc[:35] + "..." if len(desc) > 35 else desc
                lines.append(f"- {clean_name}（出場 {freq} 次）：{short_desc}")

        if state.world_elements:
            lines.append("\n【核心世界觀與設定】")
            for term, desc in list(state.world_elements.items())[:20]:
                clean_term = term.strip("*_#[] ")
                short_desc = desc[:30] + "..." if len(desc) > 30 else desc
                lines.append(f"- {clean_term}：{short_desc}")

        if state.timeline_events:
            lines.append("\n【重大里程碑事件】")
            for evt in state.timeline_events[-12:]:
                short_evt = evt[:35] + "..." if len(evt) > 35 else evt
                lines.append(f"- {short_evt}")

        if state.unresolved_threads:
            lines.append("\n【關鍵伏筆與未解懸念】")
            for thread in state.unresolved_threads[-6:]:
                short_thread = thread[:30] + "..." if len(thread) > 30 else thread
                lines.append(f"- {short_thread}")

        return "\n".join(lines) if lines else state.to_summary_text()

    def analyze_long_text(self, text: str, task_type: str,
                          custom_prompt: str = "",
                          progress_callback: Optional[Callable[[int, int, str], None]] = None,
                          is_cancelled_callback: Optional[Callable[[], bool]] = None) -> LongTextAnalysisResult:
        """執行長文 HRCI 捲動壓縮分析完整管線。

        Args:
            text: 待分析之完整小說文本
            task_type: 分析類型 (impression, character, world, timeline)
            custom_prompt: 自訂額外提示詞
            progress_callback: 進度回報回呼 (current_step, total_steps, message)
            is_cancelled_callback: 是否已取消之回呼

        Returns:
            LongTextAnalysisResult 物件
        """
        if not self.ai_caller:
            raise ValueError("未設定 ai_caller，無法執行 AI 分析。")

        try:
            dynamic_chunk_size, max_tokens = self.calculate_dynamic_chunk_size()
            if self._custom_chunk_size is not None:
                self.chunk_size = min(self._custom_chunk_size, dynamic_chunk_size)
            else:
                self.chunk_size = dynamic_chunk_size
        except MemoryError as e:
            if is_cancelled_callback and is_cancelled_callback():
                raise InterruptedError("使用者已取消長文分析。")
            raise e

        chunks = self.split_into_chunks(text)
        total_chunks = len(chunks)
        # 總步數 = 分塊分析數 + 1 (最終全域整合)
        total_steps = total_chunks + 1 if total_chunks > 1 else 1

        if progress_callback:
            progress_callback(1, total_steps, f"準備進行分析，全文共 {len(text)} 字（拆分為 {total_chunks} 個語義區塊）...")

        state = CompactState()
        chunk_results: List[ChunkAnalysisResult] = []

        # 逐段捲動壓縮分析
        for idx, chunk in enumerate(chunks):
            if is_cancelled_callback and is_cancelled_callback():
                raise InterruptedError("使用者已取消長文分析。")

            chunk_idx = idx + 1
            if progress_callback:
                progress_callback(
                    chunk_idx,
                    total_steps,
                    f"✨ 正在分析長文（第 {chunk_idx}/{total_chunks} 段，約 {len(chunk)} 字）..."
                )

            # 動態推算剩餘可用的 Token 預算給履歷使用
            # 扣除: 本段文字 token + 輸出預留 1500 + 系統與框架字數預估 300
            chunk_token_count = self.token_counter(chunk)

            # Runtime Token 硬上限攔截：若 chunk_text 自身超出安全上限（max_tokens 的 75%），
            # 主動截斷以防止 Prompt 組裝後超出 Context Window
            safe_chunk_token_limit = int(max_tokens * 0.75)
            if chunk_token_count > safe_chunk_token_limit:
                # 保守估算：每個中文字約 2.5 token，反推安全字數上限
                safe_char_limit = int(safe_chunk_token_limit / 2.5)
                chunk = chunk[:safe_char_limit] + "\n\n【注意：本段因長度超出安全上限已截斷，以下為前段核心內容，請基於已有內容進行分析。】"
                chunk_token_count = self.token_counter(chunk)

            available_history_budget = max_tokens - (chunk_token_count + 1500 + 300)
            if available_history_budget < 200:
                available_history_budget = 200

            sys_prompt, user_prompt = self.build_chunk_prompt(
                task_type=task_type,
                chunk_text=chunk,
                chunk_index=chunk_idx,
                total_chunks=total_chunks,
                state=state,
                custom_prompt=custom_prompt,
                token_budget=available_history_budget
            )

            # 呼叫 LLM
            raw_response = self.ai_caller(sys_prompt, user_prompt)

            partial_analysis, new_state = self.parse_chunk_response(raw_response, state)

            chunk_res = ChunkAnalysisResult(
                chunk_index=chunk_idx,
                total_chunks=total_chunks,
                char_count=len(chunk),
                partial_analysis=partial_analysis,
                updated_state=new_state,
                raw_response=raw_response
            )
            chunk_results.append(chunk_res)
            state = new_state  # 捲動轉移狀態

        # 如果只有單一分塊，直接以該分塊的結論作為最終結果
        if total_chunks == 1:
            return LongTextAnalysisResult(
                task_type=task_type,
                total_chunks=1,
                total_chars=len(text),
                final_synthesis=chunk_results[0].partial_analysis,
                chunk_results=chunk_results,
                final_state=state
            )

        # 進入最終階段：全域整合
        if is_cancelled_callback and is_cancelled_callback():
            raise InterruptedError("使用者已取消長文分析。")

        if progress_callback:
            progress_callback(
                total_steps,
                total_steps,
                f"✨ 正在整合全書總體分析報告（彙整 {total_chunks} 段分析成果）..."
            )

        sys_synth, user_synth = self.build_synthesis_prompt(
            task_type=task_type,
            final_state=state,
            chunk_results=chunk_results,
            total_chars=len(text),
            custom_prompt=custom_prompt
        )

        final_synthesis_report = self.ai_caller(sys_synth, user_synth)

        return LongTextAnalysisResult(
            task_type=task_type,
            total_chunks=total_chunks,
            total_chars=len(text),
            final_synthesis=final_synthesis_report,
            chunk_results=chunk_results,
            final_state=state
        )
