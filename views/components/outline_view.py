import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTreeWidget, QTreeWidgetItem, QHeaderView, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QAction, QColor, QBrush
from utils.font_manager import FontManager
from utils.theme_manager import create_custom_icon

class OutlineView(QWidget):
    """全書大綱鳥瞰視圖元件（Outline View）。
    
    以樹狀表格呈現所有卷/章/節結構、標記狀態、字數與內文摘要，
    支援即時搜尋過濾、展開/收合與雙擊跳轉編輯。
    """
    signal_chapter_selected = pyqtSignal(str)       # 傳遞 chapter_id
    signal_back_to_editor = pyqtSignal()            # 點擊返回寫作模式
    signal_mark_changed = pyqtSignal(str, str)      # (chapter_id, mark_value)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scale_factor = getattr(parent, "scale_factor", 1.0) if parent else 1.0
        self.init_ui()
        if self.scale_factor != 1.0:
            self.update_scale(self.scale_factor)

    def minimumSizeHint(self):
        from PyQt6.QtCore import QSize
        return QSize(200, 200)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 頂部控制工具列
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self.btn_back = QPushButton("✍️ 返回寫作")
        self.btn_back.setFont(FontManager.get_font(size=9, weight=QFont.Weight.Bold))
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.clicked.connect(self.signal_back_to_editor.emit)
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: #0e639c;
                color: #ffffff;
                border: 1px solid #1177bb;
                padding: 4px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
        """)
        header_layout.addWidget(self.btn_back)

        self.lbl_title = QLabel("大綱模式 (Outline View)")
        self.lbl_title.setFont(FontManager.get_font(size=13, weight=QFont.Weight.Bold))
        header_layout.addWidget(self.lbl_title)

        header_layout.addSpacing(15)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜尋大綱章節或摘要...")
        self.search_input.setFont(FontManager.get_font(size=9))
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.filter_items)
        self.search_input.setFixedWidth(240)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                color: #e3e3e3;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 3px 6px;
            }
            QLineEdit:focus {
                border: 1px solid #007acc;
            }
        """)
        header_layout.addWidget(self.search_input)

        self.btn_expand_all = QPushButton("全部展開")
        self.btn_expand_all.setFont(FontManager.get_font(size=9))
        self.btn_expand_all.clicked.connect(self.expand_all)
        header_layout.addWidget(self.btn_expand_all)

        self.btn_collapse_all = QPushButton("全部收合")
        self.btn_collapse_all.setFont(FontManager.get_font(size=9))
        self.btn_collapse_all.clicked.connect(self.collapse_all)
        header_layout.addWidget(self.btn_collapse_all)

        header_layout.addStretch()

        self.lbl_stats = QLabel("統計: 0 卷 0 章 | 總計: 0 字")
        self.lbl_stats.setFont(FontManager.get_font(size=9))
        self.lbl_stats.setStyleSheet("color: #888888;")
        header_layout.addWidget(self.lbl_stats)

        layout.addWidget(header_widget)

        # 核心樹狀表格
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["章節結構", "標記狀態", "字數", "內容摘要"])
        self.tree_widget.setFont(FontManager.get_font(size=10))
        self.tree_widget.setAlternatingRowColors(True)
        self.tree_widget.setAnimated(True)
        self.tree_widget.setIndentation(20)
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self._show_context_menu)
        self.tree_widget.itemDoubleClicked.connect(self._on_item_double_clicked)

        header = self.tree_widget.header()
        header.setFont(FontManager.get_font(size=10, weight=QFont.Weight.Bold))
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tree_widget.setColumnWidth(0, 280)
        self.tree_widget.setColumnWidth(1, 100)
        self.tree_widget.setColumnWidth(2, 90)

        self.tree_widget.setStyleSheet("""
            QTreeWidget {
                background-color: #1e1e1e;
                alternate-background-color: #252526;
                color: #e3e3e3;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
            }
            QTreeWidget::item {
                padding: 4px 2px;
            }
            QTreeWidget::item:selected {
                background-color: #094771;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #cccccc;
                padding: 4px 6px;
                border: 1px solid #3d3d3d;
            }
        """)

        layout.addWidget(self.tree_widget, 1)

    def _strip_markdown_tags(self, text: str) -> str:
        """過濾 HTML / Markdown 標記，取得純文字摘要。"""
        if not text:
            return ""
        # 移除 HTML 標籤
        clean = re.sub(r'<[^>]+>', ' ', text)
        # 移除 Markdown 標題符號、粗體、斜體等
        clean = re.sub(r'#+\s*', '', clean)
        clean = re.sub(r'[*_~`]', '', clean)
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean

    def _format_mark(self, mark_str: str) -> tuple:
        """轉換標記名稱與對應文字色。"""
        mark_map = {
            "None": ("草稿", "#888888"),
            "Draft": ("草稿", "#888888"),
            "1st Edit": ("一校", "#569cd6"),
            "2nd Edit": ("二校", "#dcdcaa"),
            "Final": ("完稿", "#4ec9b0"),
            "Discarded": ("廢稿", "#f44747")
        }
        return mark_map.get(mark_str, ("草稿", "#888888"))

    def populate_from_tree(self, source_tree: QTreeWidget, folder_color="#e5c07b", file_color="#dcdcdc", scale_factor=None):
        """從主視窗的章節樹同步數據並建構大綱視圖。"""
        if scale_factor is None:
            scale_factor = self.scale_factor
        self.tree_widget.clear()
        
        folder_count = 0
        file_count = 0
        scene_count = 0
        total_word_count = 0

        def _copy_items(source_parent_item, target_parent_item):
            nonlocal folder_count, file_count, scene_count, total_word_count
            count = source_parent_item.childCount() if source_parent_item else source_tree.topLevelItemCount()
            for i in range(count):
                src_item = source_parent_item.child(i) if source_parent_item else source_tree.topLevelItem(i)
                data = src_item.data(0, Qt.ItemDataRole.UserRole) or {}
                node_type = data.get("type", "file")
                item_id = data.get("id", "")
                title = src_item.text(0)

                out_item = QTreeWidgetItem()
                out_item.setText(0, title)
                out_item.setData(0, Qt.ItemDataRole.UserRole, data)

                if node_type == "folder":
                    folder_count += 1
                    out_item.setIcon(0, create_custom_icon("folder", folder_color, scale_factor))
                    out_item.setText(1, "卷/目錄")
                    out_item.setText(2, "—")
                    out_item.setText(3, "")
                    out_item.setForeground(1, QBrush(QColor("#666666")))
                else:
                    if node_type == "scene":
                        scene_count += 1
                        out_item.setIcon(0, create_custom_icon("folder", "#4fa6ff", scale_factor))
                    else:
                        file_count += 1
                        out_item.setIcon(0, create_custom_icon("file", file_color, scale_factor))

                    mark_text, mark_color = self._format_mark(data.get("mark", "Draft"))
                    if node_type == "scene":
                        mark_text = f"🎬 {mark_text}"
                    out_item.setText(1, mark_text)
                    out_item.setForeground(1, QBrush(QColor(mark_color)))

                    raw_content = data.get("content", "")
                    clean_text = self._strip_markdown_tags(raw_content)
                    
                    # 計算中英文字數
                    c_chinese = len(re.findall(r'[\u4e00-\u9fa5]', clean_text))
                    c_english = len(re.findall(r'[a-zA-Z0-9]+', clean_text))
                    word_cnt = c_chinese + c_english
                    total_word_count += word_cnt

                    out_item.setText(2, f"{word_cnt:,}")
                    out_item.setTextAlignment(2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

                    # 摘要：若為幕且有 scene_summary 則優先顯示
                    scene_summary = data.get("scene_summary", "").strip() if node_type == "scene" else ""
                    if scene_summary:
                        summary = f"【幕】{scene_summary}"
                    else:
                        summary = clean_text[:100].replace("\n", " ") + ("..." if len(clean_text) > 100 else "")
                    out_item.setText(3, summary)

                if target_parent_item:
                    target_parent_item.addChild(out_item)
                else:
                    self.tree_widget.addTopLevelItem(out_item)

                out_item.setExpanded(True)
                _copy_items(src_item, out_item)

        _copy_items(None, None)
        if scene_count > 0:
            self.lbl_stats.setText(f"統計: {folder_count} 卷 {file_count} 章 {scene_count} 幕 | 總計: {total_word_count:,} 字")
        else:
            self.lbl_stats.setText(f"統計: {folder_count} 卷 {file_count} 章 | 總計: {total_word_count:,} 字")
        
        # 若有過濾字串則重新套用
        if self.search_input.text():
            self.filter_items(self.search_input.text())

    def expand_all(self):
        self.tree_widget.expandAll()

    def collapse_all(self):
        self.tree_widget.collapseAll()

    def filter_items(self, keyword: str):
        """根據關鍵字即時過濾大綱項目。"""
        keyword = keyword.strip().lower()

        def _filter(item: QTreeWidgetItem) -> bool:
            title = item.text(0).lower()
            mark = item.text(1).lower()
            summary = item.text(3).lower()
            matched = (keyword in title) or (keyword in mark) or (keyword in summary)

            child_matched = False
            for i in range(item.childCount()):
                if _filter(item.child(i)):
                    child_matched = True

            should_show = matched or child_matched
            item.setHidden(not should_show)
            if should_show and keyword:
                item.setExpanded(True)
            return should_show

        for i in range(self.tree_widget.topLevelItemCount()):
            _filter(self.tree_widget.topLevelItem(i))

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "file":
            item_id = data.get("id")
            if item_id:
                self.signal_chapter_selected.emit(item_id)

    def _show_context_menu(self, pos):
        item = self.tree_widget.itemAt(pos)
        if not item:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") != "file":
            return

        item_id = data.get("id")
        menu = QMenu(self)

        action_open = QAction("開啟寫作編輯 (Enter)", self)
        action_open.triggered.connect(lambda: self.signal_chapter_selected.emit(item_id))
        menu.addAction(action_open)
        menu.addSeparator()

        mark_menu = menu.addMenu("變更標記")
        marks = [
            ("草稿 (灰)", "Draft"),
            ("一次校稿 (藍)", "1st Edit"),
            ("二次校稿 (黃)", "2nd Edit"),
            ("完稿 (綠)", "Final"),
            ("廢稿 (紅)", "Discarded")
        ]
        for label, val in marks:
            act = QAction(label, self)
            act.triggered.connect(lambda checked, i_id=item_id, m=val: self.signal_mark_changed.emit(i_id, m))
            mark_menu.addAction(act)

        menu.exec(self.tree_widget.viewport().mapToGlobal(pos))

    def update_scale(self, scale: float):
        """依據縮放比例動態調整文字大小、欄寬、縮排與圖示。"""
        self.scale_factor = scale
        self.btn_back.setFont(FontManager.get_font(size=int(9 * scale), weight=QFont.Weight.Bold))
        self.lbl_title.setFont(FontManager.get_font(size=int(13 * scale), weight=QFont.Weight.Bold))
        self.search_input.setFont(FontManager.get_font(size=int(9 * scale)))
        self.search_input.setFixedWidth(int(240 * scale))
        self.btn_expand_all.setFont(FontManager.get_font(size=int(9 * scale)))
        self.btn_collapse_all.setFont(FontManager.get_font(size=int(9 * scale)))
        self.lbl_stats.setFont(FontManager.get_font(size=int(9 * scale)))

        self.tree_widget.setFont(FontManager.get_font(size=int(10 * scale)))
        self.tree_widget.header().setFont(FontManager.get_font(size=int(10 * scale), weight=QFont.Weight.Bold))
        self.tree_widget.setIndentation(int(20 * scale))
        self.tree_widget.setColumnWidth(0, int(280 * scale))
        self.tree_widget.setColumnWidth(1, int(100 * scale))
        self.tree_widget.setColumnWidth(2, int(90 * scale))

        def _update_icons(item):
            data = item.data(0, Qt.ItemDataRole.UserRole) or {}
            ntype = data.get("type", "file")
            if ntype == "folder":
                item.setIcon(0, create_custom_icon("folder", "#e5c07b", scale))
            elif ntype == "scene":
                item.setIcon(0, create_custom_icon("folder", "#4fa6ff", scale))
            else:
                item.setIcon(0, create_custom_icon("file", "#dcdcdc", scale))
            for i in range(item.childCount()):
                _update_icons(item.child(i))

        for i in range(self.tree_widget.topLevelItemCount()):
            _update_icons(self.tree_widget.topLevelItem(i))

