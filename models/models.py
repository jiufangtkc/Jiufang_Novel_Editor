from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal
import uuid

@dataclass
class ProofreadIgnoredRule:
    rule_type: str       # "typo", "usage", "suggestion"
    target_word: str     # 被忽略的字詞或規則
    created_at: str      # 建立時間 (ISO)

@dataclass
class ProofreadResult:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: str = "typo"   # "typo", "usage", "suggestion"
    node_id: str = ""        # 所在章節 ID
    chapter_name: str = ""   # 所在章節名稱
    char_offset: int = 0
    match_len: int = 0
    original_text: str = ""
    suggestion: str = ""
    reason: str = ""
    status: str = "pending"  # "pending", "done", "ignored"
    created_at: str = ""

@dataclass
class ProjectInfo:
    title: str = "未命名專案"
    logline: str = ""
    global_font_family: str = "Iansui"
    global_font_size: int = 12
    editor_font_family: str = "Iansui"
    editor_font_size: int = 12
    target_word_count: int = 100000
    daily_target_word_count: int = 1000
    expanded_categories: Optional[List[str]] = None

@dataclass
class CardNode:
    title: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    color: str = "#3C3F41" # Default dark color
    is_collapsed: bool = False
    children: List['CardNode'] = field(default_factory=list)

@dataclass
class AIChatMessage:
    """AI 對話紀錄中的單則訊息。"""
    role: str   # "user" 或 "assistant"
    content: str = ""

@dataclass
class AIChatRecord:
    """儲存一次完整 AI 對話紀錄，以 CardNode 形式存放在 project_cards['ai_chat'] 中。"""
    title: str           # 對話標題，預設為建立時間
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""    # 純文字摘要或完整對話內容（序列化後的文字）
    color: str = "#1a2a3a"
    is_collapsed: bool = False
    children: List[CardNode] = field(default_factory=list)  # 不使用子卡片

    def to_card_node(self) -> CardNode:
        """將 AIChatRecord 轉換為 CardNode 以統一存放在 project_cards 中。"""
        return CardNode(
            title=self.title,
            id=self.id,
            content=self.content,
            color=self.color,
            is_collapsed=self.is_collapsed,
            children=[]
        )

# 內建分類清單（固定，AI 功能僅支援此列表）
BUILTIN_CATEGORIES: List[str] = ["summary", "character", "world", "timeline", "ai_chat"]

# 分類的顯示名稱對應
CATEGORY_DISPLAY_NAMES: Dict[str, str] = {
    "summary":   "本書綱要",
    "character": "角色",
    "world":     "世界觀",
    "timeline":  "時間軸",
    "ai_chat":   "AI 對話紀錄",
}

# 分類對應的圖示（使用 Unicode 字符）
CATEGORY_ICONS: Dict[str, str] = {
    "summary":   "📖",
    "character": "👤",
    "world":     "🌍",
    "timeline":  "📅",
    "ai_chat":   "💬",
    "_custom":   "📁",  # 使用者自訂分類的預設圖示
}

# 進度標記對應的色碼
MARK_COLOR_MAP: Dict[str, str] = {
    "Draft": "#808080",
    "1st Edit": "#0000FF",
    "2nd Edit": "#FFFF00",
    "Final": "#008000",
    "Discarded": "#FF0000",
}

@dataclass
class ChapterNode:
    name: str
    node_type: Literal["folder", "file", "scene"]
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    mark: str = "Draft"  # Draft, 1st Edit, 2nd Edit, Final, Discarded
    scene_summary: str = ""     # 場景摘要（scene 節點專用）
    scene_pov: str = ""         # 視角角色（scene 節點專用）
    scene_location: str = ""    # 場景地點（scene 節點專用）
    is_expanded: bool = True
    children: List['ChapterNode'] = field(default_factory=list)

@dataclass
class WritingLogEntry:
    date: str
    duration: int = 0
    word_count: int = 0
    ai_continuation_count: int = 0    # AI 續寫次數
    ai_continuation_chars: int = 0    # AI 續寫字數
    ai_chat_count: int = 0            # AI 對話次數
    ai_details: Dict[str, int] = field(default_factory=dict)  # AI 細部功能面向次數 (例: chat, character, proofread 等)
    # [已廢棄] 僅供舊版 SQLite/JSON 向後相容反序列化，新業務邏輯與統計不再使用
    paste_large_count: int = 0
    delete_large_count: int = 0


@dataclass
class JneProject:
    project_info: ProjectInfo = field(default_factory=ProjectInfo)
    tree: List[ChapterNode] = field(default_factory=list)
    current_theme: str = "dark"
    writing_logs: List[WritingLogEntry] = field(default_factory=list)
    # project_cards 的 key 為分類名稱（英文），值為 CardNode 列表。
    # 內建分類：summary, character, world, timeline, ai_chat
    # 使用者可新增任意自訂分類 key，但 AI 功能僅支援內建分類。
    # category_order 記錄分類的排列順序（含使用者自訂分類）
    project_cards: Dict[str, List[CardNode]] = field(default_factory=lambda: {
        "summary": [],
        "character": [],
        "world": [],
        "timeline": [],
        "ai_chat": [],
    })
    # 分類排列順序（支援使用者自訂分類插入）
    category_order: List[str] = field(default_factory=lambda: [
        "summary", "character", "world", "timeline", "ai_chat"
    ])


@dataclass
class CompactState:
    """HRCI 捲動壓縮狀態物件（雙軌索引資料結構）"""
    characters: Dict[str, str] = field(default_factory=dict)       # 人物名稱: 特徵/當前狀態（全局無上限儲存）
    character_mentions: Dict[str, int] = field(default_factory=dict)  # 人物累計提及頻次
    world_elements: Dict[str, str] = field(default_factory=dict)   # 世界觀名詞/設定: 說明（全局無上限儲存）
    timeline_events: List[str] = field(default_factory=list)       # 已發生的關鍵事件節點
    unresolved_threads: List[str] = field(default_factory=list)    # 當前懸念與伏筆
    current_scene_context: str = ""                                # 當前區塊結尾場景與狀態

    def get_dynamic_summary(self, chunk_text: str, token_budget: int, token_counter) -> str:
        """依據 Token 預算，由近至遠動態抓取歷史摘要，確保不超出預算上限。
        此為暫時性的視圖壓縮（Transient View Compression），不影響原始資料庫中的紀錄。
        """
        lines = []
        current_tokens = 0
        
        def add_section(title, items, is_kv=False, is_event=False):
            nonlocal current_tokens
            if not items:
                return
            
            section_lines = [f"【{title}】"]
            section_tokens = token_counter(section_lines[0] + "\n")
            
            for item in items:
                if is_kv:
                    k, v = item
                    line = f"- {k}：{v}"
                else:
                    line = f"- {item}"
                
                line_tok = token_counter(line + "\n")
                if current_tokens + section_tokens + line_tok > token_budget:
                    # 預算已滿，不再加入此分類的後續項目
                    break
                
                section_lines.append(line)
                section_tokens += line_tok
                
            if len(section_lines) > 1:
                lines.extend(section_lines)
                current_tokens += section_tokens

        # 5. 上段結尾場景 (最優先)
        if self.current_scene_context:
            scene = f"【前段結尾場景】\n{self.current_scene_context}"
            scene_tok = token_counter(scene + "\n")
            if current_tokens + scene_tok <= token_budget:
                lines.append(scene)
                current_tokens += scene_tok

        # 從 chunk_text 抽取長度 2+ 的中文詞彙，用於事件/懸念命中篩選
        def _extract_keywords(text: str):
            """從文本中抽取長度 2+ 的連續中文字符序列（粗略關鍵詞）"""
            import re as _re
            return set(_re.findall(r'[\u4e00-\u9fff]{2,}', text))

        chunk_keywords = _extract_keywords(chunk_text) if chunk_text else set()

        def _sort_by_hit(items):
            """將事件描述中有詞彙出現於 chunk_text 的項目優先排到前面，未命中者仍保持由新到舊順序"""
            if not chunk_text:
                return list(items)

            def _item_hits(item: str) -> bool:
                """判斷事件描述中是否有任何連續 2 字中文 bigram 出現在 chunk_text 中"""
                import re as _re2
                chinese_chars = _re2.findall(r'[\u4e00-\u9fff]', item)
                # 產生所有連續 2 字 bigram
                bigrams = [''.join(chinese_chars[i:i+2]) for i in range(len(chinese_chars) - 1)]
                return any(bg in chunk_text for bg in bigrams)

            hits = [item for item in items if _item_hits(item)]
            non_hits = [item for item in items if not _item_hits(item)]
            return hits + non_hits

        # 4. 當前未解懸念 (命中優先，其次由新到舊)
        sorted_threads = _sort_by_hit(reversed(self.unresolved_threads))
        add_section("當前核心伏筆", sorted_threads, is_event=True)

        # 3. 關鍵事件脈絡 (命中優先，其次由新到舊)
        sorted_events = _sort_by_hit(reversed(self.timeline_events))
        add_section("近期重大事件", sorted_events, is_event=True)

        # 1. 人物動態命中篩選
        if self.characters:
            hit_chars = []
            non_hit_chars = []
            for name, desc in self.characters.items():
                clean_name = name.strip("*_[] ")
                if chunk_text and clean_name and clean_name in chunk_text:
                    hit_chars.append((name, desc, self.character_mentions.get(name, 1)))
                else:
                    non_hit_chars.append((name, desc, self.character_mentions.get(name, 1)))
            
            selected_chars = list(hit_chars)
            if len(selected_chars) < 3:
                non_hit_chars.sort(key=lambda x: x[2], reverse=True)
                for item in non_hit_chars:
                    if len(selected_chars) >= 5:
                        break
                    selected_chars.append(item)
            
            kv_chars = [(name, desc[:35] + "..." if len(desc) > 35 else desc) for name, desc, _ in selected_chars]
            add_section("本段相關人物狀態", kv_chars, is_kv=True)

        # 2. 世界觀設定動態命中篩選
        if self.world_elements:
            hit_elements = []
            non_hit_elements = []
            for term, desc in self.world_elements.items():
                clean_term = term.strip("*_[] ")
                if chunk_text and clean_term and clean_term in chunk_text:
                    hit_elements.append((term, desc))
                else:
                    non_hit_elements.append((term, desc))
            
            selected_elements = list(hit_elements)
            if len(selected_elements) < 2 and non_hit_elements:
                selected_elements.extend(non_hit_elements[-2:])
            kv_elements = [(term, desc[:30] + "..." if len(desc) > 30 else desc) for term, desc in selected_elements]
            add_section("相關世界觀設定", kv_elements, is_kv=True)

        result = "\n".join(lines)
        if not result:
            return "（目前為初始狀態，尚無歷史摘要索引）"

        return result

    def get_relevant_summary(self, chunk_text: str = "", max_chars: int = 600) -> str:
        """為了向下相容，將原本的調用轉發給 get_dynamic_summary 並受 max_chars 約束"""
        res = self.get_dynamic_summary(
            chunk_text=chunk_text, 
            token_budget=int(max_chars * 1.5), 
            token_counter=lambda x: int(len(x) * 1.5)
        )
        if len(res) > max_chars:
            return res[:max_chars] + "\n..."
        return res

    def to_summary_text(self) -> str:
        """將狀態序列化為精簡摘要文字（向後相容預設調用）"""
        return self.get_relevant_summary(chunk_text="", max_chars=800)


@dataclass
class ChunkAnalysisResult:
    """單一分塊的分析結果"""
    chunk_index: int
    total_chunks: int
    char_count: int
    partial_analysis: str
    updated_state: CompactState = field(default_factory=CompactState)
    raw_response: str = ""


@dataclass
class LongTextAnalysisResult:
    """長文捲動分析的完整彙整成果"""
    task_type: str
    total_chunks: int
    total_chars: int
    final_synthesis: str
    chunk_results: List[ChunkAnalysisResult] = field(default_factory=list)
    final_state: CompactState = field(default_factory=CompactState)

