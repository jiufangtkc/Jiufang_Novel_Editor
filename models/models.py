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
    paste_large_count: int = 0        # 大量貼上文字次數（短時間超過300字）
    delete_large_count: int = 0       # 大量刪除文字次數（短時間超過300字）


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
    characters: Dict[str, str] = field(default_factory=dict)       # 人物名稱: 特徵/當前狀態
    world_elements: Dict[str, str] = field(default_factory=dict)   # 世界觀名詞/設定: 說明
    timeline_events: List[str] = field(default_factory=list)       # 已發生的關鍵事件節點
    unresolved_threads: List[str] = field(default_factory=list)    # 當前懸念與伏筆
    current_scene_context: str = ""                                # 當前區塊結尾場景與狀態

    def to_summary_text(self) -> str:
        """將狀態序列化為精簡 Markdown 摘要文字供 LLM 上下文使用"""
        lines = []
        if self.characters:
            lines.append("【已知人物與狀態】")
            for name, desc in list(self.characters.items())[:15]:
                lines.append(f"- {name}：{desc}")
        if self.world_elements:
            lines.append("【核心世界觀設定】")
            for term, desc in list(self.world_elements.items())[:10]:
                lines.append(f"- {term}：{desc}")
        if self.timeline_events:
            lines.append("【主要事件脈絡】")
            for evt in self.timeline_events[-8:]:
                lines.append(f"- {evt}")
        if self.unresolved_threads:
            lines.append("【當前伏筆與懸念】")
            for thread in self.unresolved_threads[-5:]:
                lines.append(f"- {thread}")
        if self.current_scene_context:
            lines.append(f"【前段結尾場景】\n{self.current_scene_context}")

        return "\n".join(lines) if lines else "（目前為初始狀態，尚無歷史摘要索引）"


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

