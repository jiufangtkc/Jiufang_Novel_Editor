from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, pyqtSignal

from views.components.base_rich_text_edit import BaseRichTextEdit


class RightPanelCardEditor(BaseRichTextEdit):
    """資料集卡片所見即所得富文本編輯器：支援 Markdown 雙向轉換、直接樣式切換與快速鍵"""
    signal_save_requested = pyqtSignal()
    signal_ai_chat = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def keyPressEvent(self, event):
        modifiers = event.modifiers()
        key = event.key()

        # Ctrl+S 快速鍵儲存
        if modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_S:
            self.signal_save_requested.emit()
            event.accept()
            return

        super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        menu = self.build_base_context_menu()
        menu.addSeparator()

        target_text, scope_text = self.get_context_targets()

        act_chat = QAction(f"💬 與 AI 討論 ({scope_text})...", self)
        act_chat.setEnabled(bool(target_text))
        act_chat.triggered.connect(lambda: self.signal_ai_chat.emit(target_text))
        menu.addAction(act_chat)

        menu.exec(event.globalPos())
