from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from utils.font_manager import FontManager


class WordCountSettingsDialog(QDialog):
    """字數統計規則設定對話框。
    
    提供作者自訂字數統計規則：
    1. 是否計算半形英數字、半形標點符號與半形空格。
    2. 是否計算全形空格 (\\u3000)。
    """

    def __init__(self, parent=None, count_half_alnum_and_sym: bool = False, count_full_space: bool = False):
        super().__init__(parent)
        self.setWindowTitle("字數統計規則設定")
        self.resize(460, 320)
        self.setModal(True)

        self.count_half_alnum_and_sym = count_half_alnum_and_sym
        self.count_full_space = count_full_space

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(16)

        # 頂部標題與說明
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)
        lbl_title = QLabel("📊 字數統計規則設定")
        lbl_title.setFont(FontManager.get_font(size=12, weight=QFont.Weight.Bold))
        header_layout.addWidget(lbl_title)

        lbl_desc = QLabel("設定編輯器底部與專案統計字數時的計算與排除條件。")
        lbl_desc.setStyleSheet("color: #888888; font-size: 11px;")
        lbl_desc.setWordWrap(True)
        header_layout.addWidget(lbl_desc)
        layout.addLayout(header_layout)

        # 設定選項區
        options_frame = QFrame()
        options_frame.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border: 1px solid #3c3f41;
                border-radius: 6px;
                padding: 12px;
            }
            QCheckBox {
                font-size: 12px;
                color: #e0e0e0;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #555555;
                border-radius: 3px;
                background-color: #3c3f41;
            }
            QCheckBox::indicator:checked {
                background-color: #4a90e2;
                border-color: #4a90e2;
            }
        """)
        options_layout = QVBoxLayout(options_frame)
        options_layout.setSpacing(14)

        # 1. 半形英數字、符號與半形空格
        half_box = QVBoxLayout()
        half_box.setSpacing(2)
        self.chk_half = QCheckBox("計算半形英數字、符號與半形空格")
        self.chk_half.setChecked(self.count_half_alnum_and_sym)
        self.chk_half.setFont(FontManager.get_font(size=10, weight=QFont.Weight.Bold))
        half_box.addWidget(self.chk_half)

        lbl_half_note = QLabel("勾選時計入半形字母 (a-z)、數字 (0-9)、半形標點與空白鍵；取消勾選則排除。")
        lbl_half_note.setStyleSheet("color: #999999; font-size: 11px; margin-left: 26px;")
        lbl_half_note.setWordWrap(True)
        half_box.addWidget(lbl_half_note)
        options_layout.addLayout(half_box)

        # 分隔線
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #3c3f41;")
        options_layout.addWidget(line)

        # 2. 全形空格
        full_space_box = QVBoxLayout()
        full_space_box.setSpacing(2)
        self.chk_full_space = QCheckBox("計算全形空格（\\u3000）")
        self.chk_full_space.setChecked(self.count_full_space)
        self.chk_full_space.setFont(FontManager.get_font(size=10, weight=QFont.Weight.Bold))
        full_space_box.addWidget(self.chk_full_space)

        lbl_full_space_note = QLabel("勾選時段首縮排之全形空格計入字數；取消勾選則排除。")
        lbl_full_space_note.setStyleSheet("color: #999999; font-size: 11px; margin-left: 26px;")
        lbl_full_space_note.setWordWrap(True)
        full_space_box.addWidget(lbl_full_space_note)
        options_layout.addLayout(full_space_box)

        layout.addWidget(options_frame)

        # 提示文字
        lbl_hint = QLabel("💡 提示：全形中文字與全形標點符號一律計入統計。移動滑鼠至底部字數欄位可查看詳細構成。")
        lbl_hint.setStyleSheet("color: #888888; font-size: 11px;")
        lbl_hint.setWordWrap(True)
        layout.addWidget(lbl_hint)

        # 底部按鈕列
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #3c3f41;
                color: #e0e0e0;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #484b4d;
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_ok = QPushButton("儲存設定")
        self.btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
        """)
        self.btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_ok)

        layout.addLayout(btn_layout)

    def get_settings(self):
        """回傳 (count_half_alnum_and_sym, count_full_space)"""
        return self.chk_half.isChecked(), self.chk_full_space.isChecked()
