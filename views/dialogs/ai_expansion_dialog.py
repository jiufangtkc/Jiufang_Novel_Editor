from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton, QSpinBox, QMessageBox
)
from PyQt6.QtCore import Qt
from utils.font_manager import FontManager


class AIExpansionDialog(QDialog):
    """
    提供給使用者填寫擴寫參數的對話框（前文、後文、擴寫指引、預期字數）。
    輸入完畢後，點擊「開始擴寫」將觸發後續的浮動串流生成。
    """
    def __init__(self, parent=None, initial_preceding="", initial_succeeding=""):
        super().__init__(parent)
        self.setWindowTitle("✨ AI 智慧擴寫")
        self.resize(600, 500)
        self.setModal(True)
        if parent:
            self.setStyleSheet(parent.styleSheet())

        self.initial_preceding = initial_preceding
        self.initial_succeeding = initial_succeeding

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 前文
        lbl_preceding = QLabel("前文 (選填，供 AI 參考上文)：")
        lbl_preceding.setFont(FontManager.get_font(size=9, weight=FontManager.QFont.Weight.Bold))
        self.edit_preceding = QTextEdit()
        self.edit_preceding.setPlaceholderText("請貼上擴寫點之前的文字...")
        self.edit_preceding.setPlainText(self.initial_preceding)
        layout.addWidget(lbl_preceding)
        layout.addWidget(self.edit_preceding)

        # 後文
        lbl_succeeding = QLabel("後文 (選填，供 AI 參考下文，協助銜接)：")
        lbl_succeeding.setFont(FontManager.get_font(size=9, weight=FontManager.QFont.Weight.Bold))
        self.edit_succeeding = QTextEdit()
        self.edit_succeeding.setPlaceholderText("請貼上擴寫點之後的文字...")
        self.edit_succeeding.setPlainText(self.initial_succeeding)
        layout.addWidget(lbl_succeeding)
        layout.addWidget(self.edit_succeeding)

        # 擴寫指引
        lbl_guideline = QLabel("擴寫指引 (選填，告知 AI 您希望這段劇情如何發展)：")
        lbl_guideline.setFont(FontManager.get_font(size=9, weight=FontManager.QFont.Weight.Bold))
        self.edit_guideline = QTextEdit()
        self.edit_guideline.setMaximumHeight(80)
        self.edit_guideline.setPlaceholderText("例如：主角在這裡發現了一個隱藏的暗門...")
        layout.addWidget(lbl_guideline)
        layout.addWidget(self.edit_guideline)

        # 預期字數與按鈕
        bottom_layout = QHBoxLayout()
        
        lbl_words = QLabel("預期擴寫字數：")
        self.spin_words = QSpinBox()
        self.spin_words.setRange(50, 3000)
        self.spin_words.setSingleStep(50)
        self.spin_words.setValue(500)
        self.spin_words.setSuffix(" 字")
        
        bottom_layout.addWidget(lbl_words)
        bottom_layout.addWidget(self.spin_words)
        bottom_layout.addStretch(1)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_start = QPushButton("🚀 開始擴寫")
        self.btn_start.setObjectName("primary_button")
        self.btn_start.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        self.btn_start.clicked.connect(self.accept)
        
        bottom_layout.addWidget(self.btn_cancel)
        bottom_layout.addWidget(self.btn_start)

        layout.addLayout(bottom_layout)

    def get_expansion_data(self):
        """回傳使用者填寫的參數"""
        return {
            "preceding": self.edit_preceding.toPlainText().strip(),
            "succeeding": self.edit_succeeding.toPlainText().strip(),
            "guideline": self.edit_guideline.toPlainText().strip(),
            "word_count": self.spin_words.value()
        }
