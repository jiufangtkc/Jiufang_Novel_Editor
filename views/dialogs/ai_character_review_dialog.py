from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QTextEdit, QWidget,
    QFrame, QSplitter, QMessageBox, QApplication, QStackedWidget
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from utils.font_manager import FontManager
from utils.theme_manager import ThemeManager
from utils.markdown_highlighter import MarkdownHighlighter
from utils.markdown_utils import markdown_to_html, document_to_markdown


class AICharacterReviewDialog(QDialog):
    """
    AI 角色提取結果審核與批次建立對話框。
    左側：角色卡清單與關係卡（支援核取方塊多選）
    右側：選取卡片之標題、標籤、內文編輯與 Markdown 富文本預覽
    """

    def __init__(self, parent=None, result_data=None):
        super().__init__(parent)
        self.main_window = parent
        self.result_data = result_data or {}
        self.cards_data = []
        self.scale_factor = getattr(parent, "scale_factor", 1.0) if parent else 1.0

        self.setWindowTitle("AI 登場角色提取 — 結果審核與卡片建立")
        self.resize(int(960 * self.scale_factor), int(700 * self.scale_factor))
        self.setMinimumSize(int(680 * self.scale_factor), int(500 * self.scale_factor))
        self.setModal(True)
        if parent:
            self.setStyleSheet(parent.styleSheet())

        self._parse_initial_cards()
        self.init_ui()
        self._populate_card_list()

    def _parse_initial_cards(self):
        """將 AIWorker 回傳之解析資料轉換為可編輯清單"""
        parsed_chars = self.result_data.get("parsed_characters", [])
        parsed_rel = self.result_data.get("parsed_relationship")

        for c in parsed_chars:
            self.cards_data.append({
                "type": "character",
                "name": c.get("name", "未命名角色"),
                "title": c.get("title", f"【角色】{c.get('name', '未命名')}"),
                "tags": c.get("tags", ["AI角色", "人物設定"]),
                "summary": c.get("summary", ""),
                "content": c.get("content", ""),
                "selected": True
            })

        if parsed_rel:
            self.cards_data.append({
                "type": "relationship",
                "name": "角色關係網",
                "title": parsed_rel.get("title", "【角色關係網】全景梳理"),
                "tags": parsed_rel.get("tags", ["AI角色關係", "關係網"]),
                "summary": parsed_rel.get("summary", ""),
                "content": parsed_rel.get("content", ""),
                "selected": True
            })

        # 若無解析資料則使用 raw content
        if not self.cards_data:
            raw_title = self.result_data.get("title", "【角色分析】登場人物")
            raw_content = self.result_data.get("content", "")
            self.cards_data.append({
                "type": "character",
                "name": "登場角色總結",
                "title": raw_title,
                "tags": ["AI角色", "人物設定"],
                "summary": raw_content.replace('\n', ' ')[:90],
                "content": raw_content,
                "selected": True
            })

    def init_ui(self):
        sf = self.scale_factor
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(int(16 * sf), int(16 * sf), int(16 * sf), int(16 * sf))
        main_layout.setSpacing(int(10 * sf))

        # 頂部提示
        lbl_hint = QLabel(f"AI 已成功提取 {len(self.cards_data)} 張卡片！請勾選欲建立的卡片並確認內容：")
        lbl_hint.setFont(FontManager.get_font(size=int(10 * sf), weight=QFont.Weight.Bold))
        main_layout.addWidget(lbl_hint)

        # 中間分割畫面
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # === 左側面板：卡片清單 ===
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(int(8 * sf))

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

        left_btn_layout = QHBoxLayout()
        self.btn_select_all = QPushButton("☑ 全選")
        self.btn_select_all.setFont(FontManager.get_font(size=int(8 * sf)))
        self.btn_select_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_all.setStyleSheet(btn_header_style)
        self.btn_select_all.clicked.connect(self._select_all_cards)
        left_btn_layout.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("☐ 全不選")
        self.btn_deselect_all.setFont(FontManager.get_font(size=int(8 * sf)))
        self.btn_deselect_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_deselect_all.setStyleSheet(btn_header_style)
        self.btn_deselect_all.clicked.connect(self._deselect_all_cards)
        left_btn_layout.addWidget(self.btn_deselect_all)

        left_btn_layout.addStretch()
        left_layout.addLayout(left_btn_layout)

        check_icon = ThemeManager._get_checkmark_icon_path()
        self.card_list_widget = QListWidget()
        self.card_list_widget.setFont(FontManager.get_font(size=int(9 * sf)))
        self.card_list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: #1e2227;
                color: #e3e3e3;
                border: 1px solid #4b5263;
                border-radius: {int(6 * sf)}px;
                padding: {int(4 * sf)}px;
            }}
            QListWidget::item {{
                padding: {int(8 * sf)}px {int(6 * sf)}px;
                border-radius: {int(4 * sf)}px;
                margin-bottom: {int(3 * sf)}px;
            }}
            QListWidget::item:hover {{
                background-color: #2c313a;
            }}
            QListWidget::item:selected {{
                background-color: #0e639c;
                color: #ffffff;
            }}
            QListWidget::indicator {{
                width: {int(16 * sf)}px;
                height: {int(16 * sf)}px;
                border: 2px solid #8c939d;
                border-radius: 3px;
                background-color: #1a1d22;
            }}
            QListWidget::indicator:hover {{
                border-color: #61afef;
            }}
            QListWidget::indicator:checked {{
                background-color: #0e639c;
                border-color: #61afef;
                image: url('{check_icon}');
            }}
        """)
        self.card_list_widget.currentRowChanged.connect(self._on_card_selection_changed)
        self.card_list_widget.itemChanged.connect(self._on_item_check_changed)
        left_layout.addWidget(self.card_list_widget, 1)

        splitter.addWidget(left_widget)

        # === 右側面板：卡片編輯與渲染預覽 ===
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(int(8 * sf), 0, 0, 0)
        right_layout.setSpacing(int(8 * sf))

        input_style = f"""
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
        """

        # 標題與標籤列
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(int(6 * sf))
        lbl_t = QLabel("卡片名稱：")
        lbl_t.setFont(FontManager.get_font(size=int(9 * sf), weight=QFont.Weight.Bold))
        self.txt_title = QLineEdit()
        self.txt_title.setFont(FontManager.get_font(size=int(10 * sf), weight=QFont.Weight.Bold))
        self.txt_title.setStyleSheet(input_style)
        self.txt_title.textChanged.connect(self._save_current_card_meta)
        meta_layout.addWidget(lbl_t)
        meta_layout.addWidget(self.txt_title, 1)
        right_layout.addLayout(meta_layout)

        tag_layout = QHBoxLayout()
        tag_layout.setSpacing(int(6 * sf))
        lbl_tags = QLabel("標籤設定：")
        lbl_tags.setFont(FontManager.get_font(size=int(9 * sf)))
        self.txt_tags = QLineEdit()
        self.txt_tags.setFont(FontManager.get_font(size=int(9 * sf)))
        self.txt_tags.setPlaceholderText("請以逗號或空格分隔標籤")
        self.txt_tags.setStyleSheet(input_style)
        self.txt_tags.textChanged.connect(self._save_current_card_meta)
        tag_layout.addWidget(lbl_tags)
        tag_layout.addWidget(self.txt_tags, 1)

        self.btn_toggle_preview = QPushButton("📖 渲染預覽")
        self.btn_toggle_preview.setFont(FontManager.get_font(size=int(8 * sf), weight=QFont.Weight.Bold))
        self.btn_toggle_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_preview.setStyleSheet(f"""
            QPushButton {{
                background-color: #2c313a;
                color: #e3e3e3;
                border: 1px solid #4b5263;
                border-radius: {int(4 * sf)}px;
                padding: {int(4 * sf)}px {int(10 * sf)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #3e4451;
                border-color: #61afef;
            }}
        """)
        self.btn_toggle_preview.clicked.connect(self._toggle_preview)
        tag_layout.addWidget(self.btn_toggle_preview)

        right_layout.addLayout(tag_layout)

        # Stack: 編輯器 vs 富文本渲染
        self.stack = QStackedWidget()

        editor_style = f"""
            QTextEdit {{
                background-color: #1e2227;
                color: #dcdcdc;
                border: 1px solid #4b5263;
                border-radius: {int(4 * sf)}px;
                padding: {int(8 * sf)}px;
            }}
            QTextEdit:focus {{
                border: 1px solid #61afef;
            }}
        """

        self.editor = QTextEdit()
        self.editor.setAcceptRichText(True)
        self.editor.setFont(FontManager.get_font(size=int(10 * sf)))
        self.editor.setStyleSheet(editor_style)
        self.editor.textChanged.connect(self._save_current_card_content)
        self.stack.addWidget(self.editor)

        self.preview_browser = QTextEdit()
        self.preview_browser.setReadOnly(True)
        self.preview_browser.setFont(FontManager.get_font(size=int(10 * sf)))
        self.preview_browser.setStyleSheet(editor_style)
        self.stack.addWidget(self.preview_browser)

        right_layout.addWidget(self.stack, 1)
        splitter.addWidget(right_widget)

        splitter.setSizes([int(320 * sf), int(640 * sf)])
        main_layout.addWidget(splitter, 1)

        # 底部按鈕列
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(int(8 * sf))

        self.lbl_selected_count = QLabel("已勾選 0 張卡片")
        self.lbl_selected_count.setFont(FontManager.get_font(size=int(9 * sf)))
        self.lbl_selected_count.setStyleSheet("color: #61afef; font-weight: 500;")
        bottom_layout.addWidget(self.lbl_selected_count)

        bottom_layout.addStretch()

        self.btn_import_all = QPushButton("✨ 一鍵建立至資料集角色卡")
        self.btn_import_all.setFont(FontManager.get_font(size=int(9 * sf), weight=QFont.Weight.Bold))
        self.btn_import_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_import_all.setStyleSheet(f"""
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
        self.btn_import_all.clicked.connect(self._on_import_clicked)
        bottom_layout.addWidget(self.btn_import_all)

        self.btn_cancel = QPushButton("關閉")
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
        bottom_layout.addWidget(self.btn_cancel)

        main_layout.addLayout(bottom_layout)

    def _populate_card_list(self):
        self.card_list_widget.blockSignals(True)
        self.card_list_widget.clear()

        for idx, card in enumerate(self.cards_data):
            icon_str = "🕸️" if card["type"] == "relationship" else "👤"
            item = QListWidgetItem(f"{icon_str} {card['title']}")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if card.get("selected", True) else Qt.CheckState.Unchecked)
            self.card_list_widget.addItem(item)

        self.card_list_widget.blockSignals(False)
        if self.cards_data:
            self.card_list_widget.setCurrentRow(0)
        self._update_selected_count()

    def _on_card_selection_changed(self, row: int):
        if 0 <= row < len(self.cards_data):
            card = self.cards_data[row]
            self.txt_title.blockSignals(True)
            self.txt_tags.blockSignals(True)
            self.editor.blockSignals(True)

            self.txt_title.setText(card.get("title", ""))
            tags = card.get("tags", [])
            self.txt_tags.setText(", ".join(tags) if isinstance(tags, list) else str(tags))
            raw_content = card.get("content", "")
            self.editor.setHtml(markdown_to_html(raw_content))

            self.txt_title.blockSignals(False)
            self.txt_tags.blockSignals(False)
            self.editor.blockSignals(False)

            if self.stack.currentIndex() == 1:
                html = markdown_to_html(raw_content)
                self.preview_browser.setHtml(html)

    def _save_current_card_meta(self):
        row = self.card_list_widget.currentRow()
        if 0 <= row < len(self.cards_data):
            self.cards_data[row]["title"] = self.txt_title.text().strip()
            raw_tags = self.txt_tags.text().replace("，", ",").split(",")
            self.cards_data[row]["tags"] = [t.strip() for t in raw_tags if t.strip()]

            # 更新 list item text
            item = self.card_list_widget.item(row)
            if item:
                icon_str = "🕸️" if self.cards_data[row]["type"] == "relationship" else "👤"
                item.setText(f"{icon_str} {self.cards_data[row]['title']}")

    def _save_current_card_content(self):
        row = self.card_list_widget.currentRow()
        if 0 <= row < len(self.cards_data):
            content = document_to_markdown(self.editor.document())
            self.cards_data[row]["content"] = content
            if self.stack.currentIndex() == 1:
                self.preview_browser.setHtml(markdown_to_html(content))

    def _on_item_check_changed(self, item):
        row = self.card_list_widget.row(item)
        if 0 <= row < len(self.cards_data):
            self.cards_data[row]["selected"] = (item.checkState() == Qt.CheckState.Checked)
            self._update_selected_count()

    def _select_all_cards(self):
        self.card_list_widget.blockSignals(True)
        for i in range(self.card_list_widget.count()):
            self.card_list_widget.item(i).setCheckState(Qt.CheckState.Checked)
            if i < len(self.cards_data):
                self.cards_data[i]["selected"] = True
        self.card_list_widget.blockSignals(False)
        self._update_selected_count()

    def _deselect_all_cards(self):
        self.card_list_widget.blockSignals(True)
        for i in range(self.card_list_widget.count()):
            self.card_list_widget.item(i).setCheckState(Qt.CheckState.Unchecked)
            if i < len(self.cards_data):
                self.cards_data[i]["selected"] = False
        self.card_list_widget.blockSignals(False)
        self._update_selected_count()

    def _update_selected_count(self):
        selected = sum(1 for c in self.cards_data if c.get("selected", True))
        self.lbl_selected_count.setText(f"已勾選 {selected} / {len(self.cards_data)} 張卡片即將建立至資料集")
        self.btn_import_all.setEnabled(selected > 0)

    def _toggle_preview(self):
        if self.stack.currentIndex() == 0:
            content = document_to_markdown(self.editor.document())
            self.preview_browser.setHtml(markdown_to_html(content))
            self.stack.setCurrentIndex(1)
            self.btn_toggle_preview.setText("📝 返回編輯")
        else:
            self.stack.setCurrentIndex(0)
            self.btn_toggle_preview.setText("📖 渲染預覽")

    def _on_import_clicked(self):
        selected_cards = self.get_selected_cards()
        if not selected_cards:
            QMessageBox.warning(self, "提示", "請至少勾選一張欲建立的卡片。")
            return
        self.accept()

    def get_selected_cards(self) -> list[dict]:
        """回傳所有被勾選的卡片資料"""
        results = []
        for c in self.cards_data:
            if c.get("selected", True):
                results.append({
                    "category": "character",
                    "title": c.get("title", "未命名卡片"),
                    "content": c.get("content", ""),
                    "tags": c.get("tags", []),
                    "summary": c.get("summary", "")
                })
        return results
