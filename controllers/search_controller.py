import re
from typing import List, Tuple, Optional
from PyQt6.QtWidgets import QTextEdit, QTreeWidgetItem
from PyQt6.QtGui import QTextCursor, QTextCharFormat, QColor
from PyQt6.QtCore import Qt

from views.dialogs.global_search_dialog import GlobalSearchDialog

class SearchController:
    """專責搜尋、取代、高亮顯示與跨章節全文檢索控制器。"""

    def __init__(self, main_controller):
        self.mc = main_controller
        self.current_matches: List[Tuple[int, int]] = []
        self.current_match_index: int = -1
        self.global_search_dialog: Optional[GlobalSearchDialog] = None

    @property
    def editor(self):
        return self.mc.view.editor

    @property
    def find_bar(self):
        return self.mc.view.find_replace_bar

    def open_find(self):
        """開啟尋找列（Ctrl+F）。"""
        selected_text = self.editor.textCursor().selectedText()
        # 若選取文字跨行則不代入
        if "\u2029" in selected_text or "\n" in selected_text:
            selected_text = ""
        self.find_bar.show_find_mode(selected_text)
        self.update_search()

    def open_replace(self):
        """開啟取代列（Ctrl+H）。"""
        selected_text = self.editor.textCursor().selectedText()
        if "\u2029" in selected_text or "\n" in selected_text:
            selected_text = ""
        self.find_bar.show_replace_mode(selected_text)
        self.update_search()

    def close_find_bar(self):
        """關閉搜尋列並清除高亮。"""
        self.clear_highlights()
        self.editor.setFocus()

    def update_search(self):
        """依據搜尋列的當前輸入與設定，執行編輯器搜尋。"""
        query = self.find_bar.get_search_text()
        if not query:
            self.clear_highlights()
            self.find_bar.update_match_count(0, 0)
            return

        match_case = self.find_bar.is_match_case()
        whole_word = self.find_bar.is_whole_word()
        is_regex = self.find_bar.is_regex()

        self.find_in_editor(query, match_case, whole_word, is_regex)

    def find_in_editor(self, query: str, match_case: bool = False, whole_word: bool = False, is_regex: bool = False):
        """在目前編輯器中搜尋並建立高亮。"""
        self.current_matches = []
        self.current_match_index = -1

        text = self.editor.toPlainText()
        if not text or not query:
            self.clear_highlights()
            self.find_bar.update_match_count(0, 0)
            return

        # 構建正規表達式
        pattern = self._build_regex_pattern(query, match_case, whole_word, is_regex)
        if pattern is None:
            self.clear_highlights()
            self.find_bar.update_match_count(0, 0)
            return

        for match in pattern.finditer(text):
            self.current_matches.append((match.start(), match.end()))

        total_count = len(self.current_matches)
        if total_count == 0:
            self.clear_highlights()
            self.find_bar.update_match_count(0, 0)
            return

        # 尋找離目前游標最近的匹配項目
        cursor_pos = self.editor.textCursor().selectionStart()
        nearest_idx = 0
        for idx, (start, _) in enumerate(self.current_matches):
            if start >= cursor_pos:
                nearest_idx = idx
                break

        self.current_match_index = nearest_idx
        self.highlight_matches()
        self.scroll_to_match(self.current_match_index)
        self.find_bar.update_match_count(self.current_match_index + 1, total_count)

    def find_next(self):
        """跳至下一個相符項目。"""
        if not self.current_matches:
            self.update_search()
            return

        self.current_match_index = (self.current_match_index + 1) % len(self.current_matches)
        self.highlight_matches()
        self.scroll_to_match(self.current_match_index)
        self.find_bar.update_match_count(self.current_match_index + 1, len(self.current_matches))

    def find_prev(self):
        """跳至上一個相符項目。"""
        if not self.current_matches:
            self.update_search()
            return

        self.current_match_index = (self.current_match_index - 1 + len(self.current_matches)) % len(self.current_matches)
        self.highlight_matches()
        self.scroll_to_match(self.current_match_index)
        self.find_bar.update_match_count(self.current_match_index + 1, len(self.current_matches))

    def replace(self):
        """取代當前聚焦的相符項目。"""
        if not self.current_matches or self.current_match_index < 0:
            return

        start, end = self.current_matches[self.current_match_index]
        replace_text = self.find_bar.get_replace_text()

        cursor = self.editor.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(replace_text)

        # 重新搜尋並定位
        self.update_search()

    def replace_all(self):
        """取代當前文件中所有相符項目。"""
        query = self.find_bar.get_search_text()
        if not query:
            return

        match_case = self.find_bar.is_match_case()
        whole_word = self.find_bar.is_whole_word()
        is_regex = self.find_bar.is_regex()
        replace_text = self.find_bar.get_replace_text()

        pattern = self._build_regex_pattern(query, match_case, whole_word, is_regex)
        if pattern is None:
            return

        text = self.editor.toPlainText()
        new_text, count = pattern.subn(replace_text, text)

        if count > 0:
            cursor = self.editor.textCursor()
            cursor.beginEditBlock()
            cursor.select(QTextCursor.SelectionType.Document)
            cursor.insertText(new_text)
            cursor.endEditBlock()

        self.update_search()

    def scroll_to_match(self, match_index: int):
        """將游標定位並選取特定相符項目，同時捲動視圖至可見。"""
        if match_index < 0 or match_index >= len(self.current_matches):
            return

        start, end = self.current_matches[match_index]
        cursor = self.editor.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        self.editor.setTextCursor(cursor)
        self.editor.ensureCursorVisible()

    def highlight_matches(self):
        """使用 ExtraSelection 對相符文字進行高亮著色。"""
        extra_selections = []

        for idx, (start, end) in enumerate(self.current_matches):
            selection = QTextEdit.ExtraSelection()
            cursor = self.editor.textCursor()
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            selection.cursor = cursor

            fmt = QTextCharFormat()
            if idx == self.current_match_index:
                # 當前焦點項目：橘黃色強高亮
                fmt.setBackground(QColor("#d18b00"))
                fmt.setForeground(QColor("#ffffff"))
            else:
                # 其餘項目：半透明淺黃色
                fmt.setBackground(QColor("#554d24"))
                fmt.setForeground(QColor("#ffffff"))

            selection.format = fmt
            extra_selections.append(selection)

        self.editor.setExtraSelections(extra_selections)

    def clear_highlights(self):
        """清除編輯器中所有搜尋高亮。"""
        self.current_matches = []
        self.current_match_index = -1
        self.editor.setExtraSelections([])

    def _build_regex_pattern(self, query: str, match_case: bool, whole_word: bool, is_regex: bool) -> Optional[re.Pattern]:
        """建立並編譯正規表達式。"""
        try:
            if not is_regex:
                raw_pattern = re.escape(query)
            else:
                raw_pattern = query

            if whole_word:
                raw_pattern = rf"\b{raw_pattern}\b"

            flags = 0 if match_case else re.IGNORECASE
            return re.compile(raw_pattern, flags)
        except Exception:
            return None

    # ================= 跨章節全文搜尋 =================

    def open_global_search_dialog(self):
        """開啟跨章節全文搜尋對話框（Ctrl+Shift+F）。"""
        if self.global_search_dialog is None:
            self.global_search_dialog = GlobalSearchDialog(self.mc.view)
            self.global_search_dialog.signal_search_requested.connect(self.execute_global_search)
            self.global_search_dialog.signal_navigate_to_match.connect(self.navigate_to_global_match)

        selected_text = self.editor.textCursor().selectedText()
        if "\u2029" in selected_text or "\n" in selected_text:
            selected_text = ""

        self.global_search_dialog.show_dialog(selected_text)

    def execute_global_search(self, query: str, match_case: bool, whole_word: bool, is_regex: bool):
        """執行跨章節全文搜尋。"""
        # 先保存當前編輯器內容，確保資料最新
        self.mc.editor.save_current_editor_content()

        pattern = self._build_regex_pattern(query, match_case, whole_word, is_regex)
        if pattern is None:
            if self.global_search_dialog:
                self.global_search_dialog.display_results([])
            return

        results = []
        tree_widget = self.mc.view.tree_widget

        # 遍歷樹狀結構
        for i in range(tree_widget.topLevelItemCount()):
            top_item = tree_widget.topLevelItem(i)
            self._search_tree_item_recursive(top_item, pattern, results)

        if self.global_search_dialog:
            self.global_search_dialog.display_results(results)

    def _search_tree_item_recursive(self, item: QTreeWidgetItem, pattern: re.Pattern, results: list):
        """遞迴遍歷章節樹搜尋文字。"""
        if not self.mc.tree.is_item_valid(item):
            return

        node_data = item.data(0, Qt.ItemDataRole.UserRole) or {}
        node_type = node_data.get("type", "")
        content = node_data.get("content", "") or ""
        node_id = self.mc.tree.get_item_id(item)
        parent_path = self.mc.tree.get_item_path_string(item)
        item_name = item.text(0)
        item_path = f"{parent_path} / {item_name}" if parent_path != "根目錄" else item_name

        if node_type == "file" and content:
            lines = content.split("\n")
            # 建立每行字元起點索引，以便快速計算 line_num
            line_starts = []
            cur_offset = 0
            for line in lines:
                line_starts.append(cur_offset)
                cur_offset += len(line) + 1  # 包含 \n

            for match in pattern.finditer(content):
                start_pos = match.start()
                match_len = match.end() - start_pos

                # 二分搜尋或計算行號
                line_num = 1
                for idx, l_start in enumerate(line_starts):
                    if start_pos >= l_start:
                        line_num = idx + 1
                    else:
                        break

                # 擷取前後 30 字摘要
                snippet_start = max(0, start_pos - 30)
                snippet_end = min(len(content), match.end() + 30)
                raw_snippet = content[snippet_start:snippet_end].replace("\n", " ")
                if snippet_start > 0:
                    raw_snippet = "..." + raw_snippet
                if snippet_end < len(content):
                    raw_snippet = raw_snippet + "..."

                results.append({
                    "node_id": node_id,
                    "chapter_path": item_path,
                    "line_num": line_num,
                    "char_offset": start_pos,
                    "match_len": match_len,
                    "snippet": raw_snippet
                })

        # 遞迴子節點
        for i in range(item.childCount()):
            child = item.child(i)
            self._search_tree_item_recursive(child, pattern, results)

    def navigate_to_global_match(self, node_id: str, line_num: int, char_offset: int, match_len: int):
        """從全文搜尋對話框雙擊跳轉至目標章節並選取高亮文字。"""
        item = self._find_tree_item_by_id(node_id)
        if item is None:
            return

        # 切換選擇該章節
        self.mc.view.tree_widget.setCurrentItem(item)
        self.mc.tree.on_tree_item_clicked(item, 0)

        # 游標定位並選取
        cursor = self.editor.textCursor()
        cursor.setPosition(char_offset)
        cursor.setPosition(char_offset + match_len, QTextCursor.MoveMode.KeepAnchor)
        self.editor.setTextCursor(cursor)
        self.editor.ensureCursorVisible()
        self.editor.setFocus()

    def _find_tree_item_by_id(self, target_id: str) -> Optional[QTreeWidgetItem]:
        """依據 ID 在章節樹中尋找項目。"""
        tree_widget = self.mc.view.tree_widget

        def _search(parent_item):
            count = parent_item.childCount() if parent_item else tree_widget.topLevelItemCount()
            for i in range(count):
                item = parent_item.child(i) if parent_item else tree_widget.topLevelItem(i)
                if self.mc.tree.get_item_id(item) == target_id:
                    return item
                found = _search(item)
                if found:
                    return found
            return None

        return _search(None)
