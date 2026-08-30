from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QWidget, QFrame, QColorDialog,
    QFontDialog, QMenu, QApplication
)
from PyQt6.QtGui import (
    QFont, QColor, QKeySequence, QShortcut, QAction
)
from PyQt6.QtCore import Qt, pyqtSignal
from utils.theme_manager import THEME_COLORS
from utils.font_manager import FontManager


class CardDetailTextEdit(QTextEdit):
    """卡片詳情純文字編輯器：支援強制無格式貼上與 AI 右鍵討論"""
    signal_save_requested = pyqtSignal()
    signal_ai_chat = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptRichText(False)

    def insertFromMimeData(self, source):
        """全局無格式貼上：過濾所有來源富文本/HTML格式，一律以純文字插入"""
        if source.hasText():
            self.insertPlainText(source.text())
        else:
            super().insertFromMimeData(source)

    def keyPressEvent(self, event):
        modifiers = event.modifiers()
        key = event.key()

        # Ctrl+S 快捷鍵儲存
        if modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_S:
            self.signal_save_requested.emit()
            event.accept()
            return

        super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        menu.addSeparator()

        selected_text = self.textCursor().selectedText().strip()
        has_selection = bool(selected_text)
        target_text = selected_text if has_selection else self.toPlainText().strip()
        scope_text = "選取內容" if has_selection else "卡片全文"

        act_chat = QAction(f"💬 與 AI 討論 ({scope_text})...", self)
        act_chat.setEnabled(bool(target_text))
        act_chat.triggered.connect(lambda: self.signal_ai_chat.emit(target_text))
        menu.addAction(act_chat)

        menu.exec(event.globalPos())


class CardDetailDialog(QDialog):
    """資料集卡片專屬詳細檢視與編輯對話框（純文字模式）"""
    signal_saved = pyqtSignal(str, str, str)  # (title, content, color_hex)

    def __init__(self, parent=None, title="", content="", color_hex="#2d2d2d", category_name="資料集卡片"):
        super().__init__(parent)
        self.main_window = parent
        self.card_title = title
        self.card_content = content
        self.color_hex = color_hex
        self.category_name = category_name

        self.scale_factor = getattr(parent, "scale_factor", 1.0) if parent else 1.0

        self.setWindowTitle(f"卡片詳情 — {self.card_title if self.card_title else '未命名卡片'}")
        self.resize(int(820 * self.scale_factor), int(640 * self.scale_factor))
        self.setMinimumSize(int(540 * self.scale_factor), int(420 * self.scale_factor))

        self.init_ui()
        self.apply_theme()
        self.update_word_count()

        # 快捷鍵支援
        QShortcut(QKeySequence("Ctrl+S"), self, self.on_save_clicked)
        QShortcut(QKeySequence("Ctrl+W"), self, self.accept)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(
            int(16 * self.scale_factor),
            int(14 * self.scale_factor),
            int(16 * self.scale_factor),
            int(14 * self.scale_factor)
        )
        main_layout.setSpacing(int(10 * self.scale_factor))

        # 1. 頂部標題與分類導航區
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(int(6 * self.scale_factor))

        top_meta_layout = QHBoxLayout()
        top_meta_layout.setSpacing(int(8 * self.scale_factor))

        # 分類徽章
        self.lbl_category_badge = QLabel(f"  {self.category_name}  ")
        self.lbl_category_badge.setFont(FontManager.get_font(size=int(9 * self.scale_factor), weight=QFont.Weight.Bold))
        top_meta_layout.addWidget(self.lbl_category_badge)

        # 顏色指示色塊與更換顏色按鈕
        self.color_indicator = QFrame()
        self.color_indicator.setFixedSize(int(14 * self.scale_factor), int(14 * self.scale_factor))
        self.color_indicator.setStyleSheet(f"border-radius: {int(7 * self.scale_factor)}px; background-color: {self.color_hex};")
        top_meta_layout.addWidget(self.color_indicator)

        self.btn_change_color = QPushButton("調整卡片顏色")
        self.btn_change_color.setFont(FontManager.get_font(size=int(8 * self.scale_factor)))
        self.btn_change_color.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_change_color.clicked.connect(self.on_choose_color)
        top_meta_layout.addWidget(self.btn_change_color)

        self.btn_choose_font = QPushButton("🔤 選擇字型")
        self.btn_choose_font.setFont(FontManager.get_font(size=int(8 * self.scale_factor)))
        self.btn_choose_font.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_choose_font.clicked.connect(self.on_choose_font)
        top_meta_layout.addWidget(self.btn_choose_font)

        self.btn_ellipsis = QPushButton("……")
        self.btn_ellipsis.setFont(FontManager.get_font(size=int(8 * self.scale_factor)))
        self.btn_ellipsis.setToolTip("插入省略號 (……)")
        self.btn_ellipsis.clicked.connect(lambda: self.editor.insertPlainText("……"))
        top_meta_layout.addWidget(self.btn_ellipsis)

        self.btn_emdash = QPushButton("──")
        self.btn_emdash.setFont(FontManager.get_font(size=int(8 * self.scale_factor)))
        self.btn_emdash.setToolTip("插入破折號 (──)")
        self.btn_emdash.clicked.connect(lambda: self.editor.insertPlainText("──"))
        top_meta_layout.addWidget(self.btn_emdash)

        top_meta_layout.addStretch()

        self.lbl_word_count = QLabel("字數：0")
        self.lbl_word_count.setFont(FontManager.get_font(size=int(9 * self.scale_factor)))
        self.lbl_word_count.setStyleSheet("color: #888888;")
        top_meta_layout.addWidget(self.lbl_word_count)

        header_layout.addLayout(top_meta_layout)

        # 卡片標題輸入列
        title_row = QHBoxLayout()
        title_lbl = QLabel("卡片名稱：")
        title_lbl.setFont(FontManager.get_font(size=int(10 * self.scale_factor), weight=QFont.Weight.Bold))
        self.title_edit = QLineEdit(self.card_title)
        self.title_edit.setFont(FontManager.get_font(size=int(11 * self.scale_factor), weight=QFont.Weight.Bold))
        self.title_edit.setPlaceholderText("請輸入卡片名稱...")
        title_row.addWidget(title_lbl)
        title_row.addWidget(self.title_edit, 1)
        header_layout.addLayout(title_row)

        main_layout.addWidget(header_widget)

        # 2. 純文字編輯區
        self.editor = CardDetailTextEdit()
        self.editor.setFont(FontManager.get_font(size=int(11 * self.scale_factor)))
        self.editor.setPlaceholderText("在此輸入卡片設定、人物傳記或世界觀細節（純文字編輯，支援全局無格式貼上）...")
        self.editor.setPlainText(self.card_content)
        self.editor.textChanged.connect(self.update_word_count)
        self.editor.signal_save_requested.connect(self.on_save_clicked)
        self.editor.signal_ai_chat.connect(self.open_ai_chat)
        main_layout.addWidget(self.editor, 1)

        # 3. 底部操作按鈕列
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(int(10 * self.scale_factor))

        self.lbl_tip = QLabel("純文字寫作模式：貼上文字時自動過濾來源格式。支援 Ctrl+S 儲存、Ctrl+W 關閉。")
        self.lbl_tip.setFont(FontManager.get_font(size=int(8 * self.scale_factor)))
        self.lbl_tip.setStyleSheet("color: #888888;")
        bottom_layout.addWidget(self.lbl_tip)

        bottom_layout.addStretch()

        self.btn_copy = QPushButton("複製內文")
        self.btn_copy.setFont(FontManager.get_font(size=int(9 * self.scale_factor)))
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.clicked.connect(self.on_copy_clicked)
        bottom_layout.addWidget(self.btn_copy)

        self.btn_save = QPushButton("儲存變更 (Ctrl+S)")
        self.btn_save.setFont(FontManager.get_font(size=int(9 * self.scale_factor), weight=QFont.Weight.Bold))
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.clicked.connect(self.on_save_clicked)
        bottom_layout.addWidget(self.btn_save)

        self.btn_close = QPushButton("關閉")
        self.btn_close.setFont(FontManager.get_font(size=int(9 * self.scale_factor)))
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.on_close_clicked)
        bottom_layout.addWidget(self.btn_close)

        main_layout.addLayout(bottom_layout)

    def update_word_count(self):
        text = self.editor.toPlainText()
        char_count = len(text)
        self.lbl_word_count.setText(f"字數：{char_count}")

    def on_choose_font(self):
        ok, font = QFontDialog.getFont(self.editor.font(), self, "選擇卡片字型")
        if ok:
            self.editor.setFont(font)

    def on_choose_color(self):
        dialog = QColorDialog(QColor(self.color_hex), self)
        dialog.setWindowTitle("選擇卡片自訂顏色")
        if dialog.exec() == QColorDialog.DialogCode.Accepted:
            selected_color = dialog.selectedColor()
            self.color_hex = selected_color.name()
            self.color_indicator.setStyleSheet(
                f"border-radius: {int(7 * self.scale_factor)}px; background-color: {self.color_hex};"
            )

    def get_current_markdown_content(self) -> str:
        """相容性方法：回傳純文字內容"""
        return self.editor.toPlainText()

    def on_copy_clicked(self):
        content = self.editor.toPlainText()
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(content)
            self.lbl_tip.setText("已複製卡片內文至剪貼簿！")

    def on_save_clicked(self):
        new_title = self.title_edit.text().strip()
        new_content = self.editor.toPlainText()
        self.card_title = new_title
        self.card_content = new_content

        self.signal_saved.emit(new_title, new_content, self.color_hex)
        self.lbl_tip.setText("卡片內容已成功儲存！")
        self.setWindowTitle(f"卡片詳情 — {self.card_title if self.card_title else '未命名卡片'}")

    def on_close_clicked(self):
        new_title = self.title_edit.text().strip()
        new_content = self.editor.toPlainText()
        if new_title != self.card_title or new_content != self.card_content:
            self.signal_saved.emit(new_title, new_content, self.color_hex)
        self.accept()

    def get_data(self):
        return {
            "title": self.title_edit.text().strip(),
            "content": self.editor.toPlainText(),
            "color_hex": self.color_hex
        }

    def apply_theme(self):
        theme_name = getattr(self.main_window, "current_theme", "default") if self.main_window else "default"
        theme_colors = THEME_COLORS.get(theme_name, THEME_COLORS["default"])

        main_bg = theme_colors.get("main_bg", "#1e1e1e")
        main_fg = theme_colors.get("main_fg", "#e3e3e3")
        tree_bg = theme_colors.get("tree_bg", "#252526")
        border_color = theme_colors.get("border_color", "#3d3d3d")
        btn_hover_bg = theme_colors.get("btn_hover_bg", "#3e3e42")
        badge_bg = theme_colors.get("tab_selected_indicator", "#007acc")

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {main_bg};
                color: {main_fg};
            }}
            QLabel {{
                color: {main_fg};
                background-color: transparent;
            }}
            QLineEdit {{
                background-color: {tree_bg};
                color: {main_fg};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 6px;
            }}
            QLineEdit:focus {{
                border: 1px solid {badge_bg};
            }}
            QTextEdit {{
                background-color: {tree_bg};
                color: {main_fg};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 10px;
                line-height: 150%;
            }}
            QPushButton {{
                background-color: {tree_bg};
                color: {main_fg};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 5px 10px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover_bg};
                border-color: {badge_bg};
            }}
        """)

        self.lbl_category_badge.setStyleSheet(f"""
            background-color: rgba(0, 122, 204, 0.25);
            color: #4fc1ff;
            border: 1px solid rgba(0, 122, 204, 0.5);
            border-radius: 4px;
            padding: 3px 8px;
        """)

    def open_ai_chat(self, context_text: str = ""):
        """開啟 AI 對話視窗並引用卡片文字"""
        from views.dialogs.ai_chat_dialog import AIChatDialog
        dlg = AIChatDialog(self, initial_context=context_text)
        dlg.signal_insert_to_editor.connect(lambda text: self.editor.insertPlainText(text))
        dlg.exec()
