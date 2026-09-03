import os
from typing import List, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox,
    QComboBox, QMessageBox, QAbstractItemView, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QFont, QColor, QTextCursor

from utils.font_manager import FontManager
from utils.theme_manager import ThemeManager
from services.lint_service import LintService, LintIssue
from views.dialogs.lint_whitelist_dialog import LintWhitelistDialog

class LintDialog(QDialog):
    """文風與贅詞檢查主視窗，提供即時問題掃描、篩選、定位跳轉與白名單維護入口。"""

    signal_navigate_to_text = pyqtSignal(int, int)  # start_pos, end_pos

    def __init__(self, parent=None, get_text_func=None):
        super().__init__(parent)
        self.setWindowTitle("文風與贅詞檢查")
        ThemeManager.apply_theme_to_dialog(self, parent)
        self.scale_factor = getattr(self, "scale_factor", 1.0)
        self.resize(int(780 * self.scale_factor), int(520 * self.scale_factor))
        self.get_text_func = get_text_func
        self.settings = LintService.load_settings()
        self.current_issues: List[LintIssue] = []

        self.init_ui()
        self.rescan()

    def init_ui(self):
        layout = QVBoxLayout(self)
        sf = self.scale_factor
        layout.setContentsMargins(int(15 * sf), int(15 * sf), int(15 * sf), int(15 * sf))
        layout.setSpacing(int(10 * sf))

        # 頂部：總開關與說明
        top_bar = QHBoxLayout()
        self.chk_master = QCheckBox("啟用文風與贅詞檢查引擎")
        self.chk_master.setFont(FontManager.get_font(size=int(11 * sf), weight=QFont.Weight.Bold))
        self.chk_master.setChecked(self.settings.get("enabled", True))
        self.chk_master.toggled.connect(self.on_master_toggle)
        top_bar.addWidget(self.chk_master)

        top_bar.addStretch()

        self.btn_manage_whitelist = QPushButton("📚 詞彙庫與白名單管理...")
        self.btn_manage_whitelist.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_manage_whitelist.clicked.connect(self.open_whitelist_manager)
        top_bar.addWidget(self.btn_manage_whitelist)

        self.btn_rescan = QPushButton("🔄 重新掃描")
        self.btn_rescan.setFont(FontManager.get_font(size=int(9 * sf), weight=QFont.Weight.Bold))
        self.btn_rescan.clicked.connect(self.rescan)
        top_bar.addWidget(self.btn_rescan)

        layout.addLayout(top_bar)

        # 次頂部：細項規則開關
        rules_bar = QHBoxLayout()
        rules_bar.setSpacing(int(15 * sf))

        rules = self.settings.get("rules", {})
        self.chk_redundant = QCheckBox("公文與冗贅片語")
        self.chk_redundant.setFont(FontManager.get_font(size=int(9 * sf)))
        self.chk_redundant.setChecked(rules.get("redundant_phrase", True))
        self.chk_redundant.toggled.connect(self.on_rule_toggle)

        self.chk_particle = QCheckBox("虛詞過密偵測")
        self.chk_particle.setFont(FontManager.get_font(size=int(9 * sf)))
        self.chk_particle.setChecked(rules.get("high_density_particle", True))
        self.chk_particle.toggled.connect(self.on_rule_toggle)

        self.chk_passive = QCheckBox("被動語態弱句")
        self.chk_passive.setFont(FontManager.get_font(size=int(9 * sf)))
        self.chk_passive.setChecked(rules.get("passive_voice", True))
        self.chk_passive.toggled.connect(self.on_rule_toggle)

        self.chk_dup = QCheckBox("相鄰重複用詞")
        self.chk_dup.setFont(FontManager.get_font(size=int(9 * sf)))
        self.chk_dup.setChecked(rules.get("duplicate_words", True))
        self.chk_dup.toggled.connect(self.on_rule_toggle)

        rules_bar.addWidget(self.chk_redundant)
        rules_bar.addWidget(self.chk_particle)
        rules_bar.addWidget(self.chk_passive)
        rules_bar.addWidget(self.chk_dup)
        rules_bar.addStretch()

        layout.addLayout(rules_bar)

        # 篩選列與統計
        filter_bar = QHBoxLayout()
        lbl_filter = QLabel("篩選分類：")
        lbl_filter.setFont(FontManager.get_font(size=int(9 * sf)))
        self.combo_filter = QComboBox()
        self.combo_filter.setFont(FontManager.get_font(size=int(9 * sf)))
        self.combo_filter.addItems(["全部分類", "公文/冗贅片語", "虛詞過密", "被動語態", "相鄰重複用詞"])
        self.combo_filter.currentIndexChanged.connect(self.apply_filter)

        self.lbl_stats = QLabel("掃描完成：共發現 0 處修飾建議")
        self.lbl_stats.setFont(FontManager.get_font(size=int(9 * sf)))
        self.lbl_stats.setStyleSheet("color: #a0aec0;")

        filter_bar.addWidget(lbl_filter)
        filter_bar.addWidget(self.combo_filter)
        filter_bar.addStretch()
        filter_bar.addWidget(self.lbl_stats)

        layout.addLayout(filter_bar)

        # 問題列表 Table
        self.table = QTableWidget()
        self.table.setFont(FontManager.get_font(size=int(9 * sf)))
        self.table.horizontalHeader().setFont(FontManager.get_font(size=int(9 * sf), weight=QFont.Weight.Bold))
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["行號", "分類", "標記文字 / 片段", "說明與修改建議"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.itemClicked.connect(self.on_table_item_clicked)
        self.table.itemDoubleClicked.connect(self.on_table_item_clicked)

        layout.addWidget(self.table, 1)

        # 底部列
        bottom_bar = QHBoxLayout()
        tip_lbl = QLabel("※ 點擊列表項目可立即在主編輯器中選取並定位該文字。")
        tip_lbl.setFont(FontManager.get_font(size=int(9 * sf)))
        tip_lbl.setStyleSheet("color: #a0aec0;")
        bottom_bar.addWidget(tip_lbl)
        bottom_bar.addStretch()

        btn_close = QPushButton("關閉")
        btn_close.setFont(FontManager.get_font(size=int(9 * sf)))
        btn_close.clicked.connect(self.accept)
        bottom_bar.addWidget(btn_close)

        layout.addLayout(bottom_bar)

    def on_master_toggle(self, checked: bool):
        self.settings["enabled"] = checked
        self.chk_redundant.setEnabled(checked)
        self.chk_particle.setEnabled(checked)
        self.chk_passive.setEnabled(checked)
        self.chk_dup.setEnabled(checked)
        LintService.save_settings(self.settings)
        self.rescan()

    def on_rule_toggle(self):
        self.settings["rules"] = {
            "redundant_phrase": self.chk_redundant.isChecked(),
            "high_density_particle": self.chk_particle.isChecked(),
            "passive_voice": self.chk_passive.isChecked(),
            "duplicate_words": self.chk_dup.isChecked()
        }
        LintService.save_settings(self.settings)
        self.rescan()

    def open_whitelist_manager(self):
        dlg = LintWhitelistDialog(self, self.settings)
        dlg.signal_settings_updated.connect(self.on_whitelist_updated)
        dlg.exec()

    def on_whitelist_updated(self):
        self.settings = LintService.load_settings()
        self.rescan()

    def rescan(self):
        """重新掃描當前編輯文字。"""
        if not self.get_text_func:
            return

        text = self.get_text_func()
        if not self.settings.get("enabled", True):
            self.current_issues = []
            self.lbl_stats.setText("檢查引擎已停用")
        else:
            self.current_issues = LintService.check_text(text, self.settings)
            self.lbl_stats.setText(f"掃描完成：共發現 {len(self.current_issues)} 處修飾建議")

        self.apply_filter()

    def apply_filter(self):
        filter_text = self.combo_filter.currentText()
        self.table.clearContents()
        self.table.setRowCount(0)

        for issue in self.current_issues:
            if filter_text != "全部分類" and issue.issue_type_name != filter_text:
                continue

            row = self.table.rowCount()
            self.table.insertRow(row)

            item_line = QTableWidgetItem(f"第 {issue.line_number} 行")
            item_line.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_type = QTableWidgetItem(issue.issue_type_name)
            item_type.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_target = QTableWidgetItem(issue.target_text)
            item_msg = QTableWidgetItem(f"{issue.message} — {issue.suggestion}")

            # 存入 issue 實例方便跳轉
            item_line.setData(Qt.ItemDataRole.UserRole, issue)

            self.table.setItem(row, 0, item_line)
            self.table.setItem(row, 1, item_type)
            self.table.setItem(row, 2, item_target)
            self.table.setItem(row, 3, item_msg)

    def on_table_item_clicked(self, item):
        row = item.row()
        line_item = self.table.item(row, 0)
        if line_item:
            issue: LintIssue = line_item.data(Qt.ItemDataRole.UserRole)
            if issue:
                self.signal_navigate_to_text.emit(issue.start_pos, issue.end_pos)

    def show_context_menu(self, pos: QPoint):
        item = self.table.itemAt(pos)
        if not item:
            return
        row = item.row()
        line_item = self.table.item(row, 0)
        if not line_item:
            return
        issue: LintIssue = line_item.data(Qt.ItemDataRole.UserRole)
        if not issue:
            return

        menu = QMenu(self)
        act_nav = menu.addAction("🔍 在編輯器中定位選取")
        act_whitelist = menu.addAction(f"🛡️ 將「{issue.target_text[:10]}」加入忽略白名單")

        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == act_nav:
            self.signal_navigate_to_text.emit(issue.start_pos, issue.end_pos)
        elif action == act_whitelist:
            clean_word = issue.target_text.strip()
            if "「" in clean_word and "」" in clean_word:
                clean_word = clean_word.split("「")[1].split("」")[0]
            if clean_word not in self.settings.get("whitelist", []):
                self.settings.setdefault("whitelist", []).append(clean_word)
                LintService.save_settings(self.settings)
                QMessageBox.information(self, "成功", f"已將「{clean_word}」加入白名單，未來將不再提示。")
                self.rescan()
