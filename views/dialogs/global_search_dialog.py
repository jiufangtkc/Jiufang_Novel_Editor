from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QToolButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt, pyqtSignal
from utils.font_manager import FontManager

class GlobalSearchDialog(QDialog):
    """跨章節全文搜尋對話框。"""
    # 傳遞 (node_id, line_number, char_offset, match_length)
    signal_navigate_to_match = pyqtSignal(str, int, int, int)
    signal_search_requested = pyqtSignal(str, bool, bool, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("跨章節全文搜尋 (Ctrl+Shift+F)")
        self.resize(750, 480)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #cccccc;
            }
            QLineEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3c3c3c;
                padding: 5px 8px;
                border-radius: 4px;
                selection-background-color: #264f78;
            }
            QLineEdit:focus {
                border: 1px solid #007acc;
            }
            QPushButton, QToolButton {
                background-color: #333333;
                color: #cccccc;
                border: 1px solid #555555;
                padding: 4px 10px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover, QToolButton:hover {
                background-color: #444444;
                color: #ffffff;
            }
            QPushButton:pressed, QToolButton:pressed {
                background-color: #007acc;
                color: #ffffff;
            }
            QToolButton:checked {
                background-color: #0e639c;
                border-color: #1177bb;
                color: #ffffff;
            }
            QTableWidget {
                background-color: #252526;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                gridline-color: #2d2d2d;
                selection-background-color: #094771;
                selection-color: #ffffff;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #cccccc;
                padding: 4px;
                border: 1px solid #3c3c3c;
                font-weight: bold;
            }
            QLabel {
                color: #aaaaaa;
                font-size: 11px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 頂部搜尋列
        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("輸入要在全文/所有章節中搜尋的文字...")
        self.input_search.setFont(FontManager.get_font(size=11))
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
        self.btn_search.setFont(FontManager.get_font(size=10, weight=QFont.Weight.Bold))
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
        self.results_table.setHorizontalHeaderLabels(["章節路徑", "行號", "相符內容預覽"])
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.results_table.setColumnWidth(0, 180)
        self.results_table.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.results_table, 1)

        # 底部狀態列與動作
        bottom_row = QHBoxLayout()
        self.lbl_status = QLabel("請輸入關鍵字並點擊「搜尋全文」")
        self.btn_jump = QPushButton("跳轉至目標 (Enter)")
        self.btn_jump.clicked.connect(self._jump_to_selected)
        self.btn_close = QPushButton("關閉 (Esc)")
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
