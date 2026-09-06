from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtGui import QFont, QAction, QTextCharFormat
from PyQt6.QtCore import Qt, pyqtSignal

from utils.markdown_utils import markdown_to_html, document_to_markdown


class RightPanelCardEditor(QTextEdit):
    """資料集卡片所見即所得富文本編輯器：支援 Markdown 雙向轉換、直接樣式切換與快速鍵"""
    signal_save_requested = pyqtSignal()
    signal_ai_chat = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptRichText(True)
        # 移除 Qt HTML 預設段落邊距，維持緊湊排版
        self.document().setDefaultStyleSheet("p, li { margin: 0px; padding: 0px; }")

    def set_markdown(self, md_text: str):
        self.blockSignals(True)
        html = markdown_to_html(md_text)
        self.setHtml(html)
        self.blockSignals(False)

    def to_markdown(self) -> str:
        return document_to_markdown(self.document())

    def toggle_bold(self):
        cursor = self.textCursor()
        fmt = QTextCharFormat()
        is_bold = (cursor.charFormat().fontWeight() == QFont.Weight.Bold) or (cursor.charFormat().fontWeight() >= 700)
        fmt.setFontWeight(QFont.Weight.Normal if is_bold else QFont.Weight.Bold)
        cursor.mergeCharFormat(fmt)

    def toggle_italic(self):
        cursor = self.textCursor()
        fmt = QTextCharFormat()
        is_italic = cursor.charFormat().fontItalic()
        fmt.setFontItalic(not is_italic)
        cursor.mergeCharFormat(fmt)

    def toggle_strike(self):
        cursor = self.textCursor()
        fmt = QTextCharFormat()
        is_strike = cursor.charFormat().fontStrikeOut()
        fmt.setFontStrikeOut(not is_strike)
        cursor.mergeCharFormat(fmt)

    def insertFromMimeData(self, source):
        """貼上文字時若含有 Markdown 格式，自動轉換為乾淨純文字或保持排版"""
        if source.hasText():
            self.insertPlainText(source.text())
        else:
            super().insertFromMimeData(source)

    def keyPressEvent(self, event):
        modifiers = event.modifiers()
        key = event.key()

        # Ctrl+S 快速鍵儲存
        if modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_S:
            self.signal_save_requested.emit()
            event.accept()
            return

        # Ctrl+B 粗體快速鍵 (所見即所得)
        if modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_B:
            self.toggle_bold()
            event.accept()
            return

        # Ctrl+I 斜體快速鍵 (所見即所得)
        if modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_I:
            self.toggle_italic()
            event.accept()
            return

        super().keyPressEvent(event)

    def wrap_selection(self, prefix: str, suffix: str):
        """相容輔助：將選取文字套用格式"""
        if prefix == "**":
            self.toggle_bold()
            return
        if prefix == "*":
            self.toggle_italic()
            return
        if prefix == "~~":
            self.toggle_strike()
            return

        cursor = self.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText()
            cursor.insertText(f"{prefix}{text}{suffix}")
        else:
            pos = cursor.position()
            cursor.insertText(f"{prefix}{suffix}")
            cursor.setPosition(pos + len(prefix))
            self.setTextCursor(cursor)
        self.setFocus()

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        menu.addSeparator()

        selected_text = self.textCursor().selectedText().strip()
        has_selection = bool(selected_text)
        target_text = selected_text if has_selection else self.toPlainText().strip()
        scope_text = "選取內容" if has_selection else "卡片全文"

        act_chat = QAction(f"💬 與 AI 討論 ({scope_text})...", self)
        act_chat.setEnabled(bool(target_text))
        act_chat.triggered.connect(lambda: self.signal_ai_chat.emit(target_text))
        menu.addAction(act_chat)

        menu.exec(event.globalPos())
