from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QToolButton
)
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtCore import Qt, pyqtSignal
from utils.font_manager import FontManager

class CustomLineEdit(QLineEdit):
    """自訂輸入框，攔截特定按鍵信號（如 Escape、Shift+Enter 等）。"""
    signal_escape_pressed = pyqtSignal()
    signal_return_pressed = pyqtSignal(bool)  # is_shift_pressed

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.signal_escape_pressed.emit()
            event.accept()
            return
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            is_shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            self.signal_return_pressed.emit(is_shift)
            event.accept()
            return
        super().keyPressEvent(event)


class FindReplaceBar(QWidget):
    """嵌入式尋找與取代工具列元件。"""
    signal_find_next = pyqtSignal()
    signal_find_prev = pyqtSignal()
    signal_replace = pyqtSignal()
    signal_replace_all = pyqtSignal()
    signal_text_changed = pyqtSignal(str)
    signal_options_changed = pyqtSignal()
    signal_closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scale_factor = getattr(parent, "scale_factor", 1.0) if parent else 1.0
        self.is_replace_mode = False
        self.init_ui()

    def init_ui(self):
        self.setObjectName("findReplaceBar")
        self.setStyleSheet("""
            QWidget#findReplaceBar {
                background-color: #252526;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
            }
            QLineEdit {
                background-color: #3c3c3c;
                color: #cccccc;
                border: 1px solid #555555;
                padding: 3px 6px;
                border-radius: 3px;
                selection-background-color: #264f78;
            }
            QLineEdit:focus {
                border: 1px solid #007acc;
            }
            QPushButton, QToolButton {
                background-color: #333333;
                color: #cccccc;
                border: 1px solid #555555;
                padding: 3px 8px;
                border-radius: 3px;
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
            QLabel {
                color: #888888;
                font-size: 11px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # 1. 尋找列
        find_row = QWidget()
        sf = self.scale_factor
        find_layout = QHBoxLayout(find_row)
        find_layout.setContentsMargins(0, 0, 0, 0)
        find_layout.setSpacing(int(6 * sf))

        self.input_find = CustomLineEdit()
        self.input_find.setPlaceholderText("尋找...")
        self.input_find.setFont(FontManager.get_font(size=int(10 * sf)))
        self.input_find.textChanged.connect(self.signal_text_changed.emit)
        self.input_find.signal_return_pressed.connect(self._on_find_return_pressed)
        self.input_find.signal_escape_pressed.connect(self.close_bar)

        # 比對選項按鈕
        self.btn_match_case = QToolButton()
        self.btn_match_case.setText("Aa")
        self.btn_match_case.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_match_case.setCheckable(True)
        self.btn_match_case.setToolTip("區分大小寫 (Match Case)")
        self.btn_match_case.toggled.connect(self._on_option_toggled)

        self.btn_whole_word = QToolButton()
        self.btn_whole_word.setText("\\b")
        self.btn_whole_word.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_whole_word.setCheckable(True)
        self.btn_whole_word.setToolTip("全字相符 (Whole Word)")
        self.btn_whole_word.toggled.connect(self._on_option_toggled)

        self.btn_regex = QToolButton()
        self.btn_regex.setText(".*")
        self.btn_regex.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_regex.setCheckable(True)
        self.btn_regex.setToolTip("正規表達式 (Regular Expression)")
        self.btn_regex.toggled.connect(self._on_option_toggled)

        # 結果計數
        self.lbl_match_count = QLabel("")
        self.lbl_match_count.setFont(FontManager.get_font(size=int(9 * sf)))
        self.lbl_match_count.setFixedWidth(int(70 * sf))
        self.lbl_match_count.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 導航按鈕
        self.btn_prev = QPushButton("▲ 上一個")
        self.btn_prev.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_prev.setToolTip("找上一個 (Shift+F3)")
        self.btn_prev.clicked.connect(self.signal_find_prev.emit)

        self.btn_next = QPushButton("▼ 下一個")
        self.btn_next.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_next.setToolTip("找下一個 (F3)")
        self.btn_next.clicked.connect(self.signal_find_next.emit)

        # 關閉按鈕
        self.btn_close = QPushButton("✕")
        self.btn_close.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_close.setFixedWidth(int(24 * sf))
        self.btn_close.setToolTip("關閉 (Esc)")
        self.btn_close.clicked.connect(self.close_bar)

        find_layout.addWidget(self.input_find, 1)
        find_layout.addWidget(self.btn_match_case)
        find_layout.addWidget(self.btn_whole_word)
        find_layout.addWidget(self.btn_regex)
        find_layout.addWidget(self.lbl_match_count)
        find_layout.addWidget(self.btn_prev)
        find_layout.addWidget(self.btn_next)
        find_layout.addWidget(self.btn_close)
        layout.addWidget(find_row)

        # 2. 取代列
        self.replace_row = QWidget()
        replace_layout = QHBoxLayout(self.replace_row)
        replace_layout.setContentsMargins(0, 0, 0, 0)
        replace_layout.setSpacing(int(6 * sf))

        self.input_replace = CustomLineEdit()
        self.input_replace.setPlaceholderText("取代為...")
        self.input_replace.setFont(FontManager.get_font(size=int(10 * sf)))
        self.input_replace.signal_return_pressed.connect(lambda _: self.signal_replace.emit())
        self.input_replace.signal_escape_pressed.connect(self.close_bar)

        self.btn_replace = QPushButton("取代")
        self.btn_replace.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_replace.setToolTip("取代目前相符項目")
        self.btn_replace.clicked.connect(self.signal_replace.emit)

        self.btn_replace_all = QPushButton("全部取代")
        self.btn_replace_all.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_replace_all.setToolTip("取代當前文件內所有相符項目")
        self.btn_replace_all.clicked.connect(self.signal_replace_all.emit)

        replace_layout.addWidget(self.input_replace, 1)
        replace_layout.addWidget(self.btn_replace)
        replace_layout.addWidget(self.btn_replace_all)
        layout.addWidget(self.replace_row)

        # 預設不展開取代列
        self.replace_row.setVisible(False)

    def _on_find_return_pressed(self, is_shift: bool):
        if is_shift:
            self.signal_find_prev.emit()
        else:
            self.signal_find_next.emit()

    def _on_option_toggled(self, _):
        self.signal_options_changed.emit()

    def show_find_mode(self, initial_text: str = ""):
        """切換為尋找模式（隱藏取代列）並聚焦。"""
        self.is_replace_mode = False
        self.replace_row.setVisible(False)
        self.show()
        if initial_text:
            self.input_find.setText(initial_text)
        self.input_find.selectAll()
        self.input_find.setFocus()

    def show_replace_mode(self, initial_text: str = ""):
        """切換為取代模式（展開取代列）並聚焦。"""
        self.is_replace_mode = True
        self.replace_row.setVisible(True)
        self.show()
        if initial_text:
            self.input_find.setText(initial_text)
            self.input_find.selectAll()
        self.input_find.setFocus()

    def close_bar(self):
        """關閉搜尋列並發出信號。"""
        self.hide()
        self.signal_closed.emit()

    def update_match_count(self, current_index: int, total_count: int):
        """更新比對命中數顯示。"""
        if total_count == 0:
            if not self.input_find.text():
                self.lbl_match_count.setText("")
            else:
                self.lbl_match_count.setText("無相符")
        else:
            self.lbl_match_count.setText(f"{current_index} / {total_count}")

    def get_search_text(self) -> str:
        return self.input_find.text()

    def get_replace_text(self) -> str:
        return self.input_replace.text()

    def is_match_case(self) -> bool:
        return self.btn_match_case.isChecked()

    def is_whole_word(self) -> bool:
        return self.btn_whole_word.isChecked()

    def is_regex(self) -> bool:
        return self.btn_regex.isChecked()

    def update_scale(self, scale: float):
        """介面縮放改變時動態更新字級與寬度尺寸。"""
        self.scale_factor = scale
        sf = scale
        self.input_find.setFont(FontManager.get_font(size=int(10 * sf)))
        self.btn_match_case.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_whole_word.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_regex.setFont(FontManager.get_font(size=int(9 * sf)))
        self.lbl_match_count.setFont(FontManager.get_font(size=int(9 * sf)))
        self.lbl_match_count.setFixedWidth(int(70 * sf))
        self.btn_prev.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_next.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_close.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_close.setFixedWidth(int(24 * sf))
        self.input_replace.setFont(FontManager.get_font(size=int(10 * sf)))
        self.btn_replace.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_replace_all.setFont(FontManager.get_font(size=int(9 * sf)))
