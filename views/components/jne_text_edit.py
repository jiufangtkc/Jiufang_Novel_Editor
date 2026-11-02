from PyQt6.QtCore import pyqtSignal

from views.components.base_rich_text_edit import BaseRichTextEdit


class JNE_TextEdit(BaseRichTextEdit):
    # 發射信號：(pasted_text) 貼上文字信號
    signal_text_pasted = pyqtSignal(str)

    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window

    def contextMenuEvent(self, event):
        # 使用基礎右鍵選單
        menu = self.build_base_context_menu()
        menu.exec(event.globalPos())

