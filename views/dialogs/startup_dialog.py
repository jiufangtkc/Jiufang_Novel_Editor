from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from utils.font_manager import FontManager
from utils.theme_manager import set_window_dark_mode
import sys


class StartupDialog(QDialog):
    """程式啟動引導對話框。
    
    提供作者在軟體啟動時選擇：
    1. 開啟新的寫作專案
    2. 讀取上次寫的專案（自動尋找最新存檔）
    3. 讀取專案存檔（預設開啟 story 目錄）
    4. 讀取暫存檔（預設開啟 Temp_doc 目錄）
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("九方小說編輯器 — 歡迎")
        scale = 1.0
        if parent and hasattr(parent, "scale_factor"):
            scale = parent.scale_factor
        else:
            try:
                from services.app_settings_service import AppSettingsService
                scale = AppSettingsService.get_ui_scale()
            except Exception:
                scale = 1.0
        self.scale_factor = scale
        self.setFixedSize(int(500 * scale), int(470 * scale))
        self.setModal(True)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
        """)
        if sys.platform == "win32":
            set_window_dark_mode(int(self.winId()))
        self.selected_action = "new"  # 'new', 'open_latest', 'open', 'open_temp'

        self.init_ui()

    def _create_card_button(self, icon_title: str, description: str) -> QPushButton:
        """輔助建立一致風格的選項卡片按鈕。"""
        sf = self.scale_factor
        btn = QPushButton()
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(int(68 * sf))
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #2b2b2b;
                border: 1px solid #3c3f41;
                border-radius: {int(8 * sf)}px;
                text-align: left;
                padding-left: {int(18 * sf)}px;
            }}
            QPushButton:hover {{
                background-color: #35383a;
                border: 1px solid #2b78e4;
            }}
            QPushButton:pressed {{
                background-color: #232526;
            }}
        """)
        card_layout = QVBoxLayout(btn)
        card_layout.setContentsMargins(int(12 * sf), int(8 * sf), int(12 * sf), int(8 * sf))
        card_layout.setSpacing(int(2 * sf))

        lbl_title = QLabel(icon_title)
        lbl_title.setFont(FontManager.get_font(size=int(12 * sf), weight=QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #ffffff;")
        
        lbl_desc = QLabel(description)
        lbl_desc.setFont(FontManager.get_font(size=int(9 * sf)))
        lbl_desc.setStyleSheet("color: #a0aec0;")

        card_layout.addWidget(lbl_title)
        card_layout.addWidget(lbl_desc)
        return btn

    def init_ui(self):
        sf = self.scale_factor
        layout = QVBoxLayout(self)
        layout.setContentsMargins(int(24 * sf), int(22 * sf), int(24 * sf), int(22 * sf))
        layout.setSpacing(int(14 * sf))

        # 頂部歡迎標題
        header_layout = QVBoxLayout()
        header_layout.setSpacing(int(4 * sf))
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_title = QLabel("九方小說編輯器")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setFont(FontManager.get_font(size=int(16 * sf), weight=QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #ffffff; letter-spacing: 2px;")
        header_layout.addWidget(lbl_title)

        lbl_subtitle = QLabel("專為長篇小說創作者打造的沉浸式寫作工具")
        lbl_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_subtitle.setFont(FontManager.get_font(size=int(10 * sf)))
        lbl_subtitle.setStyleSheet("color: #999999;")
        header_layout.addWidget(lbl_subtitle)

        layout.addLayout(header_layout)

        # 選項卡片區
        cards_layout = QVBoxLayout()
        cards_layout.setSpacing(10)

        # 按鈕 1：開啟新的寫作專案
        self.btn_new_project = self._create_card_button(
            "✍️  開啟新的寫作專案",
            "建立全新專案，預設包含標準卷、章、幕結構"
        )
        self.btn_new_project.clicked.connect(self._on_new_clicked)
        cards_layout.addWidget(self.btn_new_project)

        # 按鈕 2：讀取上次寫的專案
        self.btn_open_latest = self._create_card_button(
            "📖  讀取上次寫的專案",
            "自動搜尋 story 目錄中最新存檔的專案並開啟"
        )
        self.btn_open_latest.clicked.connect(self._on_open_latest_clicked)
        cards_layout.addWidget(self.btn_open_latest)

        # 按鈕 3：讀取專案存檔
        self.btn_open_project = self._create_card_button(
            "📂  讀取專案存檔",
            "從 story 目錄選擇既有專案存檔 (.db) 繼續創作"
        )
        self.btn_open_project.clicked.connect(self._on_open_clicked)
        cards_layout.addWidget(self.btn_open_project)

        # 按鈕 4：讀取暫存檔
        self.btn_open_temp = self._create_card_button(
            "💾  讀取暫存檔",
            "從 Temp_doc 目錄選擇歷史自動暫存檔 (.db)"
        )
        self.btn_open_temp.clicked.connect(self._on_open_temp_clicked)
        cards_layout.addWidget(self.btn_open_temp)

        layout.addLayout(cards_layout)

    def _on_new_clicked(self):
        self.selected_action = "new"
        self.accept()

    def _on_open_latest_clicked(self):
        self.selected_action = "open_latest"
        self.accept()

    def _on_open_clicked(self):
        self.selected_action = "open"
        self.accept()

    def _on_open_temp_clicked(self):
        self.selected_action = "open_temp"
        self.accept()
