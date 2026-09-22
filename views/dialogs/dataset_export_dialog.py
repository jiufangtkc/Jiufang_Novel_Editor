import os
from typing import Dict, List, Any, Set, Optional
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QRadioButton, QButtonGroup,
    QFrame, QGroupBox
)
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor, QPen
from PyQt6.QtCore import Qt
from views.common.base_dialog import BaseDialog
from utils.font_manager import FontManager
from utils.theme_manager import ThemeManager
from models.models import BUILTIN_CATEGORIES, CATEGORY_DISPLAY_NAMES


ROLE_NODE_TYPE = Qt.ItemDataRole.UserRole + 1
ROLE_CATEGORY = Qt.ItemDataRole.UserRole + 2
ROLE_CARD_ID = Qt.ItemDataRole.UserRole + 3


class DatasetExportDialog(BaseDialog):
    """資料集匯出精靈對話框。
    
    提供作家選取要匯出的分類與卡片範圍，並可選擇匯出為：
    1. 九方備份檔 (*.json)
    2. Word 閱讀檔 (*.docx)
    3. Markdown 閱讀檔 (*.md)
    """

    def __init__(
        self,
        parent=None,
        cards_data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        categories_meta: Optional[Dict[str, str]] = None
    ):
        super().__init__(parent)
        self.parent_win = parent
        self.raw_cards_data = cards_data or {}
        self.categories_meta = {**CATEGORY_DISPLAY_NAMES, **(categories_meta or {})}

        self.setWindowTitle("匯出設定資料集")
        self.resize(int(520 * self.scale_factor), int(640 * self.scale_factor))
        self.setModal(True)

        self._ensure_checkbox_icons()

        sf = self.scale_factor
        layout = QVBoxLayout(self)
        layout.setContentsMargins(int(18 * sf), int(18 * sf), int(18 * sf), int(18 * sf))
        layout.setSpacing(int(12 * sf))

        # 頂部提示文字
        lbl_hint = QLabel("請勾選欲匯出的資料集分類與卡片：")
        lbl_hint.setFont(FontManager.get_font(size=int(10 * sf), weight=QFont.Weight.Bold))
        layout.addWidget(lbl_hint)

        # 樹狀選擇區塊
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        self._apply_tree_styles()
        layout.addWidget(self.tree_widget, 1)

        # 快速勾選按鈕列
        btn_select_layout = QHBoxLayout()
        btn_select_layout.setSpacing(int(8 * sf))

        self.btn_select_all = QPushButton("全選")
        self.btn_select_all.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_select_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_all.clicked.connect(self.select_all_items)
        btn_select_layout.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("全不選")
        self.btn_deselect_all.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_deselect_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_deselect_all.clicked.connect(self.deselect_all_items)
        btn_select_layout.addWidget(self.btn_deselect_all)

        btn_select_layout.addStretch()
        layout.addLayout(btn_select_layout)

        # 分隔線
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("color: #3e4451;")
        layout.addWidget(line)

        # 匯出格式選擇群組
        group_format = QGroupBox("匯出格式")
        group_format.setFont(FontManager.get_font(size=int(10 * sf), weight=QFont.Weight.Bold))
        group_layout = QVBoxLayout(group_format)
        group_layout.setSpacing(int(8 * sf))

        self.radio_docx = QRadioButton("Word 閱讀檔 (*.docx) — 排版精美之文件，適合列印與閱讀")
        self.radio_docx.setFont(FontManager.get_font(size=int(9 * sf)))
        self.radio_docx.setChecked(True)

        self.radio_md = QRadioButton("Markdown 閱讀檔 (*.md) — 階層式純文字檔，具備動態標題降級")
        self.radio_md.setFont(FontManager.get_font(size=int(9 * sf)))

        self.radio_json = QRadioButton("九方備份檔 (*.json) — 保留完整結構與欄位，供後續匯入還原")
        self.radio_json.setFont(FontManager.get_font(size=int(9 * sf)))

        self.format_group = QButtonGroup(self)
        self.format_group.addButton(self.radio_docx)
        self.format_group.addButton(self.radio_md)
        self.format_group.addButton(self.radio_json)

        group_layout.addWidget(self.radio_docx)
        group_layout.addWidget(self.radio_md)
        group_layout.addWidget(self.radio_json)
        layout.addWidget(group_format)

        # 建立樹狀卡片清單
        self._populate_tree()

        # 連接樹狀勾選訊號
        self.tree_widget.itemChanged.connect(self._on_item_changed)

        # 底部確定 / 取消按鈕
        btn_action_layout = QHBoxLayout()
        btn_action_layout.addStretch()

        self.btn_export = QPushButton("選擇儲存位置並匯出...")
        self.btn_export.setFont(FontManager.get_font(size=int(10 * sf), weight=QFont.Weight.Bold))
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
        btn_action_layout.addWidget(self.btn_export)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setFont(FontManager.get_font(size=int(10 * sf)))
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)
        btn_action_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_action_layout)

    def _apply_tree_styles(self):
        """設定 QTreeWidget 樣式與核取方塊圖示。"""
        theme_name = "default"
        if self.parent_win and hasattr(self.parent_win, "current_theme"):
            theme_name = self.parent_win.current_theme
        theme_colors = ThemeManager.get_theme_colors(theme_name)
        tree_bg = theme_colors.get("tree_bg", "#1e2227")
        tree_fg = theme_colors.get("tree_fg", "#e3e3e3")
        tree_border = theme_colors.get("tree_border", "#3e4451")
        tree_hover = theme_colors.get("tree_item_hover_bg", "#2c313a")
        tree_selected = theme_colors.get("tree_item_selected_bg", "#094771")

        icon_checked_path = os.path.abspath("resources/icons/checkbox_checked.png").replace("\\", "/")
        icon_unchecked_path = os.path.abspath("resources/icons/checkbox_unchecked.png").replace("\\", "/")

        self.tree_widget.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {tree_bg};
                color: {tree_fg};
                border: 1px solid {tree_border};
                border-radius: 4px;
                padding: 4px;
            }}
            QTreeWidget::item {{
                padding: 4px;
                border-radius: 3px;
            }}
            QTreeWidget::item:hover {{
                background-color: {tree_hover};
            }}
            QTreeWidget::item:selected {{
                background-color: {tree_selected};
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

    def _ensure_checkbox_icons(self):
        """確保核取方塊圖示存在。"""
        os.makedirs("resources/icons", exist_ok=True)
        checked_file = "resources/icons/checkbox_checked.png"
        unchecked_file = "resources/icons/checkbox_unchecked.png"

        if not os.path.exists(checked_file):
            p = QPixmap(20, 20)
            p.fill(Qt.GlobalColor.transparent)
            pt = QPainter(p)
            pt.setRenderHint(QPainter.RenderHint.Antialiasing)
            pt.setBrush(QColor("#2b78e4"))
            pt.setPen(QPen(QColor("#5c9bf5"), 1.8))
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
            pt2.setPen(QPen(QColor("#8c939d"), 2.0))
            pt2.drawRoundedRect(1, 1, 18, 18, 4, 4)
            pt2.end()
            p2.save(unchecked_file)

    def _populate_tree(self):
        """根據傳入的卡片資料建立樹狀導航項目。"""
        self.tree_widget.blockSignals(True)
        self.tree_widget.clear()

        for cat_key, cards in self.raw_cards_data.items():
            if not cards:
                continue

            display_name = self.categories_meta.get(cat_key, cat_key)
            cat_item = QTreeWidgetItem([display_name])
            cat_item.setData(0, ROLE_NODE_TYPE, "category")
            cat_item.setData(0, ROLE_CATEGORY, cat_key)
            cat_item.setCheckState(0, Qt.CheckState.Checked)

            for card in cards:
                self._add_card_tree_item(cat_item, card, cat_key)

            self.tree_widget.addTopLevelItem(cat_item)
            cat_item.setExpanded(True)

        self.tree_widget.blockSignals(False)

    def _add_card_tree_item(self, parent_item: QTreeWidgetItem, card_dict: Dict[str, Any], cat_key: str):
        """遞迴建立卡片樹狀項目。"""
        title = card_dict.get("title") or "未命名卡片"
        card_id = card_dict.get("id", "")

        card_item = QTreeWidgetItem([title])
        card_item.setData(0, ROLE_NODE_TYPE, "card")
        card_item.setData(0, ROLE_CATEGORY, cat_key)
        card_item.setData(0, ROLE_CARD_ID, card_id)
        card_item.setCheckState(0, Qt.CheckState.Checked)

        for child in card_dict.get("children", []):
            self._add_card_tree_item(card_item, child, cat_key)

        parent_item.addChild(card_item)
        card_item.setExpanded(True)

    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        """核取狀態改變事件處理（包含子項目同步連動與父項目自動勾選）。"""
        if column != 0:
            return

        state = item.checkState(0)
        self.tree_widget.blockSignals(True)
        # 1. 向下遞迴連動所有子項目
        self._check_children(item, state)

        # 2. 向上連動：若被勾選，確保父項目也為勾選狀態
        if state == Qt.CheckState.Checked:
            parent = item.parent()
            while parent is not None:
                parent.setCheckState(0, Qt.CheckState.Checked)
                parent = parent.parent()

        self.tree_widget.blockSignals(False)

    def _check_children(self, parent_item: QTreeWidgetItem, state: Qt.CheckState):
        """遞迴設定所有子項目核取狀態。"""
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            child.setCheckState(0, state)
            self._check_children(child, state)

    def select_all_items(self):
        """全選所有項目。"""
        self.tree_widget.blockSignals(True)
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            item.setCheckState(0, Qt.CheckState.Checked)
            self._check_children(item, Qt.CheckState.Checked)
        self.tree_widget.blockSignals(False)

    def deselect_all_items(self):
        """取消勾選所有項目。"""
        self.tree_widget.blockSignals(True)
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            item.setCheckState(0, Qt.CheckState.Unchecked)
            self._check_children(item, Qt.CheckState.Unchecked)
        self.tree_widget.blockSignals(False)

    def get_export_format(self) -> str:
        """取得使用者選擇的匯出格式 ('docx', 'md', 'json')。"""
        if self.radio_docx.isChecked():
            return "docx"
        elif self.radio_md.isChecked():
            return "md"
        else:
            return "json"

    def get_selected_card_ids(self) -> Set[str]:
        """取得所有被勾選之卡片 ID 集合。"""
        selected_ids = set()

        def traverse(item: QTreeWidgetItem):
            if item.data(0, ROLE_NODE_TYPE) == "card" and item.checkState(0) == Qt.CheckState.Checked:
                cid = item.data(0, ROLE_CARD_ID)
                if cid:
                    selected_ids.add(cid)
            for i in range(item.childCount()):
                traverse(item.child(i))

        for i in range(self.tree_widget.topLevelItemCount()):
            traverse(self.tree_widget.topLevelItem(i))

        return selected_ids

    def get_filtered_cards_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """根據勾選狀態，過濾並產生新的卡片資料字典。"""
        selected_ids = self.get_selected_card_ids()
        filtered_result: Dict[str, List[Dict[str, Any]]] = {}

        def _filter_card(card: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            cid = card.get("id")
            # 檢查子節點
            filtered_children = []
            for child in card.get("children", []):
                fc = _filter_card(child)
                if fc is not None:
                    filtered_children.append(fc)

            # 若卡片本身被勾選，或者其子節點有被勾選，則保留卡片節點
            if cid in selected_ids or filtered_children:
                new_card = dict(card)
                new_card["children"] = filtered_children
                return new_card
            return None

        for cat_key, cards in self.raw_cards_data.items():
            filtered_cards = []
            for card in cards:
                fc = _filter_card(card)
                if fc is not None:
                    filtered_cards.append(fc)
            if filtered_cards:
                filtered_result[cat_key] = filtered_cards

        return filtered_result
