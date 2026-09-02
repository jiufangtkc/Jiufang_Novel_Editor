from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QFrame, QFormLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from utils.font_manager import FontManager
from utils.theme_manager import ThemeManager


class AutosaveSettingsDialog(QDialog):
    """暫存與自動存檔設定對話框。
    
    提供作者自訂暫存檔儲存間隔（分鐘）與暫存檔數量上限。
    """

    def __init__(self, parent=None, interval_minutes: int = 10, max_files: int = 100):
        super().__init__(parent)
        self.setWindowTitle("暫存與自動存檔設定")
        self.resize(420, 260)
        self.setModal(True)
        ThemeManager.apply_theme_to_dialog(self, parent)

        self.interval_minutes = interval_minutes
        self.max_files = max_files

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 頂部標題與說明
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)
        lbl_title = QLabel("💾 暫存檔與自動備份設定")
        lbl_title.setFont(FontManager.get_font(size=11, weight=QFont.Weight.Bold))
        header_layout.addWidget(lbl_title)

        lbl_desc = QLabel("設定系統自動儲存暫存檔的頻率與硬碟保留的歷史檔案數量。")
        lbl_desc.setStyleSheet("color: #888888; font-size: 11px;")
        lbl_desc.setWordWrap(True)
        header_layout.addWidget(lbl_desc)
        layout.addLayout(header_layout)

        # 取得當前主題色彩
        theme_name = "default"
        if self.parent() and hasattr(self.parent(), "current_theme"):
            theme_name = self.parent().current_theme
        theme_colors = ThemeManager.get_theme_colors(theme_name)
        accent = theme_colors.get("accent", "#2b78e4")
        subtext = theme_colors.get("subtext_color", "#a0aec0")
        card_bg = theme_colors.get("tree_bg", "#252930")
        card_border = theme_colors.get("tree_border", "#3c424a")
        fg = theme_colors.get("main_fg", "#e0e0e0")

        lbl_desc.setStyleSheet(f"color: {subtext}; font-size: 11px;")

        # 表單區
        form_frame = QFrame()
        form_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 6px;
                padding: 10px;
            }}
            QLabel {{
                font-size: 12px;
                color: {fg};
            }}
            QSpinBox {{
                background-color: {theme_colors.get('input_bg', '#3c3f41')};
                color: {theme_colors.get('input_fg', '#ffffff')};
                border: 1px solid {theme_colors.get('input_border', '#555555')};
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 100px;
            }}
            QSpinBox:focus {{
                border: 1px solid {accent};
            }}
        """)
        form_layout = QFormLayout(form_frame)
        form_layout.setSpacing(12)

        # 1. 存檔頻率
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(1, 120)
        self.spin_interval.setSingleStep(1)
        self.spin_interval.setSuffix(" 分鐘")
        self.spin_interval.setValue(max(1, min(120, self.interval_minutes)))
        form_layout.addRow("自動存檔週期：", self.spin_interval)

        # 2. 保留上限
        self.spin_max_files = QSpinBox()
        self.spin_max_files.setRange(5, 1000)
        self.spin_max_files.setSingleStep(5)
        self.spin_max_files.setSuffix(" 個")
        self.spin_max_files.setValue(max(5, min(1000, self.max_files)))
        form_layout.addRow("最多保留數量：", self.spin_max_files)

        layout.addWidget(form_frame)

        # 提示文字
        lbl_hint = QLabel("💡 提示：超過保留數量時，系統將自動從最舊的暫存檔開始清理。")
        lbl_hint.setStyleSheet(f"color: {subtext}; font-size: 11px;")
        lbl_hint.setWordWrap(True)
        layout.addWidget(lbl_hint)

        # 底部按鈕列
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme_colors.get('btn_bg', '#3c3f41')};
                color: {fg};
                border: 1px solid {theme_colors.get('btn_border', '#555555')};
                border-radius: 4px;
                padding: 6px 16px;
            }}
            QPushButton:hover {{
                background-color: {theme_colors.get('btn_hover_bg', '#4c4f51')};
            }}
        """)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_ok = QPushButton("儲存設定")
        self.btn_ok.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 6px 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
        """)
        self.btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_ok)

        layout.addLayout(btn_layout)

    def get_settings(self) -> tuple[int, int]:
        """回傳 (interval_minutes, max_files)"""
        return self.spin_interval.value(), self.spin_max_files.value()
