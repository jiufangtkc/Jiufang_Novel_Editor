import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QComboBox, QCheckBox, QRadioButton,
    QButtonGroup, QFrame
)
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor, QPen
from PyQt6.QtCore import Qt
from utils.font_manager import FontManager


class ExportScopeDialog(QDialog):
    """匯出範圍與格式選擇對話框。"""

    def __init__(self, parent=None, checked_item=None, default_title=""):
        super().__init__(parent)
        self.parent_win = parent
        self.default_title = default_title
        self.setWindowTitle("匯出作品與格式設定")
        self.resize(480, 580)
        self.setModal(True)

        self._ensure_checkbox_icons()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # 頂部說明
        lbl_hint = QLabel("請勾選欲匯出的文件與章節：")
        lbl_hint.setFont(FontManager.get_font(size=10, weight=QFont.Weight.Bold))
        layout.addWidget(lbl_hint)

        # 樹狀目錄
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        if parent and hasattr(parent, 'tree_widget'):
            self.tree_widget.setIconSize(parent.tree_widget.iconSize())

        # 設定高對比度核取方塊樣式
        icon_checked_path = os.path.abspath("resources/icons/checkbox_checked.png").replace("\\", "/")
        icon_unchecked_path = os.path.abspath("resources/icons/checkbox_unchecked.png").replace("\\", "/")
        
        self.tree_widget.setStyleSheet(f"""
            QTreeWidget {{
                background-color: #1e2227;
                color: #e3e3e3;
                border: 1px solid #3e4451;
                border-radius: 4px;
                padding: 4px;
            }}
            QTreeWidget::item {{
                padding: 4px;
                border-radius: 3px;
            }}
            QTreeWidget::item:hover {{
                background-color: #2c313a;
            }}
            QTreeWidget::item:selected {{
                background-color: #3e4451;
                color: #ffffff;
            }}
            QTreeWidget::indicator {{
                width: 18px;
                height: 18px;
            }}
            QTreeWidget::indicator:checked {{
                image: url('{icon_checked_path}');
            }}
            QTreeWidget::indicator:unchecked {{
                image: url('{icon_unchecked_path}');
            }}
        """)
        layout.addWidget(self.tree_widget, 1)

        # 快速選取按鈕列
        select_btn_layout = QHBoxLayout()
        select_btn_layout.setSpacing(8)

        self.btn_select_all = QPushButton("☑ 全選")
        self.btn_select_all.setFont(FontManager.get_font(size=9))
        self.btn_select_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_all.clicked.connect(self.select_all_items)
        select_btn_layout.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("☐ 全不選")
        self.btn_deselect_all.setFont(FontManager.get_font(size=9))
        self.btn_deselect_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_deselect_all.clicked.connect(self.deselect_all_items)
        select_btn_layout.addWidget(self.btn_deselect_all)

        select_btn_layout.addStretch()
        layout.addLayout(select_btn_layout)

        # 分隔線
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("color: #3e4451;")
        layout.addWidget(line)

        # 匯出格式選擇列
        format_layout = QHBoxLayout()
        format_layout.setSpacing(10)
        lbl_format = QLabel("匯出格式：")
        lbl_format.setFont(FontManager.get_font(size=10, weight=QFont.Weight.Bold))
        format_layout.addWidget(lbl_format)

        self.combo_format = QComboBox()
        self.combo_format.setFont(FontManager.get_font(size=10))
        self.combo_format.addItems([
            "Word 文件 (*.docx)",
            "純文字檔案 (*.txt)",
            "Markdown 檔案 (*.md)",
            "ePub 電子書 (*.epub)"
        ])
        format_layout.addWidget(self.combo_format, 1)
        layout.addLayout(format_layout)

        # 匯出選項
        self.chk_include_title = QCheckBox("包含文件名稱作為章節標題")
        self.chk_include_title.setFont(FontManager.get_font(size=9))
        self.chk_include_title.setChecked(True)
        layout.addWidget(self.chk_include_title)

        # 匯出模式（合併 or 獨立檔案）
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(15)
        self.radio_merge = QRadioButton("合併為單一檔案")
        self.radio_merge.setFont(FontManager.get_font(size=9))
        self.radio_merge.setChecked(True)
        self.radio_separate = QRadioButton("按章節分割為多個檔案")
        self.radio_separate.setFont(FontManager.get_font(size=9))

        self.export_mode_group = QButtonGroup(self)
        self.export_mode_group.addButton(self.radio_merge)
        self.export_mode_group.addButton(self.radio_separate)

        mode_layout.addWidget(self.radio_merge)
        mode_layout.addWidget(self.radio_separate)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        # 複製樹狀結構
        self.item_map = {}
        if parent and hasattr(parent, 'tree_widget'):
            for i in range(parent.tree_widget.topLevelItemCount()):
                src_item = parent.tree_widget.topLevelItem(i)
                self.tree_widget.addTopLevelItem(self.copy_tree_item(src_item))

        # 預設勾選目前活動中/選取的文件（若無則全選）
        if checked_item:
            checked_data = checked_item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(checked_data, dict):
                checked_id = checked_data.get("id")
                if checked_id and checked_id in self.item_map:
                    dest_item = self.item_map[checked_id]
                    dest_item.setCheckState(0, Qt.CheckState.Checked)
                    self.check_children(dest_item, Qt.CheckState.Checked)
                else:
                    self.select_all_items()
            else:
                self.select_all_items()
        else:
            self.select_all_items()

        self.tree_widget.itemChanged.connect(self.on_item_changed)

        # 底部按鈕
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_export = QPushButton("選擇儲存位置並匯出...")
        self.btn_export.setFont(FontManager.get_font(size=10, weight=QFont.Weight.Bold))
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.setStyleSheet("""
            QPushButton {
                background-color: #2b78e4;
                color: #ffffff;
                padding: 6px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3b88f4;
            }
        """)
        self.btn_export.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_export)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setFont(FontManager.get_font(size=10))
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)

    def _ensure_checkbox_icons(self):
        """確保核取方塊圖示存在且清晰。"""
        os.makedirs("resources/icons", exist_ok=True)
        checked_file = "resources/icons/checkbox_checked.png"
        unchecked_file = "resources/icons/checkbox_unchecked.png"

        if not os.path.exists(checked_file):
            p = QPixmap(20, 20)
            p.fill(Qt.GlobalColor.transparent)
            pt = QPainter(p)
            pt.setRenderHint(QPainter.RenderHint.Antialiasing)
            pt.setBrush(QColor("#2b78e4"))
            pt.setPen(QPen(QColor("#5c9bf5"), 1.5))
            pt.drawRoundedRect(1, 1, 18, 18, 4, 4)
            pt.setPen(QPen(QColor("#ffffff"), 2.5))
            pt.drawLine(5, 10, 8, 14)
            pt.drawLine(8, 14, 15, 6)
            pt.end()
            p.save(checked_file)

        if not os.path.exists(unchecked_file):
            p2 = QPixmap(20, 20)
            p2.fill(Qt.GlobalColor.transparent)
            pt2 = QPainter(p2)
            pt2.setRenderHint(QPainter.RenderHint.Antialiasing)
            pt2.setBrush(QColor("#22262b"))
            pt2.setPen(QPen(QColor("#6c757d"), 1.5))
            pt2.drawRoundedRect(1, 1, 18, 18, 4, 4)
            pt2.end()
            p2.save(unchecked_file)

    def copy_tree_item(self, src_item):
        dest_item = QTreeWidgetItem([src_item.text(0)])
        dest_item.setData(0, Qt.ItemDataRole.UserRole, src_item.data(0, Qt.ItemDataRole.UserRole))
        dest_item.setIcon(0, src_item.icon(0))
        dest_item.setCheckState(0, Qt.CheckState.Unchecked)
        dest_item.setExpanded(src_item.isExpanded())

        node_data = src_item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(node_data, dict):
            item_id = node_data.get("id")
            if item_id:
                self.item_map[item_id] = dest_item

        for i in range(src_item.childCount()):
            dest_item.addChild(self.copy_tree_item(src_item.child(i)))
        return dest_item

    def on_item_changed(self, item, column):
        if column != 0:
            return
        state = item.checkState(0)
        self.tree_widget.blockSignals(True)
        self.check_children(item, state)
        self.tree_widget.blockSignals(False)

    def check_children(self, parent_item, state):
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            child.setCheckState(0, state)
            self.check_children(child, state)

    def select_all_items(self):
        self.tree_widget.blockSignals(True)
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            item.setCheckState(0, Qt.CheckState.Checked)
            self.check_children(item, Qt.CheckState.Checked)
        self.tree_widget.blockSignals(False)

    def deselect_all_items(self):
        self.tree_widget.blockSignals(True)
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            item.setCheckState(0, Qt.CheckState.Unchecked)
            self.check_children(item, Qt.CheckState.Unchecked)
        self.tree_widget.blockSignals(False)

    def get_checked_files(self):
        checked_files = []

        def traverse(item):
            node_data = item.data(0, Qt.ItemDataRole.UserRole)
            if node_data and node_data.get("type") in ("file", "scene"):
                if item.checkState(0) == Qt.CheckState.Checked:
                    checked_files.append(item)
            for i in range(item.childCount()):
                traverse(item.child(i))

        for i in range(self.tree_widget.topLevelItemCount()):
            traverse(self.tree_widget.topLevelItem(i))

        return checked_files

    def get_export_format(self) -> str:
        """返回匯出副檔名：docx, txt, md, epub。"""
        idx = self.combo_format.currentIndex()
        mapping = {0: "docx", 1: "txt", 2: "md", 3: "epub"}
        return mapping.get(idx, "docx")

    def is_include_title(self) -> bool:
        return self.chk_include_title.isChecked()

    def is_merge_mode(self) -> bool:
        return self.radio_merge.isChecked()
