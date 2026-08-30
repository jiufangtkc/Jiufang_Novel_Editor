from PyQt6.QtWidgets import (
    QFrame, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QTextEdit, QPushButton, QColorDialog, QMessageBox, QLabel, QSizePolicy
)
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from utils.theme_manager import THEME_COLORS
from utils.font_manager import FontManager


class CardContentTextEdit(QTextEdit):
    """卡片純文字編輯框：強制無格式貼上"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptRichText(False)

    def insertFromMimeData(self, source):
        if source.hasText():
            self.insertPlainText(source.text())
        else:
            super().insertFromMimeData(source)


class CardWidget(QFrame):
    signal_data_changed = pyqtSignal()
    signal_open_detail = pyqtSignal(object)  # 發射 self

    def __init__(self, parent_mainwindow, color_hex="#2d2d2d", parent_card=None):
        super().__init__()
        self.main_window = parent_mainwindow
        self.parent_card = parent_card
        self.color_hex = color_hex
        self.is_collapsed = True
        
        self.setObjectName("CardWidget")
        self.setFrameShape(QFrame.Shape.NoFrame)
        
        self.init_ui()
        self.apply_color(self.color_hex)
        self.set_collapsed(True)
        self.update_scale(self.main_window.scale_factor)

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(5)
        
        # 計算巢狀深度以決定按鈕文字與縮排
        self.nesting_level = 0
        p = self.parent_card
        while p:
            self.nesting_level += 1
            p = p.parent_card
            
        if self.nesting_level == 0:
            add_child_text = "+ 子卡片"
            detail_text = "🔍 檢視"
            color_text = "顏色"
            delete_text = "刪除"
            indentation = 10
        else:
            add_child_text = "+"
            detail_text = "🔍"
            color_text = "色"
            delete_text = "刪"
            # 隨深度稍微遞減縮排以節省空間，但至少保留 6 像素
            indentation = max(6, 10 - self.nesting_level)
            
        # 標題列
        self.header_widget = QWidget()
        self.header_layout = QHBoxLayout(self.header_widget)
        self.header_layout.setContentsMargins(5, 2, 5, 2)
        self.header_layout.setSpacing(5)
        
        self.arrow_lbl = QLabel("▼")
        self.arrow_lbl.setFont(FontManager.get_font(size=9, weight=QFont.Weight.Bold))
        self.arrow_lbl.setStyleSheet("color: #aaaaaa; background-color: transparent;")
        self.header_layout.addWidget(self.arrow_lbl)
        
        self.title_lbl = QLabel("新卡片")
        self.title_lbl.setFont(FontManager.get_font(size=9, weight=QFont.Weight.Bold))
        self.title_lbl.setStyleSheet("color: #e3e3e3; background-color: transparent;")
        self.header_layout.addWidget(self.title_lbl)
        
        self.header_layout.addStretch()
        
        self.btn_detail = QPushButton(detail_text)
        self.btn_detail.setFont(FontManager.get_font(size=8, weight=QFont.Weight.Bold))
        self.btn_detail.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_detail.setToolTip("以專屬視窗開啟閱讀與編輯（亦可雙擊卡片標題）")
        self.btn_detail.clicked.connect(lambda: self.signal_open_detail.emit(self))
        self.header_layout.addWidget(self.btn_detail)

        self.btn_add_child = QPushButton(add_child_text)
        self.btn_add_child.setFont(FontManager.get_font(size=8, weight=QFont.Weight.Bold))
        self.btn_add_child.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_child.setToolTip("新增子卡片")
        self.btn_add_child.clicked.connect(self.add_child_card)
        self.header_layout.addWidget(self.btn_add_child)
        
        self.btn_color = QPushButton(color_text)
        self.btn_color.setFont(FontManager.get_font(size=8, weight=QFont.Weight.Bold))
        self.btn_color.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_color.setToolTip("自訂顏色")
        self.btn_color.clicked.connect(self.choose_color)
        self.header_layout.addWidget(self.btn_color)
        
        self.btn_delete = QPushButton(delete_text)
        self.btn_delete.setFont(FontManager.get_font(size=8, weight=QFont.Weight.Bold))
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.setToolTip("刪除此卡片")
        self.btn_delete.clicked.connect(self.delete_self)
        self.header_layout.addWidget(self.btn_delete)
        
        self.main_layout.addWidget(self.header_widget)
        
        self.header_widget.mousePressEvent = self.toggle_collapse
        self.header_widget.mouseDoubleClickEvent = lambda e: self.signal_open_detail.emit(self)
        self.header_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # 內容區 (Body)
        self.body_widget = QWidget()
        self.body_layout = QVBoxLayout(self.body_widget)
        self.body_layout.setContentsMargins(5, 5, 5, 5)
        self.body_layout.setSpacing(5)
        
        name_layout = QHBoxLayout()
        self.name_lbl = QLabel("名稱:")
        self.name_lbl.setFont(FontManager.get_font(size=9))
        self.name_lbl.setStyleSheet("color: #aaaaaa; background-color: transparent;")
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("請輸入卡片名稱...")
        self.title_edit.setFont(FontManager.get_font(size=9))
        self.title_edit.textChanged.connect(self.on_title_changed)
        name_layout.addWidget(self.name_lbl)
        name_layout.addWidget(self.title_edit)
        self.body_layout.addLayout(name_layout)
        
        self.content_edit = CardContentTextEdit()
        self.content_edit.setPlaceholderText("請輸入設定或大綱內文...")
        self.content_edit.setFont(FontManager.get_font(size=9))
        self.content_edit.setFixedHeight(75)
        self.content_edit.textChanged.connect(self.on_content_changed)
        self.body_layout.addWidget(self.content_edit)
        
        self.child_container = QWidget()
        self.child_container.setVisible(False)
        self.child_layout = QVBoxLayout(self.child_container)
        self.child_layout.setContentsMargins(indentation, 0, 0, 0)
        self.child_layout.setSpacing(5)
        self.child_layout.addStretch()
        self.body_layout.addWidget(self.child_container)
        
        self.body_layout.addStretch()
        
        self.main_layout.addWidget(self.body_widget)

    def update_scale(self, scale):
        self.arrow_lbl.setFont(FontManager.get_font(size=int(9 * scale), weight=QFont.Weight.Bold))
        self.title_lbl.setFont(FontManager.get_font(size=int(9 * scale), weight=QFont.Weight.Bold))
        self.btn_detail.setFont(FontManager.get_font(size=int(8 * scale)))
        self.btn_add_child.setFont(FontManager.get_font(size=int(8 * scale)))
        self.btn_color.setFont(FontManager.get_font(size=int(8 * scale)))
        self.btn_delete.setFont(FontManager.get_font(size=int(8 * scale)))
        if hasattr(self, 'name_lbl'):
            self.name_lbl.setFont(FontManager.get_font(size=int(9 * scale)))
        self.title_edit.setFont(FontManager.get_font(size=int(9 * scale)))
        self.content_edit.setFont(FontManager.get_font(size=int(9 * scale)))
        self.content_edit.setFixedHeight(int(75 * scale))
        if self.is_collapsed:
            self.set_collapsed(True)

    def on_title_changed(self, text):
        display_text = text.strip() if text.strip() else "新卡片"
        self.title_lbl.setText(display_text)
        self.signal_data_changed.emit()

    def on_content_changed(self):
        self.signal_data_changed.emit()

    def toggle_collapse(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_collapsed(not self.is_collapsed)
            self.signal_data_changed.emit()

    def set_collapsed(self, collapse):
        self.is_collapsed = collapse
        self.body_widget.setVisible(not collapse)
        self.arrow_lbl.setText("▶" if collapse else "▼")
        if collapse:
            self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            header_h = self.header_widget.sizeHint().height()
            if header_h <= 0:
                header_h = int(24 * self.main_window.scale_factor)
            margins = self.main_layout.contentsMargins()
            self.setFixedHeight(header_h + margins.top() + margins.bottom())
        else:
            self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
            self.setMinimumHeight(0)
            self.setMaximumHeight(16777215)
        self.updateGeometry()

    def add_child_card(self):
        self.child_container.setVisible(True)
        child = CardWidget(self.main_window, color_hex="#2d2d2d", parent_card=self)
        child.signal_data_changed.connect(self.signal_data_changed.emit)
        child.signal_open_detail.connect(self.signal_open_detail.emit)
        self.child_layout.insertWidget(self.child_layout.count() - 1, child)
        self.set_collapsed(False)
        self.signal_data_changed.emit()

    def choose_color(self):
        dialog = QColorDialog(QColor(self.color_hex), self.main_window)
        dialog.setWindowTitle("選擇卡片自訂顏色")
        if dialog.exec() == QColorDialog.DialogCode.Accepted:
            selected_color = dialog.selectedColor()
            self.color_hex = selected_color.name()
            self.apply_color(self.color_hex)
            self.signal_data_changed.emit()

    def apply_color(self, color_hex):
        color = QColor(color_hex)
        r, g, b = color.red(), color.green(), color.blue()
        
        # 取得當前主題顏色
        theme_name = getattr(self.main_window, "current_theme", "default")
        theme_colors = THEME_COLORS.get(theme_name, THEME_COLORS["default"])
        main_bg_hex = theme_colors.get("main_bg", "#1e1e1e")
        main_fg_hex = theme_colors.get("main_fg", "#e3e3e3")
        
        # 計算亮度以判斷主題是暗色還是亮色，從而適應微調
        bg_qcolor = QColor(main_bg_hex)
        theme_is_light = (0.299 * bg_qcolor.red() + 0.587 * bg_qcolor.green() + 0.114 * bg_qcolor.blue()) > 140
        
        is_default = (color_hex.lower() == "#2d2d2d")
        if is_default:
            # 預設狀態：微透光深色卡片背景，1px 柔和白邊框
            bg_style = "background-color: #25282d;"
            border_style = "border: 1px solid rgba(255, 255, 255, 0.16);"
            arrow_color = "#79c0ff"
            text_color = "#f0f2f5"
        else:
            # 自訂顏色：1px 明亮自訂色邊框 + 22% 不透明度自訂色背景
            bg_style = f"background-color: rgba({r}, {g}, {b}, 0.22);"
            border_style = f"border: 1px solid rgba({r}, {g}, {b}, 0.65);"
            arrow_color = f"rgb({r}, {g}, {b})"
            text_color = "#ffffff"
            
        # 設定卡片樣式表
        self.setStyleSheet(f"""
            QFrame#CardWidget {{
                {bg_style}
                {border_style}
                border-radius: 8px;
            }}
            QFrame#CardWidget QWidget {{
                background-color: transparent;
            }}
        """)
        
        self.title_lbl.setStyleSheet(f"color: {text_color}; background-color: transparent;")
        self.arrow_lbl.setStyleSheet(f"color: {arrow_color}; background-color: transparent;")
        if hasattr(self, 'name_lbl'):
            self.name_lbl.setStyleSheet("color: #c5d0e0; background-color: transparent;")
        
        # 輸入框樣式：高對比且帶微邊框
        input_style = f"""
            QLineEdit, QTextEdit {{
                background-color: rgba(0, 0, 0, 0.25);
                color: #f0f2f5;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 4px;
                padding: 4px;
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border: 1px solid #58a6ff;
                background-color: rgba(0, 0, 0, 0.35);
            }}
        """
        self.title_edit.setStyleSheet(input_style)
        self.content_edit.setStyleSheet(input_style)
        
        # 按鈕群色彩獨立分明，高對比、質感膠囊按鈕
        def _get_action_btn_style(r: int, g: int, b: int, text_color: str, hover_border: str) -> str:
            return f"""
                QPushButton {{
                    background-color: rgba({r}, {g}, {b}, 0.12);
                    border: 1px solid rgba({r}, {g}, {b}, 0.35);
                    border-radius: 4px;
                    padding: 2px 6px;
                    color: {text_color};
                }}
                QPushButton:hover {{
                    background-color: rgba({r}, {g}, {b}, 0.30);
                    border: 1px solid {hover_border};
                    color: #ffffff;
                }}
                QPushButton:pressed {{
                    background-color: rgba({r}, {g}, {b}, 0.45);
                }}
            """

        self.btn_detail.setStyleSheet(_get_action_btn_style(88, 166, 255, "#79c0ff", "#58a6ff"))
        self.btn_add_child.setStyleSheet(_get_action_btn_style(126, 231, 135, "#7ee787", "#56d364"))
        self.btn_color.setStyleSheet(_get_action_btn_style(210, 168, 255, "#d2a8ff", "#bc8cff"))
        self.btn_delete.setStyleSheet(_get_action_btn_style(255, 123, 114, "#ff7b72", "#ff7b72"))

    def delete_self(self):
        reply = QMessageBox.question(
            self.main_window, "確認刪除", "確定要刪除此卡片及其底下的所有子卡片嗎？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            parent_card = self.parent_card
            self.setParent(None)
            self.deleteLater()
            
            # 若父卡片已無其他子卡片，隱藏父卡片的子卡片容器
            if parent_card and isinstance(parent_card, CardWidget):
                has_remaining_children = False
                for i in range(parent_card.child_layout.count()):
                    item = parent_card.child_layout.itemAt(i)
                    if item and item.widget() and isinstance(item.widget(), CardWidget):
                        has_remaining_children = True
                        break
                if not has_remaining_children:
                    parent_card.child_container.setVisible(False)
                    
            self.signal_data_changed.emit()
