from PyQt6.QtGui import QFont, QTextCursor, QTextCharFormat
from PyQt6.QtCore import Qt

class EditorController:
    """負責編輯器文字操作、字型字級設定與打字機模式（純文字寫作）。"""

    def __init__(self, main_controller):
        self.mc = main_controller

    @property
    def view(self):
        return self.mc.view

    def save_current_editor_content(self):
        if not self.mc.tree.is_item_valid(self.mc.current_file_item):
            self.mc.current_file_item = None
        if self.mc.current_file_item:
            data = self.mc.current_file_item.data(0, Qt.ItemDataRole.UserRole)
            # 統一儲存乾淨 Markdown 內容
            if hasattr(self.view.editor, "to_markdown"):
                data["content"] = self.view.editor.to_markdown()
            else:
                data["content"] = self.view.editor.toPlainText()
            self.mc.current_file_item.setData(0, Qt.ItemDataRole.UserRole, data)

    def on_editor_text_changed(self):
        if not self.mc.tree.is_item_valid(self.mc.current_file_item):
            self.mc.current_file_item = None
        self.save_current_editor_content()

        if self.mc.current_file_item:
            text = self.view.editor.toPlainText()
            stats = self.mc.stats.analyze_exclusions(text)
            current_count = stats["valid"]

            if hasattr(self.mc, 'current_file_last_word_count'):
                delta = current_count - self.mc.current_file_last_word_count
                self.mc.today_written_count = max(0, self.mc.today_written_count + delta)
            self.mc.current_file_last_word_count = current_count

            item_id = self.mc.tree.get_item_id(self.mc.current_file_item)
            if item_id:
                self.mc.file_word_stats[item_id] = stats

        self.mc.mark_dirty(True)
        self.mc.update_status_bar()

    def change_font(self, font):
        family = font.family() if isinstance(font, QFont) else str(font)
        self.mc.editor_font_family = family
        self.mc.project_info.editor_font_family = family
        cursor = self.view.editor.textCursor()
        if cursor.hasSelection():
            fmt = QTextCharFormat()
            fmt.setFontFamily(family)
            cursor.mergeCharFormat(fmt)
        else:
            ed_font = self.view.editor.font()
            ed_font.setFamily(family)
            self.view.editor.setFont(ed_font)
        self.view.editor.setFocus()

    def change_font_size(self, size):
        try:
            size = float(size)
        except ValueError:
            return
        self.mc.editor_font_size = int(size)
        self.mc.project_info.editor_font_size = int(size)
        cursor = self.view.editor.textCursor()
        if cursor.hasSelection():
            fmt = QTextCharFormat()
            fmt.setFontPointSize(size)
            cursor.mergeCharFormat(fmt)
        else:
            ed_font = self.view.editor.font()
            ed_font.setPointSizeF(size)
            self.view.editor.setFont(ed_font)
        self.view.editor.setFocus()

    def toggle_typewriter(self, checked: bool):
        self.mc.typewriter_mode = checked
        self.view.btn_typewriter.setText("打字機模式: 開" if checked else "打字機模式: 關")
        if checked:
            self.on_cursor_position_changed()

    def on_cursor_position_changed(self):
        if not self.mc.typewriter_mode:
            return
        cursor = self.view.editor.textCursor()
        cursor_rect = self.view.editor.cursorRect(cursor)
        viewport_height = self.view.editor.viewport().height()
        scrollbar = self.view.editor.verticalScrollBar()
        target_y = cursor_rect.top() + scrollbar.value() - (viewport_height / 2)
        if target_y > 0:
            scrollbar.setValue(int(target_y))

    def open_lint_dialog(self):
        """開啟文風與贅詞檢查對話框。"""
        from views.dialogs.lint_dialog import LintDialog

        def get_text():
            return self.view.editor.toPlainText()

        dlg = LintDialog(self.view, get_text_func=get_text)
        dlg.signal_navigate_to_text.connect(self.select_editor_range)
        dlg.exec()

    def select_editor_range(self, start_pos: int, end_pos: int):
        """在編輯器中選取指定字元區間並滾動至可見。"""
        cursor = self.view.editor.textCursor()
        cursor.setPosition(start_pos)
        cursor.setPosition(end_pos, QTextCursor.MoveMode.KeepAnchor)
        self.view.editor.setTextCursor(cursor)
        self.view.editor.ensureCursorVisible()
        self.view.editor.setFocus()

