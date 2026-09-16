from PyQt6.QtWidgets import QTextEdit, QMenu, QApplication
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QTextCharFormat, QFont
from utils.markdown_utils import markdown_to_html, document_to_markdown


class BaseRichTextEdit(QTextEdit):
    """
    小說編輯器與卡片編輯器的共用基礎類別：
    - 封裝 Markdown 雙向轉換邏輯 (所見即所得)
    - 提供共用的格式化快捷鍵 (粗體、斜體、刪除線、分隔線)
    - 提供雙重貼上模式：富文本 (Ctrl+V) 與 純文字 (Ctrl+Shift+V)
    - 提供基礎的右鍵選單
    """
    # 發射信號：(context_text) 供子類別或外部處理 AI 對話
    signal_ai_chat = pyqtSignal(str)
    # 發射信號：(pasted_text) 貼上文字信號
    signal_text_pasted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptRichText(True)
        # 移除 Qt HTML 預設段落邊距 (margin: 12px)，確保小說段落與空行排版緊湊自然
        self.document().setDefaultStyleSheet("p, li { margin: 0px; padding: 0px; }")

    def set_markdown(self, md_text: str):
        """載入 Markdown 文字並渲染為所見即所得富文本"""
        self.blockSignals(True)
        html = markdown_to_html(md_text)
        self.setHtml(html)
        self.blockSignals(False)

    def to_markdown(self) -> str:
        """將所見即所得富文本內容提取並序列化為乾淨標準的 Markdown 文本"""
        return document_to_markdown(self.document())

    # =========================================================================
    # 格式化操作
    # =========================================================================

    def toggle_bold(self):
        """直觀切換選取文字的粗體樣式"""
        cursor = self.textCursor()
        fmt = QTextCharFormat()
        is_bold = (cursor.charFormat().fontWeight() == QFont.Weight.Bold) or (cursor.charFormat().fontWeight() >= 700)
        fmt.setFontWeight(QFont.Weight.Normal if is_bold else QFont.Weight.Bold)
        cursor.mergeCharFormat(fmt)

    def toggle_italic(self):
        """直觀切換選取文字的斜體樣式"""
        cursor = self.textCursor()
        fmt = QTextCharFormat()
        is_italic = cursor.charFormat().fontItalic()
        fmt.setFontItalic(not is_italic)
        cursor.mergeCharFormat(fmt)

    def toggle_strike(self):
        """直觀切換選取文字的刪除線樣式"""
        cursor = self.textCursor()
        fmt = QTextCharFormat()
        is_strike = cursor.charFormat().fontStrikeOut()
        fmt.setFontStrikeOut(not is_strike)
        cursor.mergeCharFormat(fmt)

    def toggle_line_prefix(self, prefix: str):
        """為目前游標所在的段落（或多個選取的段落）切換指定前綴（如清單、標題）"""
        from PyQt6.QtGui import QTextCursor
        cursor = self.textCursor()
        cursor.beginEditBlock()

        start_block = self.document().findBlock(cursor.selectionStart())
        end_block = self.document().findBlock(cursor.selectionEnd())

        # 第一階段：檢查是否所有選取的段落都已經有此前綴
        all_have_prefix = True
        curr_block = start_block
        while curr_block.isValid():
            if not curr_block.text().startswith(prefix):
                all_have_prefix = False
                break
            if curr_block == end_block:
                break
            curr_block = curr_block.next()

        # 第二階段：統一新增或移除前綴
        curr_block = start_block
        while curr_block.isValid():
            block_cursor = self.textCursor()
            block_cursor.setPosition(curr_block.position())
            
            if all_have_prefix:
                # 移除前綴
                block_cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, len(prefix))
                block_cursor.removeSelectedText()
            else:
                # 新增前綴（如果還沒有的話）
                if not curr_block.text().startswith(prefix):
                    block_cursor.insertText(prefix)
            
            if curr_block == end_block:
                break
            curr_block = curr_block.next()

        cursor.endEditBlock()
        self.setFocus()

    def insert_scene_divider(self):
        """插入小說場景分隔線"""
        cursor = self.textCursor()
        cursor.insertText("\n――――――――――――――――――――\n")

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

    # =========================================================================
    # 貼上與按鍵事件處理
    # =========================================================================

    def paste_as_plain_text(self):
        """僅貼上純文字（過濾所有格式與富文本）"""
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            self.insertPlainText(text)
            self.signal_text_pasted.emit(text)

    def insertFromMimeData(self, source):
        """預設貼上：支援按照來源格式貼上富文本，或純文字"""
        if source.hasHtml():
            # 來源含有富文本，套用預設 Qt 行為（保留格式）
            super().insertFromMimeData(source)
            if source.hasText():
                self.signal_text_pasted.emit(source.text())
        elif source.hasText():
            # 來源僅有純文字，使用 insertPlainText 避免多餘空行（相容舊版邏輯）
            text = source.text()
            self.insertPlainText(text)
            self.signal_text_pasted.emit(text)
        else:
            super().insertFromMimeData(source)

    def keyPressEvent(self, event):
        modifiers = event.modifiers()
        key = event.key()

        # Ctrl+Shift+V: 僅貼上純文字
        if modifiers == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier) and key == Qt.Key.Key_V:
            self.paste_as_plain_text()
            event.accept()
            return

        # Ctrl+B: 粗體切換
        if modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_B:
            self.toggle_bold()
            event.accept()
            return

        # Ctrl+I: 斜體切換
        if modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_I:
            self.toggle_italic()
            event.accept()
            return

        # Ctrl+Shift+S: 刪除線切換
        if modifiers == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier) and key == Qt.Key.Key_S:
            self.toggle_strike()
            event.accept()
            return

        # Ctrl+Shift+H: 插入場景分隔線
        if modifiers == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier) and key == Qt.Key.Key_H:
            self.insert_scene_divider()
            event.accept()
            return

        super().keyPressEvent(event)

    # =========================================================================
    # 右鍵選單輔助
    # =========================================================================

    def build_base_context_menu(self) -> QMenu:
        """建立包含雙重貼上模式與排版格式的基礎右鍵選單"""
        menu = self.createStandardContextMenu()
        
        # 尋找並修改預設的「貼上」選項
        actions = menu.actions()
        paste_action = None
        for action in actions:
            # 依賴 Qt 內部名稱或文字比對
            if "Paste" in action.text() or "貼上" in action.text():
                paste_action = action
                break
        
        if paste_action:
            paste_action.setText("📋 按照來源格式貼上 (Ctrl+V)")
            # 在一般貼上後方插入「僅貼上純文字」
            idx = actions.index(paste_action)
            act_paste_plain = QAction("📝 僅貼上純文字 (Ctrl+Shift+V)", self)
            act_paste_plain.triggered.connect(self.paste_as_plain_text)
            if idx + 1 < len(actions):
                menu.insertAction(actions[idx + 1], act_paste_plain)
            else:
                menu.addAction(act_paste_plain)

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

        return menu

    def get_context_targets(self):
        """取得選取範圍的目標文字與範圍說明 (供 AI 子選單使用)"""
        selected_text = self.textCursor().selectedText().strip()
        has_selection = bool(selected_text)
        target_text = selected_text if has_selection else self.toPlainText().strip()
        scope_text = "選取內容" if has_selection else "全文"
        return target_text, scope_text
