from typing import Dict, List, Any, Optional
from models.models import CATEGORY_DISPLAY_NAMES


class DatasetFormatter:
    """資料集結構化文字格式化工具。
    
    將作家在右側面板建立的角色、世界觀、綱要等樹狀卡片資料，
    轉換為結構清晰、層次分明的 Markdown 文字，以供匯出為閱讀檔（.md 或 .docx）。
    
    支援動態標題降級機制：
    - 分類層：Level 1 (# 分類名稱)
    - 第一層卡片：Level 2 (## 卡片名稱)
    - 第二層卡片：Level 3 (### 卡片名稱)
    - 第三層及更深層（Depth >= 4）：動態降級為帶有麵包屑路徑的清單與引言區塊，
      避免產生過深的 Heading 破壞大綱結構與文書排版。
    """

    @classmethod
    def format_to_markdown(
        cls,
        cards_data: Dict[str, List[Dict[str, Any]]],
        categories_meta: Optional[Dict[str, str]] = None,
        book_title: str = ""
    ) -> str:
        """將卡片資料字典轉換為 Markdown 字串。
        
        :param cards_data: 分類對應之卡片字典列表，格式如 {'character': [{'title': '...', 'content': '...', 'children': [...]}]}
        :param categories_meta: 分類顯示名稱對照字典（選填）
        :param book_title: 作品名稱（選填，作為總標題）
        :return: 格式化後的 Markdown 字串
        """
        lines: List[str] = []
        meta = {**CATEGORY_DISPLAY_NAMES, **(categories_meta or {})}

        if book_title:
            lines.append(f"# {book_title} — 設定資料集")
            lines.append("")
            lines.append("---")
            lines.append("")

        categories = list(cards_data.keys())
        first_category = True

        for cat_key in categories:
            cards = cards_data.get(cat_key, [])
            if not cards:
                continue

            if not first_category:
                lines.append("")
                lines.append("---")
                lines.append("")
            else:
                first_category = False

            cat_display_name = meta.get(cat_key, cat_key)
            lines.append(f"# {cat_display_name}")
            lines.append("")

            for card in cards:
                cls._format_card_node(card, depth=2, breadcrumbs=[], lines=lines)

        return "\n".join(lines).strip() + "\n"

    @classmethod
    def _format_card_node(
        cls,
        card: Dict[str, Any],
        depth: int,
        breadcrumbs: List[str],
        lines: List[str]
    ):
        """遞迴處理單一卡片節點及其子節點。
        
        :param card: 卡片資料字典
        :param depth: 當前深度（分類為 1，頂層卡片為 2，第二層為 3，第三層及以上 >= 4）
        :param breadcrumbs: 從根節點向下的父卡片名稱列表
        :param lines: 輸出的行緩衝區
        """
        title = (card.get("title") or "未命名卡片").strip()
        content = (card.get("content") or "").strip()
        children = card.get("children") or []

        if depth <= 3:
            # 正常使用 Markdown 標題層級
            prefix = "#" * depth
            lines.append(f"{prefix} {title}")
            lines.append("")

            if content:
                for c_line in content.splitlines():
                    lines.append(c_line)
                lines.append("")
        else:
            # 深度 >= 4 觸發動態降級：使用麵包屑路徑標註層級
            path_str = " > ".join(breadcrumbs)
            lines.append(f"* **[{path_str}] {title}**")
            lines.append("")

            if content:
                for c_line in content.splitlines():
                    lines.append(f"  > {c_line}")
                lines.append("")

        # 遞迴處理子卡片
        next_breadcrumbs = breadcrumbs + [title]
        for child in children:
            cls._format_card_node(
                child,
                depth=depth + 1,
                breadcrumbs=next_breadcrumbs,
                lines=lines
            )
