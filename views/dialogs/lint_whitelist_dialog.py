import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QLineEdit, QMessageBox, QTabWidget, QWidget,
    QFormLayout, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from utils.font_manager import FontManager
from utils.theme_manager import ThemeManager
from services.lint_service import LintService

class LintWhitelistDialog(QDialog):
    """詞彙庫與白名單管理對話框，供使用者自由新增/刪除忽略詞與自訂贅詞。"""

    signal_settings_updated = pyqtSignal()

    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.setWindowTitle("文風檢查詞彙庫與白名單管理")
        ThemeManager.apply_theme_to_dialog(self, parent)
        self.scale_factor = getattr(self, "scale_factor", 1.0)
        self.resize(int(560 * self.scale_factor), int(450 * self.scale_factor))
        self.setMinimumSize(int(520 * self.scale_factor), int(420 * self.scale_factor))
        self.settings = settings or LintService.load_settings()
        self.init_ui()

    def init_ui(self):
        sf = self.scale_factor
        layout = QVBoxLayout(self)
        layout.setContentsMargins(int(15 * sf), int(15 * sf), int(15 * sf), int(15 * sf))
        layout.setSpacing(int(12 * sf))

        title_lbl = QLabel("📚 詞彙庫與檢查參數設定")
        title_lbl.setFont(FontManager.get_font(size=int(13 * sf), weight=QFont.Weight.Bold))
        layout.addWidget(title_lbl)

        desc_lbl = QLabel("在此維護您的自訂白名單（永久忽略不提醒）與個人專屬贅詞庫。")
        desc_lbl.setFont(FontManager.get_font(size=int(9 * sf)))
        desc_lbl.setStyleSheet("color: #a0aec0;")
        layout.addWidget(desc_lbl)

        self.tabs = QTabWidget()

        # Tab 1: 忽略白名單
        self.tab_whitelist = QWidget()
        tab1_layout = QVBoxLayout(self.tab_whitelist)
        tab1_layout.setContentsMargins(int(10 * sf), int(10 * sf), int(10 * sf), int(10 * sf))
        tab1_layout.setSpacing(int(8 * sf))

        tab1_info = QLabel("以下詞彙在文風檢查時將被完全忽略（例如專有名詞、特定句式）：")
        tab1_info.setFont(FontManager.get_font(size=int(9 * sf)))
        tab1_layout.addWidget(tab1_info)

        self.list_whitelist = QListWidget()
        self.list_whitelist.setFont(FontManager.get_font(size=int(10 * sf)))
        for w in self.settings.get("whitelist", []):
            self.list_whitelist.addItem(w)
        tab1_layout.addWidget(self.list_whitelist)

        add_layout1 = QHBoxLayout()
        self.input_whitelist = QLineEdit()
        self.input_whitelist.setPlaceholderText("輸入欲加入白名單的詞彙...")
        self.input_whitelist.setFont(FontManager.get_font(size=int(9 * sf)))
        self.input_whitelist.returnPressed.connect(self.add_whitelist_word)

        btn_add_whitelist = QPushButton("新增至白名單")
        btn_add_whitelist.setFont(FontManager.get_font(size=int(9 * sf)))
        btn_add_whitelist.clicked.connect(self.add_whitelist_word)

        btn_del_whitelist = QPushButton("刪除選取")
        btn_del_whitelist.setFont(FontManager.get_font(size=int(9 * sf)))
        btn_del_whitelist.clicked.connect(self.delete_whitelist_word)

        add_layout1.addWidget(self.input_whitelist)
        add_layout1.addWidget(btn_add_whitelist)
        add_layout1.addWidget(btn_del_whitelist)
        tab1_layout.addLayout(add_layout1)

        self.tabs.addTab(self.tab_whitelist, "🛡️ 忽略白名單")

        # Tab 2: 自訂贅詞庫
        self.tab_custom = QWidget()
        tab2_layout = QVBoxLayout(self.tab_custom)
        tab2_layout.setContentsMargins(int(10 * sf), int(10 * sf), int(10 * sf), int(10 * sf))
        tab2_layout.setSpacing(int(8 * sf))

        tab2_info = QLabel("除內建贅詞外，您可在下方新增個人寫作習慣中想避免的口癖或冗詞：")
        tab2_info.setFont(FontManager.get_font(size=int(9 * sf)))
        tab2_layout.addWidget(tab2_info)

        self.list_custom = QListWidget()
        self.list_custom.setFont(FontManager.get_font(size=int(10 * sf)))
        for w in self.settings.get("custom_redundant_words", []):
            self.list_custom.addItem(w)
        tab2_layout.addWidget(self.list_custom)

        add_layout2 = QHBoxLayout()
        self.input_custom = QLineEdit()
        self.input_custom.setPlaceholderText("輸入欲加入檢查的自訂贅詞...")
        self.input_custom.setFont(FontManager.get_font(size=int(9 * sf)))
        self.input_custom.returnPressed.connect(self.add_custom_word)

        btn_add_custom = QPushButton("新增贅詞")
        btn_add_custom.setFont(FontManager.get_font(size=int(9 * sf)))
        btn_add_custom.clicked.connect(self.add_custom_word)

        btn_del_custom = QPushButton("刪除選取")
        btn_del_custom.setFont(FontManager.get_font(size=int(9 * sf)))
        btn_del_custom.clicked.connect(self.delete_custom_word)

        add_layout2.addWidget(self.input_custom)
        add_layout2.addWidget(btn_add_custom)
        add_layout2.addWidget(btn_del_custom)
        tab2_layout.addLayout(add_layout2)

        self.tabs.addTab(self.tab_custom, "⚠️ 自訂贅詞庫")

        # Tab 3: 參數設定
        self.tab_params = QWidget()
        tab3_layout = QVBoxLayout(self.tab_params)
        tab3_layout.setContentsMargins(int(15 * sf), int(15 * sf), int(15 * sf), int(15 * sf))
        tab3_layout.setSpacing(int(12 * sf))

        form = QFormLayout()
        self.spin_particle = QSpinBox()
        self.spin_particle.setFont(FontManager.get_font(size=int(9 * sf)))
        self.spin_particle.setRange(2, 10)
        self.spin_particle.setValue(self.settings.get("particle_density_threshold", 3))
        self.spin_particle.setSuffix(" 次")
        lbl_threshold = QLabel("單句同虛詞出現門檻：")
        lbl_threshold.setFont(FontManager.get_font(size=int(9 * sf)))
        form.addRow(lbl_threshold, self.spin_particle)

        tab3_layout.addLayout(form)
        param_hint = QLabel("說明：當單句內「了」「的」「是」「有」「就」等同一虛詞出現達到此次數且比例偏高時，將觸發密度警告。")
        param_hint.setWordWrap(True)
        param_hint.setFont(FontManager.get_font(size=int(9 * sf)))
        param_hint.setStyleSheet("color: #888888;")
        tab3_layout.addWidget(param_hint)
        tab3_layout.addStretch()

        self.tabs.addTab(self.tab_params, "⚙️ 參數設定")

        layout.addWidget(self.tabs)

        # 底部按鈕
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_save = QPushButton("儲存設定")
        btn_save.setFont(FontManager.get_font(size=int(10 * sf), weight=QFont.Weight.Bold))
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #0e639c;
                color: #ffffff;
                padding: 6px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
        """)
        btn_save.clicked.connect(self.save_and_close)

        btn_cancel = QPushButton("取消")
        btn_cancel.setFont(FontManager.get_font(size=int(9 * sf)))
        btn_cancel.clicked.connect(self.reject)

        btn_box.addWidget(btn_save)
        btn_box.addWidget(btn_cancel)
        layout.addLayout(btn_box)

    def add_whitelist_word(self):
        word = self.input_whitelist.text().strip()
        if not word:
            return
        # 檢查是否已存在
        items = [self.list_whitelist.item(i).text() for i in range(self.list_whitelist.count())]
        if word in items:
            QMessageBox.information(self, "提示", f"「{word}」已在白名單中。")
            return
        self.list_whitelist.addItem(word)
        self.input_whitelist.clear()

    def delete_whitelist_word(self):
        row = self.list_whitelist.currentRow()
        if row >= 0:
            self.list_whitelist.takeItem(row)

    def add_custom_word(self):
        word = self.input_custom.text().strip()
        if not word:
            return
        items = [self.list_custom.item(i).text() for i in range(self.list_custom.count())]
        if word in items:
            QMessageBox.information(self, "提示", f"「{word}」已在自訂贅詞庫中。")
            return
        self.list_custom.addItem(word)
        self.input_custom.clear()

    def delete_custom_word(self):
        row = self.list_custom.currentRow()
        if row >= 0:
            self.list_custom.takeItem(row)

    def save_and_close(self):
        whitelist = [self.list_whitelist.item(i).text() for i in range(self.list_whitelist.count())]
        custom_words = [self.list_custom.item(i).text() for i in range(self.list_custom.count())]
        
        self.settings["whitelist"] = whitelist
        self.settings["custom_redundant_words"] = custom_words
        self.settings["particle_density_threshold"] = self.spin_particle.value()

        LintService.save_settings(self.settings)
        self.signal_settings_updated.emit()
        self.accept()
