import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QInputDialog, QLineEdit, QTextEdit, QFrame, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from utils.font_manager import FontManager
from utils.theme_manager import ThemeManager
from services.database import DatabaseService


class SnapshotDialog(QDialog):
    """版本快照管理對話框。
    
    提供作者建立專案歷史快照、檢視快照清單、刪除過期快照與一鍵還原功能。
    """
    signal_restore_snapshot = pyqtSignal(int)  # 傳遞 snapshot_id

    def __init__(self, parent=None, db_path=""):
        super().__init__(parent)
        self.db_path = db_path
        self.setWindowTitle("版本快照管理 (Version Snapshots)")
        self.resize(680, 480)
        self.setModal(True)
        ThemeManager.apply_theme_to_dialog(self, parent)

        self.init_ui()
        self.refresh_snapshots()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 頂部說明列
        top_layout = QHBoxLayout()
        lbl_hint = QLabel("📚 專案版本歷史快照：")
        lbl_hint.setFont(FontManager.get_font(size=11, weight=QFont.Weight.Bold))
        top_layout.addWidget(lbl_hint)

        top_layout.addStretch()

        self.btn_create = QPushButton("📸 建立當前快照...")
        self.btn_create.setFont(FontManager.get_font(size=9, weight=QFont.Weight.Bold))
        self.btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_create.setStyleSheet("""
            QPushButton {
                background-color: #2b78e4;
                color: #ffffff;
                padding: 5px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3b88f4;
            }
        """)
        top_layout.addWidget(self.btn_create)
        layout.addLayout(top_layout)

        # 快照表格
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["建立時間", "快照名稱", "字數", "備註說明"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        theme_name = "default"
        if self.parent() and hasattr(self.parent(), "current_theme"):
            theme_name = self.parent().current_theme
        theme_colors = ThemeManager.get_theme_colors(theme_name)
        tbl_bg = theme_colors.get("tree_bg", "#1e2227")
        tbl_fg = theme_colors.get("tree_fg", "#e3e3e3")
        tbl_border = theme_colors.get("tree_border", "#3e4451")
        tbl_sel = theme_colors.get("tree_item_selected_bg", "#094771")
        header_bg = theme_colors.get("header_bg", "#282c34")

        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {tbl_bg};
                color: {tbl_fg};
                border: 1px solid {tbl_border};
                border-radius: 4px;
                gridline-color: {tbl_border};
            }}
            QTableWidget::item {{
                padding: 4px 6px;
            }}
            QTableWidget::item:selected {{
                background-color: {tbl_sel};
                color: #ffffff;
            }}
            QHeaderView::section {{
                background-color: {header_bg};
                color: {tbl_fg};
                padding: 4px;
                border: 1px solid {tbl_border};
                font-weight: bold;
            }}
        """)
        layout.addWidget(self.table, 1)

        # 操作按鈕列
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_restore = QPushButton("🔄 還原至選取快照")
        self.btn_restore.setFont(FontManager.get_font(size=9, weight=QFont.Weight.Bold))
        self.btn_restore.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_restore.setStyleSheet("""
            QPushButton {
                background-color: #e5a00d;
                color: #000000;
                padding: 5px 14px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f5b01d;
            }
        """)
        self.btn_restore.clicked.connect(self.on_restore_clicked)
        btn_layout.addWidget(self.btn_restore)

        self.btn_delete = QPushButton("🗑️ 刪除快照")
        self.btn_delete.setFont(FontManager.get_font(size=9))
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.setStyleSheet("""
            QPushButton {
                background-color: #c94f4f;
                color: #ffffff;
                padding: 5px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d95f5f;
            }
        """)
        self.btn_delete.clicked.connect(self.on_delete_clicked)
        btn_layout.addWidget(self.btn_delete)

        btn_layout.addStretch()

        self.btn_close = QPushButton("關閉")
        self.btn_close.setFont(FontManager.get_font(size=9))
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_close)

        layout.addLayout(btn_layout)

    def refresh_snapshots(self):
        """重新從資料庫載入快照清單。"""
        if not self.db_path or not os.path.isfile(self.db_path):
            self.table.setRowCount(0)
            return

        snapshots = DatabaseService.list_snapshots(self.db_path)
        self.table.setRowCount(len(snapshots))
        for row_idx, snap in enumerate(snapshots):
            # 儲存 snapshot_id
            item_time = QTableWidgetItem(snap.get("timestamp", ""))
            item_time.setData(Qt.ItemDataRole.UserRole, snap.get("id"))
            
            item_name = QTableWidgetItem(snap.get("name", ""))
            item_words = QTableWidgetItem(f"{snap.get('word_count', 0):,}")
            item_words.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_note = QTableWidgetItem(snap.get("note", ""))

            self.table.setItem(row_idx, 0, item_time)
            self.table.setItem(row_idx, 1, item_name)
            self.table.setItem(row_idx, 2, item_words)
            self.table.setItem(row_idx, 3, item_note)

    def get_selected_snapshot_id(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        row = selected_rows[0].row()
        item = self.table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def on_restore_clicked(self):
        snap_id = self.get_selected_snapshot_id()
        if not snap_id:
            QMessageBox.warning(self, "提示", "請先點選欲還原的快照。")
            return

        reply = QMessageBox.question(
            self,
            "確認還原快照",
            "⚠️ 還原快照將會以該版本內容覆蓋當前編輯中的專案！\n（系統將在還原前自動建立一份目前狀態的保護快照）\n\n確定要還原嗎？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.signal_restore_snapshot.emit(snap_id)
            self.accept()

    def on_delete_clicked(self):
        snap_id = self.get_selected_snapshot_id()
        if not snap_id:
            QMessageBox.warning(self, "提示", "請先點選欲刪除的快照。")
            return

        reply = QMessageBox.question(
            self,
            "確認刪除",
            "確定要永久刪除此版本快照嗎？此操作無法復原。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            success = DatabaseService.delete_snapshot(self.db_path, snap_id)
            if success:
                self.refresh_snapshots()
            else:
                QMessageBox.warning(self, "失敗", "刪除快照失敗。")
