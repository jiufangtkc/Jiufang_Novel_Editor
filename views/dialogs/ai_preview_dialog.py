from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
    QLineEdit, QTextEdit, QPushButton, QLabel, QApplication,
    QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from utils.font_manager import FontManager


class AIPreviewDialog(QDialog):
    def __init__(self, parent=None, result_data=None):
        super().__init__(parent)
        self.setWindowTitle("AI 分析結果審核與卡片建立")
        self.scale_factor = getattr(parent, "scale_factor", 1.0) if parent else 1.0
        self.resize(int(650 * self.scale_factor), int(600 * self.scale_factor))
        self.setModal(True)
        if parent:
            self.setStyleSheet(parent.styleSheet())

        self.result_data = result_data or {}
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        sf = self.scale_factor
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(int(15 * sf), int(15 * sf), int(15 * sf), int(15 * sf))
        main_layout.setSpacing(int(10 * sf))

        # 頂部提示
        lbl_hint = QLabel("審核與編輯 AI 分析結果，確認無誤後可一鍵加入右側資料集：")
        lbl_hint.setFont(FontManager.get_font(size=int(9 * sf), weight=QFont.Weight.Bold))
        main_layout.addWidget(lbl_hint)

        form_layout = QFormLayout()
        form_layout.setSpacing(int(8 * sf))

        # 標題
        self.input_title = QLineEdit()
        self.input_title.setFont(FontManager.get_font(size=int(9 * sf)))
        lbl_card_title = QLabel("卡片標題:")
        lbl_card_title.setFont(FontManager.get_font(size=int(9 * sf)))
        form_layout.addRow(lbl_card_title, self.input_title)

        # 分類選擇
        self.combo_category = QComboBox()
        self.combo_category.setFont(FontManager.get_font(size=int(9 * sf)))
        self.combo_category.addItem("本書綱要", "summary")
        self.combo_category.addItem("角色設定", "character")
        self.combo_category.addItem("世界觀", "world")
        self.combo_category.addItem("時間軸", "timeline")
        lbl_card_cat = QLabel("卡片分類:")
        lbl_card_cat.setFont(FontManager.get_font(size=int(9 * sf)))
        form_layout.addRow(lbl_card_cat, self.combo_category)

        # 標籤
        self.input_tags = QLineEdit()
        self.input_tags.setFont(FontManager.get_font(size=int(9 * sf)))
        self.input_tags.setPlaceholderText("請以逗號或空格分隔標籤")
        lbl_card_tags = QLabel("卡片標籤:")
        lbl_card_tags.setFont(FontManager.get_font(size=int(9 * sf)))
        form_layout.addRow(lbl_card_tags, self.input_tags)

        # 一句話簡述
        self.input_summary = QLineEdit()
        self.input_summary.setFont(FontManager.get_font(size=int(9 * sf)))
        lbl_card_sum = QLabel("卡片簡述:")
        lbl_card_sum.setFont(FontManager.get_font(size=int(9 * sf)))
        form_layout.addRow(lbl_card_sum, self.input_summary)

        main_layout.addLayout(form_layout)

        # 內文編輯區
        lbl_content = QLabel("詳細分析內容:")
        lbl_content.setFont(FontManager.get_font(size=int(9 * sf)))
        main_layout.addWidget(lbl_content)

        self.text_content = QTextEdit()
        self.text_content.setFont(FontManager.get_font(size=int(10 * sf)))
        main_layout.addWidget(self.text_content, 1)

        # 底部按鈕列
        btn_layout = QHBoxLayout()

        self.btn_copy = QPushButton("📋 複製內容")
        self.btn_copy.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_copy.clicked.connect(self._copy_to_clipboard)
        btn_layout.addWidget(self.btn_copy)

        btn_layout.addStretch()

        self.btn_create_card = QPushButton("✨ 建立為資料卡片")
        self.btn_create_card.setStyleSheet("""
            QPushButton {
                background-color: #0e639c;
                color: #ffffff;
                font-weight: bold;
                padding: 6px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
        """)
        self.btn_create_card.setFont(FontManager.get_font(size=int(9 * sf), weight=QFont.Weight.Bold))
        self.btn_create_card.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_create_card)

        self.btn_cancel = QPushButton("關閉")
        self.btn_cancel.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        main_layout.addLayout(btn_layout)

    def _load_data(self):
        title = self.result_data.get("title", "")
        self.input_title.setText(title)

        category = self.result_data.get("category", "summary")
        idx = self.combo_category.findData(category)
        if idx >= 0:
            self.combo_category.setCurrentIndex(idx)

        tags = self.result_data.get("tags", [])
        if isinstance(tags, list):
            self.input_tags.setText(", ".join(tags))
        else:
            self.input_tags.setText(str(tags))

        self.input_summary.setText(self.result_data.get("summary", ""))
        self.text_content.setPlainText(self.result_data.get("content", ""))

    def _copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.text_content.toPlainText())
        QMessageBox.information(self, "提示", "已將分析內容複製至剪貼簿！")

    def get_card_data(self) -> dict:
        """取得使用者審核修改後的卡片資料"""
        raw_tags = self.input_tags.text().replace("，", ",").split(",")
        tags = [t.strip() for t in raw_tags if t.strip()]

        return {
            "title": self.input_title.text().strip() or "未命名卡片",
            "category": self.combo_category.currentData(),
            "tags": tags,
            "summary": self.input_summary.text().strip(),
            "content": self.text_content.toPlainText().strip()
        }
