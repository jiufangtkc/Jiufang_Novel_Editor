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
        self.mc.stats.update_status_bar()
        if self.mc.typewriter_mode:
            self.align_typewriter_center()

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
            self.align_typewriter_center()

    def align_typewriter_center(self):
        """在打字機模式下，將游標垂直對齊至編輯器可見區域中央。

        若當前游標處於文字選取狀態（例如使用者正在拖曳框選文字），則不進行對齊，
        避免畫面滾動導致選取範圍跳動失控。
        """
        if not self.mc.typewriter_mode:
            return
        cursor = self.view.editor.textCursor()
        if cursor.hasSelection():
            return
        cursor_rect = self.view.editor.cursorRect(cursor)
        viewport_height = self.view.editor.viewport().height()
        scrollbar = self.view.editor.verticalScrollBar()
        target_y = int(cursor_rect.top() + scrollbar.value() - (viewport_height / 2))
        scrollbar.setValue(max(0, target_y))

    def on_cursor_position_changed(self):
        # 游標位置變動時同步樣式按鈕（粗體/斜體/刪除線）之狀態
        self.update_format_buttons_state()

    def update_format_buttons_state(self):
        """根據當前游標處字元格式，同步樣式按鈕之按下狀態。"""
        cursor = self.view.editor.textCursor()
        fmt = cursor.charFormat()
        is_bold = (fmt.fontWeight() == QFont.Weight.Bold) or (fmt.fontWeight() >= 700)
        is_italic = fmt.fontItalic()
        is_strike = fmt.fontStrikeOut()

        if hasattr(self.view, "btn_bold"):
            self.view.btn_bold.blockSignals(True)
            self.view.btn_bold.setChecked(is_bold)
            self.view.btn_bold.blockSignals(False)

        if hasattr(self.view, "btn_italic"):
            self.view.btn_italic.blockSignals(True)
            self.view.btn_italic.setChecked(is_italic)
            self.view.btn_italic.blockSignals(False)

        if hasattr(self.view, "btn_strike"):
            self.view.btn_strike.blockSignals(True)
            self.view.btn_strike.setChecked(is_strike)
            self.view.btn_strike.blockSignals(False)

    def toggle_bold(self):
        """切換粗體樣式。"""
        if hasattr(self.view.editor, "toggle_bold"):
            self.view.editor.toggle_bold()
        self.update_format_buttons_state()
        self.view.editor.setFocus()

    def toggle_italic(self):
        """切換斜體樣式。"""
        if hasattr(self.view.editor, "toggle_italic"):
            self.view.editor.toggle_italic()
        self.update_format_buttons_state()
        self.view.editor.setFocus()

    def toggle_strike(self):
        """切換刪除線樣式。"""
        if hasattr(self.view.editor, "toggle_strike"):
            self.view.editor.toggle_strike()
        self.update_format_buttons_state()
        self.view.editor.setFocus()

    def insert_bracket_pair(self, open_br: str, close_br: str):
        """成對括號/引號插入或包裹選取文字。"""
        cursor = self.view.editor.textCursor()
        if cursor.hasSelection():
            selected = cursor.selectedText()
            cursor.insertText(f"{open_br}{selected}{close_br}")
        else:
            pos = cursor.position()
            cursor.insertText(f"{open_br}{close_br}")
            cursor.setPosition(pos + len(open_br))
            self.view.editor.setTextCursor(cursor)
        self.view.editor.setFocus()

    def insert_punctuation(self, punc: str):
        """插入指定標點符號並保持編輯器焦點。"""
        self.view.editor.insertPlainText(punc)
        self.view.editor.setFocus()

    def open_auto_format_dialog(self):
        """開啟小說自動排版工具對話框。"""
        from views.dialogs.auto_format_dialog import AutoFormatDialog
        from services.text_formatter_service import TextFormatterService

        current_text = self.view.editor.toPlainText()
        dlg = AutoFormatDialog(self.view, current_text=current_text)
        if dlg.exec():
            options = dlg.get_options()
            scope = options.get('scope', 'current')

            if scope == 'current':
                # 套用至當前章節
                if not current_text:
                    return
                formatted = TextFormatterService.format_text(current_text, options)
                cursor = self.view.editor.textCursor()
                cursor.beginEditBlock()
                cursor.select(QTextCursor.SelectionType.Document)
                cursor.insertText(formatted)
                cursor.endEditBlock()
            else:
                # 套用至全書所有章節
                from PyQt6.QtWidgets import QMessageBox
                ret = QMessageBox.question(
                    self.view,
                    "確認套用全書排版",
                    "即將對全書所有章節進行自動排版，此動作將更新所有章節內文。\n是否確定繼續？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                if ret != QMessageBox.StandardButton.Yes:
                    return

                # 先儲存當前章節內容避免被舊快照覆蓋
                self.save_current_editor_content()

                def process_item(item):
                    data = item.data(0, Qt.ItemDataRole.UserRole)
                    if data and data.get("type") != "folder":
                        content = data.get("content", "")
                        if content:
                            new_content = TextFormatterService.format_text(content, options)
                            data["content"] = new_content
                            item.setData(0, Qt.ItemDataRole.UserRole, data)
                    for i in range(item.childCount()):
                        process_item(item.child(i))

                for i in range(self.view.tree_widget.topLevelItemCount()):
                    process_item(self.view.tree_widget.topLevelItem(i))

                # 重新載入當前章節編輯器內容
                if self.mc.current_file_item:
                    curr_data = self.mc.current_file_item.data(0, Qt.ItemDataRole.UserRole)
                    if curr_data:
                        content = curr_data.get("content", "")
                        self.view.editor.set_markdown(content)

                self.mc.mark_dirty(True)
                self.mc.stats.update_status_bar()

    def open_lint_dialog(self):
        """開啟文風與贅詞檢查對話框。"""
        from views.dialogs.lint_dialog import LintDialog

        def get_text():
            return self.view.editor.toPlainText()

        dlg = LintDialog(self.view, get_text_func=get_text)
        dlg.signal_navigate_to_text.connect(self.select_editor_range)
        dlg.exec()

    def select_editor_range(self, start_pos: int, end_pos: int):
        """在編輯器中選取指定字元區間並捲動至可見。"""
        cursor = self.view.editor.textCursor()
        cursor.setPosition(start_pos)
        cursor.setPosition(end_pos, QTextCursor.MoveMode.KeepAnchor)
        self.view.editor.setTextCursor(cursor)
        self.view.editor.ensureCursorVisible()
        self.view.editor.setFocus()

