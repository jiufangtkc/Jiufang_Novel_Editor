import os
from typing import List, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QComboBox, QCheckBox, QRadioButton,
    QButtonGroup, QFrame, QLineEdit, QFileDialog, QSplitter, QWidget,
    QGroupBox, QMessageBox
)
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt, pyqtSignal

from utils.font_manager import FontManager
from utils.theme_manager import ThemeManager, create_custom_icon
from services.import_service import ImportService, ImportOptions, DEFAULT_VOLUME_REGEX, DEFAULT_CHAPTER_REGEX, DEFAULT_SCENE_REGEX
from models.models import ChapterNode


class ImportPreviewDialog(QDialog):
    """外部文件匯入預覽與設定對話框。"""

    def __init__(self, parent=None, default_file_path: str = "", current_target_name: str = ""):
        super().__init__(parent)
        self.parent_win = parent
        self.file_path = default_file_path
        self.current_target_name = current_target_name
        self.parsed_nodes: List[ChapterNode] = []

        self.setWindowTitle("匯入外部文件至作品面板")
        ThemeManager.apply_theme_to_dialog(self, parent)
        self.scale_factor = getattr(self, "scale_factor", 1.0)
        sf = self.scale_factor
        self.resize(int(820 * sf), int(620 * sf))
        self.setModal(True)

        self._init_ui(sf)

        if self.file_path and os.path.exists(self.file_path):
            self.txt_file_path.setText(self.file_path)
            self._parse_and_preview()

    def _init_ui(self, sf: float):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(int(16 * sf), int(16 * sf), int(16 * sf), int(16 * sf))
        main_layout.setSpacing(int(10 * sf))

        # 1. 頂部：檔案選取列
        file_box = QHBoxLayout()
        file_box.setSpacing(int(8 * sf))
        lbl_file = QLabel("選擇檔案/目錄：")
        lbl_file.setFont(FontManager.get_font(size=int(10 * sf), weight=QFont.Weight.Bold))
        self.txt_file_path = QLineEdit()
        self.txt_file_path.setPlaceholderText("請選擇 .txt、.md、.docx 檔案或資料夾...")
        self.txt_file_path.setFont(FontManager.get_font(size=int(9.5 * sf)))

        btn_browse_file = QPushButton("瀏覽檔案...")
        btn_browse_file.setFont(FontManager.get_font(size=int(9 * sf)))
        btn_browse_file.clicked.connect(self._on_browse_file)

        btn_browse_dir = QPushButton("選擇資料夾...")
        btn_browse_dir.setFont(FontManager.get_font(size=int(9 * sf)))
        btn_browse_dir.clicked.connect(self._on_browse_dir)

        file_box.addWidget(lbl_file)
        file_box.addWidget(self.txt_file_path, 1)
        file_box.addWidget(btn_browse_file)
        file_box.addWidget(btn_browse_dir)
        main_layout.addLayout(file_box)

        # 2. 中間：左右 Splitter (左邊規則設定，右邊樹狀預覽)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- 左側：設定控制面板 ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, int(8 * sf), 0)
        left_layout.setSpacing(int(10 * sf))

        # (A) 切分模式
        grp_mode = QGroupBox("切分規則")
        grp_mode.setFont(FontManager.get_font(size=int(9.5 * sf), weight=QFont.Weight.Bold))
        v_mode = QVBoxLayout(grp_mode)
        v_mode.setSpacing(int(6 * sf))

        self.combo_mode = QComboBox()
        self.combo_mode.setFont(FontManager.get_font(size=int(9 * sf)))
        self.combo_mode.addItem("中文小說常規（第X卷、第X章）", "novel_regex")
        self.combo_mode.addItem("Markdown 標題層級 (#, ##, ###)", "markdown")
        self.combo_mode.addItem("整檔不切分（單一章節）", "single_chapter")
        self.combo_mode.addItem("自訂正規表達式", "custom_regex")
        self.combo_mode.currentIndexChanged.connect(self._on_mode_changed)
        v_mode.addWidget(self.combo_mode)

        # 編碼選擇
        h_enc = QHBoxLayout()
        lbl_enc = QLabel("文字編碼：")
        lbl_enc.setFont(FontManager.get_font(size=int(9 * sf)))
        self.combo_encoding = QComboBox()
        self.combo_encoding.setFont(FontManager.get_font(size=int(9 * sf)))
        self.combo_encoding.addItem("自動偵測", "auto")
        self.combo_encoding.addItem("UTF-8", "utf-8")
        self.combo_encoding.addItem("繁體中文 (Big5/CP950)", "cp950")
        self.combo_encoding.addItem("簡體中文 (GB18030)", "gb18030")
        self.combo_encoding.currentIndexChanged.connect(self._on_encoding_changed)
        h_enc.addWidget(lbl_enc)
        h_enc.addWidget(self.combo_encoding, 1)
        v_mode.addLayout(h_enc)

        # 自訂正則欄位
        self.lbl_vol_regex = QLabel("分卷規則 (Regex)：")
        self.lbl_vol_regex.setFont(FontManager.get_font(size=int(8.5 * sf)))
        self.txt_vol_regex = QLineEdit(DEFAULT_VOLUME_REGEX)
        self.txt_vol_regex.setFont(FontManager.get_font(size=int(8.5 * sf)))
        v_mode.addWidget(self.lbl_vol_regex)
        v_mode.addWidget(self.txt_vol_regex)

        self.lbl_chap_regex = QLabel("分章規則 (Regex)：")
        self.lbl_chap_regex.setFont(FontManager.get_font(size=int(8.5 * sf)))
        self.txt_chap_regex = QLineEdit(DEFAULT_CHAPTER_REGEX)
        self.txt_chap_regex.setFont(FontManager.get_font(size=int(8.5 * sf)))
        v_mode.addWidget(self.lbl_chap_regex)
        v_mode.addWidget(self.txt_chap_regex)

        self.chk_scene = QCheckBox("啟用場景自動切分 (Scene)")
        self.chk_scene.setFont(FontManager.get_font(size=int(9 * sf)))
        self.chk_scene.toggled.connect(self._on_scene_toggled)
        v_mode.addWidget(self.chk_scene)

        self.txt_scene_regex = QLineEdit(DEFAULT_SCENE_REGEX)
        self.txt_scene_regex.setFont(FontManager.get_font(size=int(8.5 * sf)))
        self.txt_scene_regex.setEnabled(False)
        v_mode.addWidget(self.txt_scene_regex)

        btn_refresh = QPushButton("🔄 重新解析預覽")
        btn_refresh.setFont(FontManager.get_font(size=int(9 * sf), weight=QFont.Weight.Bold))
        btn_refresh.clicked.connect(self._parse_and_preview)
        v_mode.addWidget(btn_refresh)

        left_layout.addWidget(grp_mode)

        # (B) 匯入落點目標
        grp_target = QGroupBox("匯入位置")
        grp_target.setFont(FontManager.get_font(size=int(9.5 * sf), weight=QFont.Weight.Bold))
        v_target = QVBoxLayout(grp_target)
        v_target.setSpacing(int(6 * sf))

        self.target_group = QButtonGroup(self)
        self.radio_append = QRadioButton("追加至目前作品末尾")
        self.radio_append.setChecked(True)
        self.radio_append.setFont(FontManager.get_font(size=int(9 * sf)))
        self.target_group.addButton(self.radio_append)
        v_target.addWidget(self.radio_append)

        insert_text = f"插入至選取項底下「{self.current_target_name}」" if self.current_target_name else "插入至目前選取的項目底下"
        self.radio_insert = QRadioButton(insert_text)
        self.radio_insert.setFont(FontManager.get_font(size=int(9 * sf)))
        self.radio_insert.setEnabled(bool(self.current_target_name))
        self.target_group.addButton(self.radio_insert)
        v_target.addWidget(self.radio_insert)

        self.radio_new_book = QRadioButton("直接建立為全新作品（清空現有作品樹）")
        self.radio_new_book.setFont(FontManager.get_font(size=int(9 * sf)))
        self.target_group.addButton(self.radio_new_book)
        v_target.addWidget(self.radio_new_book)

        left_layout.addWidget(grp_target)
        left_layout.addStretch(1)

        splitter.addWidget(left_widget)

        # --- 右側：樹狀即時預覽面板 ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(int(8 * sf), 0, 0, 0)
        right_layout.setSpacing(int(8 * sf))

        preview_header = QHBoxLayout()
        lbl_preview = QLabel("目錄樹預覽（可勾選欲匯入之章節）：")
        lbl_preview.setFont(FontManager.get_font(size=int(9.5 * sf), weight=QFont.Weight.Bold))
        preview_header.addWidget(lbl_preview)
        preview_header.addStretch(1)

        btn_select_all = QPushButton("全選")
        btn_select_all.setFont(FontManager.get_font(size=int(8.5 * sf)))
        btn_select_all.clicked.connect(lambda: self._set_all_checked(True))
        btn_deselect_all = QPushButton("全不選")
        btn_deselect_all.setFont(FontManager.get_font(size=int(8.5 * sf)))
        btn_deselect_all.clicked.connect(lambda: self._set_all_checked(False))
        preview_header.addWidget(btn_select_all)
        preview_header.addWidget(btn_deselect_all)
        right_layout.addLayout(preview_header)

        self.tree_preview = QTreeWidget()
        self.tree_preview.setHeaderLabels(["名稱", "字數"])
        self.tree_preview.setColumnWidth(0, int(320 * sf))
        self.tree_preview.setFont(FontManager.get_font(size=int(9.5 * sf)))
        right_layout.addWidget(self.tree_preview, 1)

        self.lbl_stats = QLabel("📊 尚未載入檔案")
        self.lbl_stats.setFont(FontManager.get_font(size=int(9 * sf)))
        right_layout.addWidget(self.lbl_stats)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        main_layout.addWidget(splitter, 1)

        # 3. 底部：確認與取消按鈕
        btn_box = QHBoxLayout()
        btn_box.addStretch(1)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setFont(FontManager.get_font(size=int(9.5 * sf)))
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        self.btn_import = QPushButton("確認匯入")
        self.btn_import.setFont(FontManager.get_font(size=int(9.5 * sf), weight=QFont.Weight.Bold))
        self.btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_import.setStyleSheet("""
            QPushButton {
                background-color: #2da44e;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 6px 18px;
            }
            QPushButton:hover {
                background-color: #2c974b;
            }
            QPushButton:disabled {
                background-color: #4b5563;
                color: #9ca3af;
            }
        """)
        self.btn_import.clicked.connect(self._on_confirm_import)
        btn_box.addWidget(self.btn_import)

        main_layout.addLayout(btn_box)

        self._update_regex_visibility()

    def _on_mode_changed(self):
        self._update_regex_visibility()
        self._parse_and_preview()

    def _on_encoding_changed(self):
        self._parse_and_preview()

    def _on_scene_toggled(self, checked: bool):
        self.txt_scene_regex.setEnabled(checked)
        self._parse_and_preview()

    def _update_regex_visibility(self):
        mode = self.combo_mode.currentData()
        is_custom = (mode == "custom_regex")
        is_novel = (mode == "novel_regex")
        self.lbl_vol_regex.setVisible(is_custom or is_novel)
        self.txt_vol_regex.setVisible(is_custom or is_novel)
        self.lbl_chap_regex.setVisible(is_custom or is_novel)
        self.txt_chap_regex.setVisible(is_custom or is_novel)
        self.txt_vol_regex.setReadOnly(not is_custom)
        self.txt_chap_regex.setReadOnly(not is_custom)

    def _on_browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "選取欲匯入的小說檔案",
            "",
            "支援的所有檔案 (*.txt *.md *.docx);;純文字檔案 (*.txt);;Markdown 檔案 (*.md);;Word 文件 (*.docx);;所有檔案 (*.*)"
        )
        if path:
            self.file_path = path
            self.txt_file_path.setText(path)
            # 自動偵測檔案類型調整預設 mode
            ext = os.path.splitext(path)[1].lower()
            if ext == ".md":
                idx = self.combo_mode.findData("markdown")
                if idx >= 0:
                    self.combo_mode.setCurrentIndex(idx)
            self._parse_and_preview()

    def _on_browse_dir(self):
        path = QFileDialog.getExistingDirectory(self, "選取欲匯入的小說資料夾")
        if path:
            self.file_path = path
            self.txt_file_path.setText(path)
            self._parse_and_preview()

    def _get_current_options(self) -> ImportOptions:
        mode = self.combo_mode.currentData()
        return ImportOptions(
            mode=mode,
            volume_regex=self.txt_vol_regex.text().strip(),
            chapter_regex=self.txt_chap_regex.text().strip(),
            enable_scene_split=self.chk_scene.isChecked(),
            scene_regex=self.txt_scene_regex.text().strip(),
            encoding=self.combo_encoding.currentData() or "auto"
        )

    def _parse_and_preview(self):
        path = self.txt_file_path.text().strip()
        if not path or not os.path.exists(path):
            self.tree_preview.clear()
            self.lbl_stats.setText("⚠️ 請先選擇有效的檔案或資料夾路徑")
            self.btn_import.setEnabled(False)
            return

        options = self._get_current_options()

        try:
            if os.path.isdir(path):
                nodes = ImportService.parse_directory(path, options)
            else:
                nodes = ImportService.parse_file(path, options)
        except Exception as e:
            QMessageBox.critical(self, "解析失敗", f"讀取或解析檔案時發生錯誤：\n{str(e)}")
            return

        self.parsed_nodes = nodes
        self._populate_preview_tree(nodes)

    def _populate_preview_tree(self, nodes: List[ChapterNode]):
        self.tree_preview.clear()
        total_vols = 0
        total_chaps = 0
        total_words = 0

        folder_icon = create_custom_icon("folder", "#F7BA3E", self.scale_factor)
        file_icon = create_custom_icon("file", "#D8D8D8", self.scale_factor)
        scene_icon = create_custom_icon("folder", "#7EB8F7", self.scale_factor)

        def add_node_item(node: ChapterNode, parent_item=None) -> QTreeWidgetItem:
            nonlocal total_vols, total_chaps, total_words
            words = len(node.content.replace(" ", "").replace("\n", "")) if node.content else 0
            word_str = f"{words} 字" if node.node_type in ("file", "scene") else ""

            item = QTreeWidgetItem([node.name, word_str])
            item.setCheckState(0, Qt.CheckState.Checked)
            item.setData(0, Qt.ItemDataRole.UserRole, node)

            if node.node_type == "folder":
                item.setIcon(0, folder_icon)
                total_vols += 1
            elif node.node_type == "scene":
                item.setIcon(0, scene_icon)
                total_chaps += 1
                total_words += words
            else:
                item.setIcon(0, file_icon)
                total_chaps += 1
                total_words += words

            if parent_item:
                parent_item.addChild(item)
            else:
                self.tree_preview.addTopLevelItem(item)

            for child in node.children:
                add_node_item(child, item)

            item.setExpanded(True)
            return item

        for root_node in nodes:
            add_node_item(root_node)

        self.tree_preview.expandAll()
        self.lbl_stats.setText(f"📊 共解析出 {total_vols} 卷、{total_chaps} 個章節/場景，總字數約 {total_words:,} 字")
        self.btn_import.setEnabled(len(nodes) > 0)

    def _set_all_checked(self, checked: bool):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked

        def set_state_recursive(item: QTreeWidgetItem):
            item.setCheckState(0, state)
            for i in range(item.childCount()):
                set_state_recursive(item.child(i))

        for i in range(self.tree_preview.topLevelItemCount()):
            set_state_recursive(self.tree_preview.topLevelItem(i))

    def get_selected_nodes(self) -> List[ChapterNode]:
        """過濾出使用者勾選的章節節點樹。"""
        def filter_node(item: QTreeWidgetItem) -> Optional[ChapterNode]:
            is_checked = (item.checkState(0) == Qt.CheckState.Checked)
            node: ChapterNode = item.data(0, Qt.ItemDataRole.UserRole)
            if not node:
                return None

            # 遞迴檢查子項目
            selected_children: List[ChapterNode] = []
            for i in range(item.childCount()):
                child_item = item.child(i)
                child_node = filter_node(child_item)
                if child_node is not None:
                    selected_children.append(child_node)

            # 如果本項目被勾選，或者它的子項目有被勾選，則保留此節點
            if is_checked or selected_children:
                return ChapterNode(
                    name=node.name,
                    node_type=node.node_type,
                    id=node.id,
                    content=node.content if is_checked else "",
                    mark=node.mark,
                    scene_summary=node.scene_summary,
                    scene_pov=node.scene_pov,
                    scene_location=node.scene_location,
                    children=selected_children
                )
            return None

        result: List[ChapterNode] = []
        for i in range(self.tree_preview.topLevelItemCount()):
            item = self.tree_preview.topLevelItem(i)
            filtered = filter_node(item)
            if filtered:
                result.append(filtered)
        return result

    def get_import_target(self) -> str:
        """回傳匯入目標：'append' (追加末尾), 'insert' (插入選取項下), 'new_book' (建立全新作品)。"""
        if self.radio_new_book.isChecked():
            return "new_book"
        elif self.radio_insert.isChecked():
            return "insert"
        return "append"

    def _on_confirm_import(self):
        selected = self.get_selected_nodes()
        if not selected:
            QMessageBox.warning(self, "提示", "請在右側目錄樹中至少勾選一個欲匯入的項目。")
            return
        self.accept()
