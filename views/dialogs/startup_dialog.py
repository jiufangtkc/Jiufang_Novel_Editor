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
    2. 讀取專案存檔
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("九方小說編輯器 — 歡迎")
        self.setFixedSize(480, 320)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
        """)
        if sys.platform == "win32":
            set_window_dark_mode(int(self.winId()))
        self.selected_action = "new"  # 'new' 或 'open'

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        # 頂部歡迎標題
        header_layout = QVBoxLayout()
        header_layout.setSpacing(6)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_title = QLabel("九方小說編輯器")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setFont(FontManager.get_font(size=16, weight=QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #ffffff; letter-spacing: 2px;")
        header_layout.addWidget(lbl_title)

        lbl_subtitle = QLabel("專為長篇小說創作者打造的沉浸式寫作工具")
        lbl_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_subtitle.setStyleSheet("color: #999999; font-size: 12px;")
        header_layout.addWidget(lbl_subtitle)

        layout.addLayout(header_layout)

        # 選項卡片區
        cards_layout = QVBoxLayout()
        cards_layout.setSpacing(14)

        # 按鈕 1：開啟新的寫作專案
        self.btn_new_project = QPushButton()
        self.btn_new_project.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new_project.setFixedHeight(72)
        self.btn_new_project.setStyleSheet("""
            QPushButton {
                background-color: #2b2b2b;
                border: 1px solid #3c3f41;
                border-radius: 8px;
                text-align: left;
                padding-left: 20px;
            }
            QPushButton:hover {
                background-color: #35383a;
                border: 1px solid #2b78e4;
            }
            QPushButton:pressed {
                background-color: #232526;
            }
        """)
        new_layout = QVBoxLayout(self.btn_new_project)
        new_layout.setContentsMargins(12, 10, 12, 10)
        new_layout.setSpacing(2)
        lbl_new_title = QLabel("✍️  開啟新的寫作專案")
        lbl_new_title.setFont(FontManager.get_font(size=12, weight=QFont.Weight.Bold))
        lbl_new_title.setStyleSheet("color: #ffffff;")
        lbl_new_desc = QLabel("建立全新專案，預設包含標準卷、章、幕結構")
        lbl_new_desc.setStyleSheet("color: #888888; font-size: 11px;")
        new_layout.addWidget(lbl_new_title)
        new_layout.addWidget(lbl_new_desc)
        self.btn_new_project.clicked.connect(self._on_new_clicked)
        cards_layout.addWidget(self.btn_new_project)

        # 按鈕 2：讀取專案存檔
        self.btn_open_project = QPushButton()
        self.btn_open_project.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_project.setFixedHeight(72)
        self.btn_open_project.setStyleSheet("""
            QPushButton {
                background-color: #2b2b2b;
                border: 1px solid #3c3f41;
                border-radius: 8px;
                text-align: left;
                padding-left: 20px;
            }
            QPushButton:hover {
                background-color: #35383a;
                border: 1px solid #2b78e4;
            }
            QPushButton:pressed {
                background-color: #232526;
            }
        """)
        open_layout = QVBoxLayout(self.btn_open_project)
        open_layout.setContentsMargins(12, 10, 12, 10)
        open_layout.setSpacing(2)
        lbl_open_title = QLabel("📂  讀取專案存檔")
        lbl_open_title.setFont(FontManager.get_font(size=12, weight=QFont.Weight.Bold))
        lbl_open_title.setStyleSheet("color: #ffffff;")
        lbl_open_desc = QLabel("開啟既有的小說資料庫專案 (.db) 繼續創作")
        lbl_open_desc.setStyleSheet("color: #888888; font-size: 11px;")
        open_layout.addWidget(lbl_open_title)
        open_layout.addWidget(lbl_open_desc)
        self.btn_open_project.clicked.connect(self._on_open_clicked)
        cards_layout.addWidget(self.btn_open_project)

        layout.addLayout(cards_layout)

    def _on_new_clicked(self):
        self.selected_action = "new"
        self.accept()

    def _on_open_clicked(self):
        self.selected_action = "open"
        self.accept()
