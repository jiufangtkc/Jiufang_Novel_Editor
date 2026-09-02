from PyQt6.QtWidgets import QTextEdit, QMenu
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QTextCharFormat, QFont
from utils.markdown_utils import markdown_to_html, document_to_markdown


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
        self.setAcceptRichText(True)
        # 移除 Qt HTML 預設段落邊距 (margin: 12px)，確保小說段落與空行排版緊湊自然
        self.document().setDefaultStyleSheet("p, li { margin: 0px; padding: 0px; }")

    def set_markdown(self, md_text: str):
        """載入 Markdown 文字並渲染為所見即所得富文本（隱藏 ##、** 等語法符號）"""
        self.blockSignals(True)
        html = markdown_to_html(md_text)
        self.setHtml(html)
        self.blockSignals(False)

    def to_markdown(self) -> str:
        """將所見即所得富文本內容提取並序列化為乾淨標準的 Markdown 文本"""
        return document_to_markdown(self.document())

    def keyPressEvent(self, event):
        modifiers = event.modifiers()
        key = event.key()

        # Ctrl+B: 粗體切換 (所見即所得)
        if modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_B:
            self.toggle_bold()
            return

        # Ctrl+I: 斜體切換 (所見即所得)
        if modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_I:
            self.toggle_italic()
            return

        # Ctrl+Shift+S: 刪除線切換 (所見即所得)
        if modifiers == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier) and key == Qt.Key.Key_S:
            self.toggle_strike()
            return

        # Ctrl+Shift+H: 插入場景分隔線
        if modifiers == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier) and key == Qt.Key.Key_H:
            self.insert_scene_divider()
            return

        super().keyPressEvent(event)

    def toggle_bold(self):
        """直觀切換選取文字的粗體樣式（不插入 ** 符號）"""
        cursor = self.textCursor()
        fmt = QTextCharFormat()
        is_bold = (cursor.charFormat().fontWeight() == QFont.Weight.Bold) or (cursor.charFormat().fontWeight() >= 700)
        fmt.setFontWeight(QFont.Weight.Normal if is_bold else QFont.Weight.Bold)
        cursor.mergeCharFormat(fmt)

    def toggle_italic(self):
        """直觀切換選取文字的斜體樣式（不插入 * 符號）"""
        cursor = self.textCursor()
        fmt = QTextCharFormat()
        is_italic = cursor.charFormat().fontItalic()
        fmt.setFontItalic(not is_italic)
        cursor.mergeCharFormat(fmt)

    def toggle_strike(self):
        """直觀切換選取文字的刪除線樣式（不插入 ~~ 符號）"""
        cursor = self.textCursor()
        fmt = QTextCharFormat()
        is_strike = cursor.charFormat().fontStrikeOut()
        fmt.setFontStrikeOut(not is_strike)
        cursor.mergeCharFormat(fmt)

    def insert_scene_divider(self):
        """插入小說場景分隔線"""
        cursor = self.textCursor()
        cursor.insertText("\n――――――――――――――――――――\n")

    def insertFromMimeData(self, source):
        """貼上文字時若含有 Markdown 格式，自動轉換為乾淨純文字或保持排版"""
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
        act_bold.triggered.connect(self.toggle_bold)
        fmt_menu.addAction(act_bold)

        act_italic = QAction("斜體 (Ctrl+I)", self)
        act_italic.triggered.connect(self.toggle_italic)
        fmt_menu.addAction(act_italic)

        act_strike = QAction("刪除線 (Ctrl+Shift+S)", self)
        act_strike.triggered.connect(self.toggle_strike)
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
