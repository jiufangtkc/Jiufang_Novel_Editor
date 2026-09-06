from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QRadioButton, QButtonGroup, QGroupBox,
    QTextEdit, QSplitter, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from utils.font_manager import FontManager
from utils.theme_manager import ThemeManager
from services.text_formatter_service import TextFormatterService


class AutoFormatDialog(QDialog):
    """小說自動排版設定與預覽對話框。

    提供標點轉換、段首縮排（含清除縮排）、空行增刪等自訂排版選項，
    並具備即時預覽功能。
    """

    def __init__(self, parent=None, current_text: str = ""):
        super().__init__(parent)
        self.setWindowTitle("自動排版工具")
        ThemeManager.apply_theme_to_dialog(self, parent)
        self.scale_factor = getattr(self, "scale_factor", 1.0)
        self.resize(int(820 * self.scale_factor), int(540 * self.scale_factor))
        self.setModal(True)

        self.original_text = current_text
        self.init_ui()
        self.update_preview()

    def init_ui(self):
        sf = self.scale_factor
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(int(16 * sf), int(16 * sf), int(16 * sf), int(16 * sf))
        main_layout.setSpacing(int(12 * sf))

        # 主體分割區：左側設定選項，右側預覽
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ----------------- 左側設定區 -----------------
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, int(8 * sf), 0)
        left_layout.setSpacing(int(12 * sf))

        # 1. 標點轉換群組
        grp_punc = QGroupBox("標點符號處理")
        grp_punc.setFont(FontManager.get_font(size=int(10 * sf), weight=QFont.Weight.Bold))
        layout_punc = QVBoxLayout(grp_punc)
        self.chk_convert_punc = QCheckBox("將半形標點轉為中文全形標點 (, . ! ? : ; ( ) ~)")
        self.chk_convert_punc.setFont(FontManager.get_font(size=int(9 * sf)))
        self.chk_convert_punc.setChecked(True)
        self.chk_convert_punc.toggled.connect(self.update_preview)
        layout_punc.addWidget(self.chk_convert_punc)
        left_layout.addWidget(grp_punc)

        # 2. 段首縮排群組
        grp_indent = QGroupBox("段首縮排處理")
        grp_indent.setFont(FontManager.get_font(size=int(10 * sf), weight=QFont.Weight.Bold))
        layout_indent = QVBoxLayout(grp_indent)
        self.btn_grp_indent = QButtonGroup(self)

        self.radio_indent_add = QRadioButton("每段段首縮排二格全形空格")
        self.radio_indent_add.setFont(FontManager.get_font(size=int(9 * sf)))
        self.radio_indent_add.setChecked(True)
        self.radio_indent_add.toggled.connect(self.update_preview)
        self.btn_grp_indent.addButton(self.radio_indent_add)
        layout_indent.addWidget(self.radio_indent_add)

        self.radio_indent_remove = QRadioButton("清除所有段首空格（可逆恢復齊頭）")
        self.radio_indent_remove.setFont(FontManager.get_font(size=int(9 * sf)))
        self.radio_indent_remove.toggled.connect(self.update_preview)
        self.btn_grp_indent.addButton(self.radio_indent_remove)
        layout_indent.addWidget(self.radio_indent_remove)

        self.radio_indent_none = QRadioButton("不變更段首縮排")
        self.radio_indent_none.setFont(FontManager.get_font(size=int(9 * sf)))
        self.radio_indent_none.toggled.connect(self.update_preview)
        self.btn_grp_indent.addButton(self.radio_indent_none)
        layout_indent.addWidget(self.radio_indent_none)

        left_layout.addWidget(grp_indent)

        # 3. 空行處理群組
        grp_empty = QGroupBox("空行排版處理")
        grp_empty.setFont(FontManager.get_font(size=int(10 * sf), weight=QFont.Weight.Bold))
        layout_empty = QVBoxLayout(grp_empty)
        self.btn_grp_empty = QButtonGroup(self)

        self.radio_empty_compact = QRadioButton("刪除多餘空行（連續空行壓縮為單一空行）")
        self.radio_empty_compact.setFont(FontManager.get_font(size=int(9 * sf)))
        self.radio_empty_compact.setChecked(True)
        self.radio_empty_compact.toggled.connect(self.update_preview)
        self.btn_grp_empty.addButton(self.radio_empty_compact)
        layout_empty.addWidget(self.radio_empty_compact)

        self.radio_empty_remove_all = QRadioButton("移除所有空行（各段落緊湊排列）")
        self.radio_empty_remove_all.setFont(FontManager.get_font(size=int(9 * sf)))
        self.radio_empty_remove_all.toggled.connect(self.update_preview)
        self.btn_grp_empty.addButton(self.radio_empty_remove_all)
        layout_empty.addWidget(self.radio_empty_remove_all)

        self.radio_empty_add = QRadioButton("段落之間自動增加空行（每段間隔一行空行）")
        self.radio_empty_add.setFont(FontManager.get_font(size=int(9 * sf)))
        self.radio_empty_add.toggled.connect(self.update_preview)
        self.btn_grp_empty.addButton(self.radio_empty_add)
        layout_empty.addWidget(self.radio_empty_add)

        self.radio_empty_none = QRadioButton("不變更空行")
        self.radio_empty_none.setFont(FontManager.get_font(size=int(9 * sf)))
        self.radio_empty_none.toggled.connect(self.update_preview)
        self.btn_grp_empty.addButton(self.radio_empty_none)
        layout_empty.addWidget(self.radio_empty_none)

        left_layout.addWidget(grp_empty)

        # 4. 套用範圍群組
        grp_scope = QGroupBox("套用範圍")
        grp_scope.setFont(FontManager.get_font(size=int(10 * sf), weight=QFont.Weight.Bold))
        layout_scope = QVBoxLayout(grp_scope)
        self.btn_grp_scope = QButtonGroup(self)

        self.radio_scope_current = QRadioButton("僅套用至當前編輯章節")
        self.radio_scope_current.setFont(FontManager.get_font(size=int(9 * sf)))
        self.radio_scope_current.setChecked(True)
        self.btn_grp_scope.addButton(self.radio_scope_current)
        layout_scope.addWidget(self.radio_scope_current)

        self.radio_scope_all = QRadioButton("套用至全書所有章節")
        self.radio_scope_all.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_grp_scope.addButton(self.radio_scope_all)
        layout_scope.addWidget(self.radio_scope_all)

        left_layout.addWidget(grp_scope)
        left_layout.addStretch()

        splitter.addWidget(left_widget)

        # ----------------- 右側預覽區 -----------------
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(int(8 * sf), 0, 0, 0)
        right_layout.setSpacing(int(8 * sf))

        lbl_preview_title = QLabel("即時排版效果預覽：")
        lbl_preview_title.setFont(FontManager.get_font(size=int(10 * sf), weight=QFont.Weight.Bold))
        right_layout.addWidget(lbl_preview_title)

        self.txt_preview = QTextEdit()
        self.txt_preview.setFont(FontManager.get_font(size=int(10 * sf)))
        self.txt_preview.setReadOnly(True)
        right_layout.addWidget(self.txt_preview)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)
        main_layout.addWidget(splitter, 1)

        # ----------------- 底部按鈕區 -----------------
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_cancel.clicked.connect(self.reject)
        bottom_layout.addWidget(self.btn_cancel)

        self.btn_apply = QPushButton("執行排版")
        self.btn_apply.setFont(FontManager.get_font(size=int(9 * sf), weight=QFont.Weight.Bold))
        self.btn_apply.clicked.connect(self.accept)
        bottom_layout.addWidget(self.btn_apply)

        main_layout.addLayout(bottom_layout)

    def get_options(self) -> dict:
        """取得當前勾選的排版設定字典。"""
        # 段首縮排模式
        if self.radio_indent_add.isChecked():
            indent_mode = 'indent'
        elif self.radio_indent_remove.isChecked():
            indent_mode = 'remove'
        else:
            indent_mode = 'none'

        # 空行處理模式
        if self.radio_empty_compact.isChecked():
            empty_line_mode = 'compact'
        elif self.radio_empty_remove_all.isChecked():
            empty_line_mode = 'remove_all'
        elif self.radio_empty_add.isChecked():
            empty_line_mode = 'add'
        else:
            empty_line_mode = 'none'

        # 套用範圍
        scope = 'current' if self.radio_scope_current.isChecked() else 'all'

        return {
            'convert_punctuation': self.chk_convert_punc.isChecked(),
            'indent_mode': indent_mode,
            'empty_line_mode': empty_line_mode,
            'scope': scope,
        }

    def update_preview(self):
        """根據目前選項運算預覽結果並更新至右側預覽框。"""
        if not hasattr(self, 'txt_preview'):
            return
        options = self.get_options()
        formatted = TextFormatterService.format_text(self.original_text, options)
        self.txt_preview.setPlainText(formatted)
