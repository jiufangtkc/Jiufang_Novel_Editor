import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from utils.font_manager import FontManager
from utils.theme_manager import ThemeManager
from services.app_settings_service import AppSettingsService


class StoragePathDialog(QDialog):
    """存檔路徑設定對話框。
    
    提供作者自訂專案存檔與暫存檔的根目錄（如 Dropbox、OneDrive 或本機自訂目錄），
    以實現無痛雲端同步。
    """

    def __init__(self, parent=None, current_path: str = ""):
        super().__init__(parent)
        self.setWindowTitle("存檔路徑設定")
        ThemeManager.apply_theme_to_dialog(self, parent)
        self.scale_factor = getattr(self, "scale_factor", 1.0)
        self.resize(int(520 * self.scale_factor), int(290 * self.scale_factor))
        self.setModal(True)

        self.default_path = AppSettingsService.get_default_storage_path()
        self.current_path = current_path if current_path else self.default_path

        self.init_ui()

    def init_ui(self):
        sf = self.scale_factor
        layout = QVBoxLayout(self)
        layout.setContentsMargins(int(20 * sf), int(20 * sf), int(20 * sf), int(20 * sf))
        layout.setSpacing(int(14 * sf))

        # 頂部標題與說明
        header_layout = QVBoxLayout()
        header_layout.setSpacing(int(4 * sf))
        lbl_title = QLabel("📁 稿件與暫存檔存檔路徑設定")
        lbl_title.setFont(FontManager.get_font(size=int(11 * sf), weight=QFont.Weight.Bold))
        header_layout.addWidget(lbl_title)

        lbl_desc = QLabel(
            "設定稿件 (.db) 與自動暫存檔的儲存根目錄。\n"
            "您可以選擇 Dropbox、OneDrive 等同步資料夾，輕鬆實現多裝置雲端自動同步。"
        )
        lbl_desc.setFont(FontManager.get_font(size=int(9 * sf)))
        lbl_desc.setStyleSheet("color: #888888;")
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
            QLineEdit {{
                background-color: {theme_colors.get('input_bg', '#1e1e1e')};
                color: {theme_colors.get('input_fg', '#ffffff')};
                border: 1px solid {theme_colors.get('input_border', '#555555')};
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border: 1px solid {accent};
            }}
        """)
        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(8)

        lbl_path_title = QLabel("當前存檔根目錄：")
        form_layout.addWidget(lbl_path_title)

        path_input_layout = QHBoxLayout()
        path_input_layout.setSpacing(8)

        self.line_path = QLineEdit()
        self.line_path.setText(self.current_path)
        self.line_path.setPlaceholderText("請選擇或輸入存檔資料夾路徑...")
        path_input_layout.addWidget(self.line_path, 1)

        self.btn_browse = QPushButton("瀏覽...")
        self.btn_browse.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme_colors.get('btn_bg', '#3c3f41')};
                color: {fg};
                border: 1px solid {theme_colors.get('btn_border', '#555555')};
                border-radius: 4px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: {theme_colors.get('btn_hover_bg', '#4c4f51')};
            }}
        """)
        self.btn_browse.clicked.connect(self._browse_directory)
        path_input_layout.addWidget(self.btn_browse)

        form_layout.addLayout(path_input_layout)

        # 預設路徑按鈕
        btn_reset_layout = QHBoxLayout()
        btn_reset_layout.addStretch()
        self.btn_reset_default = QPushButton("恢復預設路徑")
        self.btn_reset_default.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {accent};
                border: none;
                font-size: 11px;
                text-decoration: underline;
            }}
            QPushButton:hover {{
                opacity: 0.8;
            }}
        """)
        self.btn_reset_default.clicked.connect(self._reset_to_default)
        btn_reset_layout.addWidget(self.btn_reset_default)
        form_layout.addLayout(btn_reset_layout)

        layout.addWidget(form_frame)

        # 提示文字
        lbl_hint = QLabel(
            "💡 提示：變更存檔路徑後，系統將自動在該目錄下建立 Story、Temp_doc 與 Export 資料夾，"
            "並將舊路徑中的稿件、暫存檔與匯出檔案自動遷移至新目錄。"
        )
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

        self.btn_ok = QPushButton("確定變更")
        self.btn_ok.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                color: #ffffff;
                border-radius: 4px;
                padding: 6px 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
        """)
        self.btn_ok.clicked.connect(self._on_confirm)
        btn_layout.addWidget(self.btn_ok)

        layout.addLayout(btn_layout)

    def _browse_directory(self):
        """開啟資料夾選擇對話框。"""
        current = self.line_path.text().strip() or self.default_path
        chosen = QFileDialog.getExistingDirectory(
            self,
            "選擇存檔目錄（如 Dropbox、OneDrive 或本機資料夾）",
            current
        )
        if chosen:
            self.line_path.setText(os.path.abspath(chosen))

    def _reset_to_default(self):
        """重設為系統預設目錄。"""
        self.line_path.setText(self.default_path)

    def _on_confirm(self):
        """確認並驗證輸入的路徑。"""
        target_path = self.line_path.text().strip()
        if not target_path:
            QMessageBox.warning(self, "路徑無效", "存檔路徑不可為空，請輸入或選擇有效目錄。")
            return
        
        target_path = os.path.abspath(target_path)
        self.line_path.setText(target_path)
        self.accept()

    def get_selected_storage_path(self) -> str:
        """取得使用者設定的存檔路徑。"""
        return self.line_path.text().strip()
