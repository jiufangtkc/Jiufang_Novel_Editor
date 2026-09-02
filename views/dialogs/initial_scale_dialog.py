import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QButtonGroup, QRadioButton
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from utils.font_manager import FontManager
from utils.theme_manager import set_window_dark_mode


class InitialScaleDialog(QDialog):
    """初次乾淨開啟軟體時，詢問使用者偏好介面大小的對話框。"""

    SCALE_OPTIONS = [
        ("100% (標準預設)", 1.0, "適合標準 1080p 螢幕與預設字級"),
        ("125% (舒適放大)", 1.25, "推薦 2K 螢幕或高解析度筆電螢幕"),
        ("150% (清晰放大)", 1.5, "視覺更大、字體更清晰，適合護眼閱讀"),
        ("180% (較大尺寸)", 1.8, "適合 4K 螢幕或需要大字體顯示"),
        ("200% (超大尺寸)", 2.0, "雙倍放大顯示"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("九方小說編輯器 — 介面大小設定")
        self.setFixedSize(480, 490)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
        """)
        if sys.platform == "win32":
            set_window_dark_mode(int(self.winId()))

        self.selected_scale = 1.0
        self._radio_buttons = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(14)

        # 頂部說明區域
        header_layout = QVBoxLayout()
        header_layout.setSpacing(6)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_title = QLabel("歡迎使用九方小說編輯器")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setFont(FontManager.get_font(size=15, weight=QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #ffffff; letter-spacing: 1px;")
        header_layout.addWidget(lbl_title)

        lbl_subtitle = QLabel("請選擇您偏好的介面顯示大小：")
        lbl_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_subtitle.setFont(FontManager.get_font(size=11))
        lbl_subtitle.setStyleSheet("color: #bbbbbb;")
        header_layout.addWidget(lbl_subtitle)

        layout.addLayout(header_layout)

        # 選項群組區
        options_container = QVBoxLayout()
        options_container.setSpacing(8)

        self.button_group = QButtonGroup(self)

        for idx, (title, scale_val, desc) in enumerate(self.SCALE_OPTIONS):
            btn = QFrame()
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            btn_layout = QHBoxLayout(btn)
            btn_layout.setContentsMargins(14, 8, 14, 8)
            btn_layout.setSpacing(10)

            radio = QRadioButton()
            radio.setChecked(scale_val == 1.0)
            radio.setStyleSheet("""
                QRadioButton {
                    background: transparent;
                }
                QRadioButton::indicator {
                    width: 16px;
                    height: 16px;
                    border-radius: 9px;
                    border: 2px solid #8c939d;
                    background-color: #202428;
                }
                QRadioButton::indicator:hover {
                    border-color: #58a6ff;
                }
                QRadioButton::indicator:checked {
                    border: 2px solid #58a6ff;
                    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0 #58a6ff, stop:0.48 #58a6ff, stop:0.52 #202428, stop:1 #202428);
                }
            """)
            self.button_group.addButton(radio, idx)
            self._radio_buttons.append((radio, scale_val))

            text_layout = QVBoxLayout()
            text_layout.setSpacing(2)
            lbl_opt_title = QLabel(title)
            lbl_opt_title.setFont(FontManager.get_font(size=11, weight=QFont.Weight.Bold))
            lbl_opt_title.setStyleSheet("color: #f0f3f6; background: transparent; border: none;")

            lbl_opt_desc = QLabel(desc)
            lbl_opt_desc.setFont(FontManager.get_font(size=9))
            lbl_opt_desc.setStyleSheet("color: #a0aec0; background: transparent; border: none;")

            text_layout.addWidget(lbl_opt_title)
            text_layout.addWidget(lbl_opt_desc)

            btn_layout.addWidget(radio)
            btn_layout.addLayout(text_layout)
            btn_layout.addStretch()

            def make_style_updater(frame, r):
                def update_style(checked):
                    if checked:
                        frame.setStyleSheet("""
                            QFrame {
                                background-color: #222b35;
                                border: 1.5px solid #58a6ff;
                                border-radius: 6px;
                            }
                        """)
                    else:
                        frame.setStyleSheet("""
                            QFrame {
                                background-color: #26292e;
                                border: 1px solid #3c424a;
                                border-radius: 6px;
                            }
                            QFrame:hover {
                                background-color: #2e333b;
                                border: 1px solid #58a6ff;
                            }
                        """)
                return update_style

            style_updater = make_style_updater(btn, radio)
            radio.toggled.connect(style_updater)
            style_updater(radio.isChecked())

            # 點擊整塊卡片時切換選取
            def make_click_handler(r=radio):
                return lambda event: r.setChecked(True)
            btn.mousePressEvent = make_click_handler()

            options_container.addWidget(btn)

        layout.addLayout(options_container)

        # 底部提示文字
        lbl_hint = QLabel("💡 往後啟動均會維持此比例，亦可隨時於「設定 ➔ 介面大小調整」中變更。")
        lbl_hint.setWordWrap(True)
        lbl_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_hint.setFont(FontManager.get_font(size=9))
        lbl_hint.setStyleSheet("color: #9aa5b5; margin-top: 2px;")
        layout.addWidget(lbl_hint)

        # 確認按鈕
        btn_confirm = QPushButton("確認並開始使用")
        btn_confirm.setFixedHeight(36)
        btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_confirm.setFont(FontManager.get_font(size=11, weight=QFont.Weight.Bold))
        btn_confirm.setStyleSheet("""
            QPushButton {
                background-color: #2b78e4;
                color: #ffffff;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #3b88f4;
            }
            QPushButton:pressed {
                background-color: #1e60c0;
            }
        """)
        btn_confirm.clicked.connect(self._on_confirm)
        layout.addWidget(btn_confirm)

    def _on_confirm(self):
        for radio, scale_val in self._radio_buttons:
            if radio.isChecked():
                self.selected_scale = scale_val
                break
        self.accept()
