from PyQt6.QtWidgets import QTextEdit, QMenu
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from utils.markdown_highlighter import MarkdownHighlighter


class JNE_TextEdit(QTextEdit):
    # 發射信號：(task_type, target_text)
    signal_ai_analyze = pyqtSignal(str, str)
    # 發射信號：(context_text)
    signal_ai_chat = pyqtSignal(str)
    # 發射信號：()
    signal_ai_continuation = pyqtSignal()

    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.setAcceptRichText(False)
        self.highlighter = MarkdownHighlighter(self.document())

    def keyPressEvent(self, event):
        modifiers = event.modifiers()
        key = event.key()

        # Ctrl+B: 粗體切換
        if modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_B:
            self.toggle_inline_format("**")
            return

        # Ctrl+I: 斜體切換
        if modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_I:
            self.toggle_inline_format("*")
            return

        # Ctrl+Shift+S: 刪除線切換
        if modifiers == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier) and key == Qt.Key.Key_S:
            self.toggle_inline_format("~~")
            return

        # Ctrl+Shift+H: 插入場景分隔線
        if modifiers == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier) and key == Qt.Key.Key_H:
            self.insert_scene_divider()
            return

        super().keyPressEvent(event)

    def toggle_inline_format(self, wrap_tag: str):
        """為選取文字套用或移除 Markdown 行內包裹語法（如 ** 或 * 或 ~~）"""
        cursor = self.textCursor()
        tag_len = len(wrap_tag)

        if not cursor.hasSelection():
            # 無選取文字：插入一對標記並將游標置於中央
            pos = cursor.position()
            cursor.insertText(f"{wrap_tag}{wrap_tag}")
            cursor.setPosition(pos + tag_len)
            self.setTextCursor(cursor)
            return

        selected_text = cursor.selectedText()
        if selected_text.startswith(wrap_tag) and selected_text.endswith(wrap_tag) and len(selected_text) >= tag_len * 2:
            # 已包裹：去除標記
            new_text = selected_text[tag_len:-tag_len]
            cursor.insertText(new_text)
        else:
            # 未包裹：加上標記
            cursor.insertText(f"{wrap_tag}{selected_text}{wrap_tag}")

    def insert_scene_divider(self):
        """插入小說場景分隔線 (---)"""
        cursor = self.textCursor()
        cursor.insertText("\n---\n")

    def insertFromMimeData(self, source):
        """全局無格式貼上：過濾所有來源富文本/HTML格式，一律以純文字插入"""
        if source.hasText():
            self.insertPlainText(source.text())
        else:
            super().insertFromMimeData(source)

    def contextMenuEvent(self, event):
        # 建立標準右鍵選單
        menu = self.createStandardContextMenu()
        menu.addSeparator()

        # 格式與排版子選單
        fmt_menu = menu.addMenu("🔤 格式與排版")
        act_bold = QAction("粗體 (Ctrl+B)", self)
        act_bold.triggered.connect(lambda: self.toggle_inline_format("**"))
        fmt_menu.addAction(act_bold)

        act_italic = QAction("斜體 (Ctrl+I)", self)
        act_italic.triggered.connect(lambda: self.toggle_inline_format("*"))
        fmt_menu.addAction(act_italic)

        act_strike = QAction("刪除線 (Ctrl+Shift+S)", self)
        act_strike.triggered.connect(lambda: self.toggle_inline_format("~~"))
        fmt_menu.addAction(act_strike)

        fmt_menu.addSeparator()
        act_divider = QAction("插入場景分隔線 (Ctrl+Shift+H)", self)
        act_divider.triggered.connect(self.insert_scene_divider)
        fmt_menu.addAction(act_divider)

        menu.addSeparator()

        # 取得選取文字或全文
        selected_text = self.textCursor().selectedText().strip()
        has_selection = bool(selected_text)
        target_text = selected_text if has_selection else self.toPlainText().strip()
        scope_text = "選取內容" if has_selection else "當前全文"

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
