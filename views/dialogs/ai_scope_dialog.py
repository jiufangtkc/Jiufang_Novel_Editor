import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QRadioButton, QButtonGroup,
    QLineEdit, QWidget, QFrame, QMessageBox
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from utils.font_manager import FontManager


class AIScopeDialog(QDialog):
    """
    AI 分析與角色提取範圍選擇對話框。
    支援：
    1. 全文（全書所有章節）
    2. 當前章節 / 選取文字
    3. 自訂勾選部分章節（樹狀多選）
    """

    def __init__(self, parent=None, current_item=None, selected_text=""):
        super().__init__(parent)
        self.main_window = parent
        self.current_item = current_item
        self.selected_text = selected_text
        self.item_map = {}
        self.scale_factor = getattr(parent, "scale_factor", 1.0) if parent else 1.0

        self.setWindowTitle("AI 登場角色提取 — 分析範圍選擇")
        self.resize(int(540 * self.scale_factor), int(640 * self.scale_factor))
        self.setMinimumSize(int(460 * self.scale_factor), int(520 * self.scale_factor))
        self.setModal(True)
        if parent:
            self.setStyleSheet(parent.styleSheet())

        self.init_ui()
        self.populate_tree()
        self.update_statistics()

    def init_ui(self):
        sf = self.scale_factor
        layout = QVBoxLayout(self)
        layout.setContentsMargins(int(18 * sf), int(18 * sf), int(18 * sf), int(18 * sf))
        layout.setSpacing(int(12 * sf))

        # 頂部提示
        lbl_hint = QLabel("請選擇 AI 角色提取與分析的範圍：")
        lbl_hint.setFont(FontManager.get_font(size=int(10 * sf), weight=QFont.Weight.Bold))
        layout.addWidget(lbl_hint)

        # 範圍單選選項（卡片式清晰外框容器）
        mode_box = QFrame()
        mode_box.setObjectName("scope_mode_card")
        mode_box.setStyleSheet(f"""
            QFrame#scope_mode_card {{
                background-color: #21252b;
                border: 1px solid #4b5263;
                border-radius: {int(6 * sf)}px;
                padding: {int(8 * sf)}px {int(10 * sf)}px;
            }}
            QRadioButton {{
                color: #e3e3e3;
                spacing: {int(8 * sf)}px;
                padding: {int(4 * sf)}px 0px;
            }}
            QRadioButton::indicator {{
                width: {int(16 * sf)}px;
                height: {int(16 * sf)}px;
                border-radius: {int(8 * sf)}px;
                border: 2px solid #8c939d;
                background-color: #1e2227;
            }}
            QRadioButton::indicator:hover {{
                border: 2px solid #61afef;
            }}
            QRadioButton::indicator:checked {{
                border: 2px solid #61afef;
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0 #61afef, stop:0.48 #61afef, stop:0.52 #1e2227, stop:1 #1e2227);
            }}
        """)
        mode_layout = QVBoxLayout(mode_box)
        mode_layout.setContentsMargins(int(8 * sf), int(8 * sf), int(8 * sf), int(8 * sf))
        mode_layout.setSpacing(int(8 * sf))

        self.btn_group = QButtonGroup(self)

        self.radio_all = QRadioButton("📚 全書全文（提取整部小說的所有章節）")
        self.radio_all.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_group.addButton(self.radio_all)
        mode_layout.addWidget(self.radio_all)

        current_title = self.current_item.text(0) if self.current_item else "當前章節"
        if self.selected_text:
            self.radio_current = QRadioButton(f"📄 當前選取文字片段（約 {len(self.selected_text)} 字）")
        else:
            self.radio_current = QRadioButton(f"📄 當前編輯章節（{current_title}）")
        self.radio_current.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_group.addButton(self.radio_current)
        mode_layout.addWidget(self.radio_current)

        self.radio_custom = QRadioButton("📑 自訂勾選部分章節")
        self.radio_custom.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_group.addButton(self.radio_custom)
        mode_layout.addWidget(self.radio_custom)

        self.radio_all.setChecked(True)
        self.radio_all.toggled.connect(self._on_mode_changed)
        self.radio_current.toggled.connect(self._on_mode_changed)
        self.radio_custom.toggled.connect(self._on_mode_changed)

        layout.addWidget(mode_box)

        # 自訂章節樹容器
        self.tree_container = QWidget()
        tree_layout = QVBoxLayout(self.tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        tree_layout.setSpacing(int(6 * sf))

        tree_header = QHBoxLayout()
        tree_lbl = QLabel("勾選欲納入分析的章節：")
        tree_lbl.setFont(FontManager.get_font(size=int(9 * sf)))
        tree_header.addWidget(tree_lbl)
        tree_header.addStretch()

        btn_header_style = f"""
            QPushButton {{
                background-color: #2c313a;
                color: #e3e3e3;
                border: 1px solid #4b5263;
                border-radius: {int(4 * sf)}px;
                padding: {int(3 * sf)}px {int(8 * sf)}px;
            }}
            QPushButton:hover {{
                background-color: #3e4451;
                border-color: #61afef;
            }}
        """

        self.btn_select_all = QPushButton("☑ 全選")
        self.btn_select_all.setFont(FontManager.get_font(size=int(8 * sf)))
        self.btn_select_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_all.setStyleSheet(btn_header_style)
        self.btn_select_all.clicked.connect(self.select_all_items)
        tree_header.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("☐ 全不選")
        self.btn_deselect_all.setFont(FontManager.get_font(size=int(8 * sf)))
        self.btn_deselect_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_deselect_all.setStyleSheet(btn_header_style)
        self.btn_deselect_all.clicked.connect(self.deselect_all_items)
        tree_header.addWidget(self.btn_deselect_all)

        tree_layout.addLayout(tree_header)

        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.setFont(FontManager.get_font(size=int(9 * sf)))
        self.tree_widget.setStyleSheet(f"""
            QTreeWidget {{
                background-color: #1e2227;
                color: #e3e3e3;
                border: 1px solid #4b5263;
                border-radius: {int(4 * sf)}px;
                padding: {int(4 * sf)}px;
            }}
            QTreeWidget::item {{
                padding: {int(4 * sf)}px;
            }}
            QTreeWidget::item:hover {{
                background-color: #2c313a;
            }}
            QTreeWidget::item:selected {{
                background-color: #0e639c;
                color: #ffffff;
            }}
            QTreeWidget::indicator {{
                width: {int(15 * sf)}px;
                height: {int(15 * sf)}px;
            }}
        """)
        self.tree_widget.itemChanged.connect(self._on_tree_item_changed)
        tree_layout.addWidget(self.tree_widget, 1)

        self.tree_container.setVisible(False)
        layout.addWidget(self.tree_container, 1)

        # 分析標題自訂
        title_box = QHBoxLayout()
        title_box.setSpacing(int(8 * sf))
        lbl_title = QLabel("分析範圍名稱：")
        lbl_title.setFont(FontManager.get_font(size=int(9 * sf), weight=QFont.Weight.Bold))
        self.txt_title = QLineEdit("全書角色分析")
        self.txt_title.setFont(FontManager.get_font(size=int(9 * sf)))
        self.txt_title.setStyleSheet(f"""
            QLineEdit {{
                background-color: #1e2227;
                color: #ffffff;
                border: 1px solid #4b5263;
                border-radius: {int(4 * sf)}px;
                padding: {int(4 * sf)}px {int(8 * sf)}px;
                min-height: {int(24 * sf)}px;
            }}
            QLineEdit:focus {{
                border: 1px solid #61afef;
            }}
        """)
        title_box.addWidget(lbl_title)
        title_box.addWidget(self.txt_title, 1)
        layout.addLayout(title_box)

        # 預估字數與階段說明
        self.lbl_stats = QLabel("預估字數：統計中...")
        self.lbl_stats.setFont(FontManager.get_font(size=int(9 * sf)))
        self.lbl_stats.setStyleSheet("color: #61afef; font-weight: 500;")
        layout.addWidget(self.lbl_stats)

        # 分隔線
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("color: #4b5263; background-color: #4b5263;")
        line.setFixedHeight(1)
        layout.addWidget(line)

        # 底部按鈕
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(int(8 * sf))
        btn_layout.addStretch()

        self.btn_start = QPushButton("🚀 開始提取分析")
        self.btn_start.setFont(FontManager.get_font(size=int(9 * sf), weight=QFont.Weight.Bold))
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.setStyleSheet(f"""
            QPushButton {{
                background-color: #0e639c;
                color: #ffffff;
                padding: {int(6 * sf)}px {int(18 * sf)}px;
                border: 1px solid #1177bb;
                border-radius: {int(4 * sf)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #1177bb;
                border-color: #4fc1ff;
            }}
        """)
        self.btn_start.clicked.connect(self._on_start_clicked)
        btn_layout.addWidget(self.btn_start)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: #2c313a;
                color: #e3e3e3;
                border: 1px solid #4b5263;
                border-radius: {int(4 * sf)}px;
                padding: {int(6 * sf)}px {int(14 * sf)}px;
            }}
            QPushButton:hover {{
                background-color: #3e4451;
                border-color: #61afef;
            }}
        """)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)

    def populate_tree(self):
        if not self.main_window or not hasattr(self.main_window, 'tree_widget'):
            return

        for i in range(self.main_window.tree_widget.topLevelItemCount()):
            src_item = self.main_window.tree_widget.topLevelItem(i)
            self.tree_widget.addTopLevelItem(self._copy_tree_item(src_item))

    def _copy_tree_item(self, src_item):
        dest = QTreeWidgetItem()
        dest.setText(0, src_item.text(0))
        dest.setIcon(0, src_item.icon(0))
        data = src_item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, dict):
            dest.setData(0, Qt.ItemDataRole.UserRole, dict(data))
        else:
            dest.setData(0, Qt.ItemDataRole.UserRole, data)

        if isinstance(data, dict):
            item_id = data.get("id")
            if item_id:
                self.item_map[item_id] = dest

        dest.setFlags(dest.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        dest.setCheckState(0, Qt.CheckState.Checked)
        dest.setExpanded(src_item.isExpanded())

        for i in range(src_item.childCount()):
            dest.addChild(self._copy_tree_item(src_item.child(i)))
        return dest

    def _on_mode_changed(self):
        is_custom = self.radio_custom.isChecked()
        self.tree_container.setVisible(is_custom)

        if self.radio_all.isChecked():
            self.txt_title.setText("全書角色分析")
        elif self.radio_current.isChecked():
            current_name = self.current_item.text(0) if self.current_item else "當前章節"
            self.txt_title.setText(f"【{current_name}】角色分析")
        else:
            self.txt_title.setText("自訂章節角色分析")

        self.update_statistics()

    def select_all_items(self):
        self._set_all_check_state(Qt.CheckState.Checked)

    def deselect_all_items(self):
        self._set_all_check_state(Qt.CheckState.Unchecked)

    def _set_all_check_state(self, state):
        self.tree_widget.blockSignals(True)
        for i in range(self.tree_widget.topLevelItemCount()):
            self._check_recursive(self.tree_widget.topLevelItem(i), state)
        self.tree_widget.blockSignals(False)
        self.update_statistics()

    def _check_recursive(self, item, state):
        item.setCheckState(0, state)
        for i in range(item.childCount()):
            self._check_recursive(item.child(i), state)

    def _on_tree_item_changed(self, item, column):
        if column != 0:
            return
        state = item.checkState(0)
        self.tree_widget.blockSignals(True)
        for i in range(item.childCount()):
            self._check_recursive(item.child(i), state)
        self.tree_widget.blockSignals(False)
        self.update_statistics()

    def update_statistics(self):
        data = self.get_scope_content()
        char_count = len(data["text_content"])
        chapter_count = data["chapter_count"]

        if char_count > 4000:
            chunks = (char_count + 3999) // 4000
            self.lbl_stats.setText(
                f"包含 {chapter_count} 個章節，總計約 {char_count:,} 字（長文滾動分析，預計分為 {chunks + 1} 階段）"
            )
        else:
            self.lbl_stats.setText(
                f"包含 {chapter_count} 個章節，總計約 {char_count:,} 字（單次精確分析）"
            )

    def _get_item_text_content(self, item: QTreeWidgetItem) -> str:
        """從記憶體節點、編輯器或資料庫獲取章節/幕內文"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(data, dict):
            return ""

        node_id = data.get("id")

        # 1. 若是當前主編輯器開啟的章節，優先取最新編輯器文字
        if self.main_window and hasattr(self.main_window, 'editor'):
            curr_id = None
            if hasattr(self.main_window, 'active_file_id'):
                curr_id = self.main_window.active_file_id
            elif hasattr(self.main_window, 'current_item') and self.main_window.current_item:
                c_data = self.main_window.current_item.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(c_data, dict):
                    curr_id = c_data.get("id")

            if curr_id and node_id and curr_id == node_id:
                editor_text = self.main_window.editor.toPlainText()
                if editor_text:
                    return editor_text

        # 2. 直接從記憶體節點中取得 content
        content = data.get("content", "")
        if content:
            return content

        # 3. 備用：若記憶體中為空且有資料庫檔案，從 SQLite 資料庫讀取
        db_path = getattr(self.main_window, 'project_db_path', None) or getattr(self.main_window, 'project_path', None)
        if db_path and os.path.exists(db_path) and node_id:
            try:
                import sqlite3
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                c.execute("SELECT content FROM chapters WHERE id=?", (node_id,))
                row = c.fetchone()
                conn.close()
                if row and row[0]:
                    return row[0]
            except Exception:
                pass

        return ""

    def get_scope_content(self) -> dict:
        """根據選擇模式取得拼接後的文本與統計"""
        if self.radio_current.isChecked():
            if self.selected_text:
                return {
                    "scope_mode": "selection",
                    "scope_title": self.txt_title.text().strip() or "選取片段角色分析",
                    "text_content": self.selected_text,
                    "chapter_count": 1
                }
            else:
                curr_name = self.current_item.text(0) if self.current_item else "當前章節"
                curr_chapters = []

                def collect_current(item):
                    if not item:
                        return
                    c_text = self._get_item_text_content(item)
                    if c_text.strip():
                        curr_chapters.append((item.text(0).strip(), c_text))
                    for i in range(item.childCount()):
                        collect_current(item.child(i))

                if self.current_item:
                    collect_current(self.current_item)
                else:
                    curr_text = self.main_window.editor.toPlainText() if self.main_window and hasattr(self.main_window, 'editor') else ""
                    if curr_text.strip():
                        curr_chapters.append((curr_name, curr_text))

                combined_texts = []
                for ch_title, ch_text in curr_chapters:
                    combined_texts.append(f"### 章節：{ch_title}\n\n{ch_text}")

                full_text = "\n\n---\n\n".join(combined_texts)
                return {
                    "scope_mode": "current",
                    "scope_title": self.txt_title.text().strip() or f"【{curr_name}】角色分析",
                    "text_content": full_text,
                    "chapter_count": len(curr_chapters)
                }

        # 全文 (all) 或自訂勾選 (custom)
        collected_chapters = []
        is_all = self.radio_all.isChecked()

        def collect(item):
            data = item.data(0, Qt.ItemDataRole.UserRole)
            is_checked = (item.checkState(0) == Qt.CheckState.Checked) if not is_all else True

            # 若此節點被勾選，且本身包含有效文字內容
            if is_checked and isinstance(data, dict):
                content = self._get_item_text_content(item)
                if content.strip():
                    collected_chapters.append((item.text(0).strip(), content))

            # 無論此節點本身是否有文字，繼續遞迴收集其子節點
            for i in range(item.childCount()):
                collect(item.child(i))

        if self.tree_widget.topLevelItemCount() > 0:
            for i in range(self.tree_widget.topLevelItemCount()):
                collect(self.tree_widget.topLevelItem(i))
        else:
            # 若無 tree 則抓取當前
            curr_text = self.main_window.editor.toPlainText() if self.main_window and hasattr(self.main_window, 'editor') else ""
            if curr_text.strip():
                collected_chapters.append(("當前章節", curr_text))

        combined_texts = []
        for ch_title, ch_text in collected_chapters:
            combined_texts.append(f"### 章節：{ch_title}\n\n{ch_text}")

        full_text = "\n\n---\n\n".join(combined_texts)
        return {
            "scope_mode": "all" if is_all else "custom",
            "scope_title": self.txt_title.text().strip() or ("全書角色分析" if is_all else "自訂章節角色分析"),
            "text_content": full_text,
            "chapter_count": len(collected_chapters)
        }

    def _on_start_clicked(self):
        data = self.get_scope_content()
        if not data["text_content"].strip():
            QMessageBox.warning(self, "提示", "所選範圍內無有效小說文字可供分析。")
            return
        self.accept()
