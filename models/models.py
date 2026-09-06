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

    def get_relevant_summary(self, chunk_text: str = "", max_chars: int = 600) -> str:
        """依據當前段落文字進行動態實體命中檢索，產出精準且短小的上下文摘要。

        即使全域儲存了上百個角色與設定，此方法透過正文掃描，僅挑選當前段落活躍的角色與元素，
        徹底突破實體個數限制，同時將 Context 長度嚴格限制在安全預算內。
        """
        lines = []

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

            # 若本段命中角色不足 3 位，自非命中角色中依熱度/最新狀態補充，最多總計 5 位
            selected_chars = list(hit_chars)
            if len(selected_chars) < 3:
                # 依頻次排序，優先取高頻角色或最新角色
                non_hit_chars.sort(key=lambda x: x[2], reverse=True)
                for item in non_hit_chars:
                    if len(selected_chars) >= 5:
                        break
                    selected_chars.append(item)

            if selected_chars:
                lines.append("【本段相關人物狀態】")
                for name, desc, _ in selected_chars[:6]:
                    # 單條條目保護：最長 35 字
                    short_desc = desc[:35] + "..." if len(desc) > 35 else desc
                    lines.append(f"- {name}：{short_desc}")

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
                # 補充最新的 2 個
                selected_elements.extend(non_hit_elements[-2:])

            if selected_elements:
                lines.append("【相關世界觀設定】")
                for term, desc in selected_elements[:4]:
                    short_desc = desc[:30] + "..." if len(desc) > 30 else desc
                    lines.append(f"- {term}：{short_desc}")

        # 3. 關鍵事件脈絡（保留最近 4 筆）
        if self.timeline_events:
            lines.append("【近期重大事件】")
            for evt in self.timeline_events[-4:]:
                short_evt = evt[:35] + "..." if len(evt) > 35 else evt
                lines.append(f"- {short_evt}")

        # 4. 當前未解懸念（保留最近 3 筆）
        if self.unresolved_threads:
            lines.append("【當前核心伏筆】")
            for thread in self.unresolved_threads[-3:]:
                short_thread = thread[:30] + "..." if len(thread) > 30 else thread
                lines.append(f"- {short_thread}")

        # 5. 上段結尾場景
        if self.current_scene_context:
            short_scene = self.current_scene_context[:60] + "..." if len(self.current_scene_context) > 60 else self.current_scene_context
            lines.append(f"【前段結尾場景】\n{short_scene}")

        result = "\n".join(lines)
        if not result:
            return "（目前為初始狀態，尚無歷史摘要索引）"

        # 安全閥截斷
        if len(result) > max_chars:
            return result[:max_chars] + "\n..."
        return result

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

