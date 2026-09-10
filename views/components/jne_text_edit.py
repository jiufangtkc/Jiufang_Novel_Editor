from PyQt6.QtWidgets import QMenu
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction

from views.components.base_rich_text_edit import BaseRichTextEdit


class JNE_TextEdit(BaseRichTextEdit):
    # 發射信號：(task_type, target_text)
    signal_ai_analyze = pyqtSignal(str, str)
    # 發射信號：(context_text)
    signal_ai_chat = pyqtSignal(str)
    # 發射信號：()
    signal_ai_continuation = pyqtSignal()
    # 發射信號：(pasted_text) 貼上文字信號
    signal_text_pasted = pyqtSignal(str)

    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window



    def contextMenuEvent(self, event):
        # 使用基礎右鍵選單
        menu = self.build_base_context_menu()
        menu.addSeparator()

        target_text, scope_text = self.get_context_targets()

        # AI 多輪對話
        act_chat = QAction(f"💬 與 AI 討論 ({scope_text})...", self)
        act_chat.setEnabled(bool(target_text))
        act_chat.triggered.connect(lambda: self.signal_ai_chat.emit(target_text))
        menu.addAction(act_chat)

        # AI 擴寫
        act_continue = QAction("✍️ AI 智慧擴寫 (Ctrl+Alt+E)", self)
        act_continue.triggered.connect(lambda: self.signal_ai_continuation.emit())
        menu.addAction(act_continue)

        menu.addSeparator()

        # AI 輔助分析子選單
        ai_menu = menu.addMenu(f"✨ AI 結構化分析 ({scope_text})")
        ai_menu.setEnabled(bool(target_text))

        act_impression = QAction("📝 文學評語與寫作建議", self)
        act_impression.triggered.connect(lambda: self.signal_ai_analyze.emit("impression", target_text))
        ai_menu.addAction(act_impression)

        act_character = QAction("👤 登場角色提取", self)
        act_character.triggered.connect(lambda: self.signal_ai_analyze.emit("character", target_text))
        ai_menu.addAction(act_character)

        act_world = QAction("🌍 世界觀設定提取", self)
        act_world.triggered.connect(lambda: self.signal_ai_analyze.emit("world", target_text))
        ai_menu.addAction(act_world)

        act_timeline = QAction("⏱️ 時間線與事件梳理", self)
        act_timeline.triggered.connect(lambda: self.signal_ai_analyze.emit("timeline", target_text))
        ai_menu.addAction(act_timeline)

        menu.exec(event.globalPos())
