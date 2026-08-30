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
    children: List['ChapterNode'] = field(default_factory=list)

@dataclass
class WritingLogEntry:
    date: str
    duration: int = 0
    word_count: int = 0
    ai_continuation_count: int = 0    # AI 續寫次數
    ai_continuation_chars: int = 0    # AI 續寫字數
    ai_chat_count: int = 0            # AI 對話次數


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
