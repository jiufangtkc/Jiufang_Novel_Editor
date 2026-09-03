from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QToolButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt, pyqtSignal
from utils.font_manager import FontManager
from utils.theme_manager import ThemeManager

class GlobalSearchDialog(QDialog):
    """跨章節全文搜尋對話框。"""
    # 傳遞 (node_id, line_number, char_offset, match_length)
    signal_navigate_to_match = pyqtSignal(str, int, int, int)
    signal_search_requested = pyqtSignal(str, bool, bool, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("跨章節全文搜尋 (Ctrl+Shift+F)")
        self.scale_factor = getattr(parent, "scale_factor", 1.0) if parent else 1.0
        self.resize(int(750 * self.scale_factor), int(480 * self.scale_factor))
        self.init_ui()

    def init_ui(self):
        theme_name = "default"
        if self.parent() and hasattr(self.parent(), "current_theme"):
            theme_name = self.parent().current_theme
        theme_colors = ThemeManager.get_theme_colors(theme_name)
        main_bg = theme_colors.get("main_bg", "#1e1e1e")
        main_fg = theme_colors.get("main_fg", "#e3e3e3")
        tree_bg = theme_colors.get("tree_bg", "#252526")
        input_bg = theme_colors.get("input_bg", "#2d2d2d")
        input_fg = theme_colors.get("input_fg", "#ffffff")
        input_border = theme_colors.get("input_border", "#3c3c3c")
        accent = theme_colors.get("accent", "#007acc")
        btn_bg = theme_colors.get("btn_bg", "#333333")
        btn_fg = theme_colors.get("btn_fg", "#cccccc")
        btn_border = theme_colors.get("btn_border", "#555555")
        btn_hover = theme_colors.get("btn_hover_bg", "#444444")
        tree_sel = theme_colors.get("tree_item_selected_bg", "#094771")
        subtext = theme_colors.get("subtext_color", "#a0aec0")

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {main_bg};
                color: {main_fg};
            }}
            QLineEdit {{
                background-color: {input_bg};
                color: {input_fg};
                border: 1px solid {input_border};
                padding: 5px 8px;
                border-radius: 4px;
                selection-background-color: {tree_sel};
            }}
            QLineEdit:focus {{
                border: 1px solid {accent};
            }}
            QPushButton, QToolButton {{
                background-color: {btn_bg};
                color: {btn_fg};
                border: 1px solid {btn_border};
                padding: 4px 10px;
                border-radius: 4px;
                font-size: 11px;
            }}
            QPushButton:hover, QToolButton:hover {{
                background-color: {btn_hover};
                color: #ffffff;
            }}
            QPushButton:pressed, QToolButton:pressed {{
                background-color: {accent};
                color: #ffffff;
            }}
            QToolButton:checked {{
                background-color: {accent};
                border-color: {accent};
                color: #ffffff;
            }}
            QTableWidget {{
                background-color: {tree_bg};
                color: {main_fg};
                border: 1px solid {input_border};
                gridline-color: {input_border};
                selection-background-color: {tree_sel};
                selection-color: #ffffff;
            }}
            QHeaderView::section {{
                background-color: {theme_colors.get('header_bg', '#2d2d2d')};
                color: {main_fg};
                padding: 4px;
                border: 1px solid {input_border};
                font-weight: bold;
            }}
            QLabel {{
                color: {subtext};
                font-size: 11px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 頂部搜尋列
        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        sf = self.scale_factor
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("輸入要在全文/所有章節中搜尋的文字...")
        self.input_search.setFont(FontManager.get_font(size=int(11 * sf)))
        self.input_search.returnPressed.connect(self._trigger_search)

        self.btn_match_case = QToolButton()
        self.btn_match_case.setText("Aa")
        self.btn_match_case.setCheckable(True)
        self.btn_match_case.setToolTip("區分大小寫 (Match Case)")

        self.btn_whole_word = QToolButton()
        self.btn_whole_word.setText("\\b")
        self.btn_whole_word.setCheckable(True)
        self.btn_whole_word.setToolTip("全字相符 (Whole Word)")

        self.btn_regex = QToolButton()
        self.btn_regex.setText(".*")
        self.btn_regex.setCheckable(True)
        self.btn_regex.setToolTip("正規表達式 (Regular Expression)")

        self.btn_search = QPushButton("搜尋全文")
        self.btn_search.setFont(FontManager.get_font(size=int(10 * sf), weight=QFont.Weight.Bold))
        self.btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_search.clicked.connect(self._trigger_search)

        top_row.addWidget(self.input_search, 1)
        top_row.addWidget(self.btn_match_case)
        top_row.addWidget(self.btn_whole_word)
        top_row.addWidget(self.btn_regex)
        top_row.addWidget(self.btn_search)
        layout.addLayout(top_row)

        # 結果表格
        self.results_table = QTableWidget(0, 3)
        self.results_table.setFont(FontManager.get_font(size=int(9 * sf)))
        self.results_table.horizontalHeader().setFont(FontManager.get_font(size=int(9 * sf), weight=QFont.Weight.Bold))
        self.results_table.setHorizontalHeaderLabels(["章節路徑", "行號", "相符內容預覽"])
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.results_table.setColumnWidth(0, int(180 * sf))
        self.results_table.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.results_table, 1)

        # 底部狀態列與動作
        bottom_row = QHBoxLayout()
        self.lbl_status = QLabel("請輸入關鍵字並點擊「搜尋全文」")
        self.lbl_status.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_jump = QPushButton("跳轉至目標 (Enter)")
        self.btn_jump.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_jump.clicked.connect(self._jump_to_selected)
        self.btn_close = QPushButton("關閉 (Esc)")
        self.btn_close.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_close.clicked.connect(self.reject)

        bottom_row.addWidget(self.lbl_status, 1)
        bottom_row.addWidget(self.btn_jump)
        bottom_row.addWidget(self.btn_close)
        layout.addLayout(bottom_row)

        # 儲存結果 metadata: list of dict(node_id, line_num, char_offset, match_len)
        self.results_data = []

    def _trigger_search(self):
        text = self.input_search.text().strip()
        if not text:
            self.lbl_status.setText("請先輸入搜尋關鍵字。")
            return
        self.signal_search_requested.emit(
            self.input_search.text(),
            self.btn_match_case.isChecked(),
            self.btn_whole_word.isChecked(),
            self.btn_regex.isChecked()
        )

    def display_results(self, results: list):
        """顯示搜尋結果。
        results 格式: [
            {
                "node_id": str,
                "chapter_path": str,
                "line_num": int,
                "char_offset": int,
                "match_len": int,
                "snippet": str
            }, ...
        ]
        """
        self.results_data = results
        self.results_table.setRowCount(len(results))

        chapter_count = len(set(r["node_id"] for r in results))
        total_matches = len(results)

        if total_matches == 0:
            self.lbl_status.setText("搜尋完畢：未找到相符內容。")
            return

        self.lbl_status.setText(f"於 {chapter_count} 個章節中找到 {total_matches} 處相符項目。")

        for row_idx, item in enumerate(results):
            col_chapter = QTableWidgetItem(item["chapter_path"])
            col_line = QTableWidgetItem(str(item["line_num"]))
            col_line.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            col_snippet = QTableWidgetItem(item["snippet"])

            self.results_table.setItem(row_idx, 0, col_chapter)
            self.results_table.setItem(row_idx, 1, col_line)
            self.results_table.setItem(row_idx, 2, col_snippet)

        if total_matches > 0:
            self.results_table.selectRow(0)

    def _on_item_double_clicked(self, item):
        row = item.row()
        self._navigate_row(row)

    def _jump_to_selected(self):
        row = self.results_table.currentRow()
        if row >= 0 and row < len(self.results_data):
            self._navigate_row(row)

    def _navigate_row(self, row: int):
        if row < 0 or row >= len(self.results_data):
            return
        data = self.results_data[row]
        self.signal_navigate_to_match.emit(
            data["node_id"],
            data["line_num"],
            data["char_offset"],
            data["match_len"]
        )
        self.accept()

    def show_dialog(self, initial_text: str = ""):
        if initial_text:
            self.input_search.setText(initial_text)
            self.input_search.selectAll()
        self.input_search.setFocus()
        self.exec()
