from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QPushButton, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox, QMessageBox,
    QWidget, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal

class AIProofreadDialog(QDialog):
    """AI 校稿對話框 (非強制性視窗)"""
    
    # 傳遞 (node_id, char_offset, match_len)
    signal_navigate_to_match = pyqtSignal(str, int, int)
    # 發起校稿請求 (scope, types)
    signal_start_proofread = pyqtSignal(str, dict)
    # 改變狀態信號 (result_id, new_status)
    signal_change_status = pyqtSignal(str, str)
    # 忽略規則信號 (rule_type, target_word, result_id)
    signal_ignore_rule = pyqtSignal(str, str, str)
    
    def __init__(self, parent=None, target_text: str = ""):
        super().__init__(parent)
        self.target_text = target_text
        self.setWindowTitle("🔎 AI 校稿列表")
        self.scale_factor = getattr(parent, "scale_factor", 1.0) if parent else 1.0
        self.resize(int(850 * self.scale_factor), int(650 * self.scale_factor))
        # 設定為非強制性視窗，讓使用者可以點擊並同時在編輯器操作
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowMaximizeButtonHint)
        self.setup_ui()

    def setup_ui(self):
        sf = self.scale_factor
        layout = QVBoxLayout(self)
        layout.setSpacing(int(10 * sf))
        layout.setContentsMargins(int(16 * sf), int(16 * sf), int(16 * sf), int(16 * sf))
        
        # --- 設定區塊 ---
        setting_group = QVBoxLayout()
        lbl_info = QLabel("請選擇您希望 AI 校稿執行的檢查項目：")
        from utils.font_manager import FontManager
        lbl_info.setFont(FontManager.get_font(size=int(11 * sf), weight=QFont.Weight.Bold))
        setting_group.addWidget(lbl_info)
        
        self.cb_typo = QCheckBox("尋找錯字、漏字與別字")
        self.cb_typo.setFont(FontManager.get_font(size=int(9 * sf)))
        self.cb_typo.setChecked(True)
        self.cb_usage = QCheckBox("檢查錯誤用典與用詞")
        self.cb_usage.setFont(FontManager.get_font(size=int(9 * sf)))
        self.cb_usage.setChecked(True)
        self.cb_suggestion = QCheckBox("段落改寫建議")
        self.cb_suggestion.setFont(FontManager.get_font(size=int(9 * sf)))
        self.cb_suggestion.setChecked(True)
        
        setting_group.addWidget(self.cb_typo)
        setting_group.addWidget(self.cb_usage)
        setting_group.addWidget(self.cb_suggestion)
        
        # 範圍選擇
        scope_layout = QHBoxLayout()
        lbl_scope = QLabel("掃描範圍：")
        lbl_scope.setFont(FontManager.get_font(size=int(9 * sf)))
        self.combo_scope = QComboBox()
        self.combo_scope.setFont(FontManager.get_font(size=int(9 * sf)))
        self.combo_scope.addItems(["目前章節", "目前選取文字", "全書全文"])
        if self.target_text and len(self.target_text) > 0 and self.target_text != "【請先開啟一個章節進行寫作】":
             # 簡單判斷是否有選取
             # 這裡我們預設還是目前章節，由外部決定
             pass
        
        scope_layout.addWidget(lbl_scope)
        scope_layout.addWidget(self.combo_scope)
        scope_layout.addStretch()
        setting_group.addLayout(scope_layout)
        
        layout.addLayout(setting_group)
        
        # --- 按鈕區塊 ---
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("開始校稿")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.setFont(FontManager.get_font(size=int(10 * sf), weight=QFont.Weight.Bold))
        self.btn_start.setMinimumHeight(int(32 * sf))
        self.btn_start.clicked.connect(self.on_start_clicked)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_start)
        
        layout.addLayout(btn_layout)
        
        # --- 結果顯示區塊 (TabWidget) ---
        self.tabs = QTabWidget()
        self.tabs.setFont(FontManager.get_font(size=int(9 * sf)))
        
        self.tab_typo = QWidget()
        self.tab_usage = QWidget()
        self.tab_suggestion = QWidget()
        
        self.setup_table_tab(self.tab_typo, "typo")
        self.setup_table_tab(self.tab_usage, "usage")
        self.setup_table_tab(self.tab_suggestion, "suggestion")
        
        self.tabs.addTab(self.tab_typo, "錯漏字與別字")
        self.tabs.addTab(self.tab_usage, "用詞與用典")
        self.tabs.addTab(self.tab_suggestion, "改寫建議")
        
        layout.addWidget(self.tabs)
        
    def setup_table_tab(self, tab_widget: QWidget, category: str):
        layout = QVBoxLayout(tab_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        table = QTableWidget(0, 6)
        sf = self.scale_factor
        from utils.font_manager import FontManager
        table.setFont(FontManager.get_font(size=int(9 * sf)))
        table.horizontalHeader().setFont(FontManager.get_font(size=int(9 * sf), weight=QFont.Weight.Bold))
        table.setHorizontalHeaderLabels(["狀態", "章節", "原文", "建議", "理由", "操作"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        # 綁定雙擊導航
        table.itemDoubleClicked.connect(lambda item, c=category: self.on_item_double_clicked(item, c))
        
        setattr(self, f"table_{category}", table)
        layout.addWidget(table)
        
    def on_start_clicked(self):
        if not (self.cb_typo.isChecked() or self.cb_usage.isChecked() or self.cb_suggestion.isChecked()):
            QMessageBox.warning(self, "提示", "請至少勾選一項校稿項目。")
            return
            
        scope = self.combo_scope.currentText()
        options = {
            "typo": self.cb_typo.isChecked(),
            "usage": self.cb_usage.isChecked(),
            "suggestion": self.cb_suggestion.isChecked()
        }
        self.btn_start.setEnabled(False)
        self.btn_start.setText("校稿中...")
        self.signal_start_proofread.emit(scope, options)
        
    def finish_proofreading(self):
        self.btn_start.setEnabled(True)
        self.btn_start.setText("開始校稿")
        
    def load_results(self, results: list):
        """重新載入並顯示所有校稿結果"""
        self.table_typo.setRowCount(0)
        self.table_usage.setRowCount(0)
        self.table_suggestion.setRowCount(0)
        
        for res in results:
            cat = res.get("category", "typo")
            table = getattr(self, f"table_{cat}", None)
            if not table:
                continue
                
            row = table.rowCount()
            table.insertRow(row)
            
            # 狀態
            status_item = QTableWidgetItem(res.get("status", "pending"))
            # 章節
            chapter_item = QTableWidgetItem(res.get("chapter_name", ""))
            # 原文
            orig_item = QTableWidgetItem(res.get("original_text", ""))
            # 建議
            sugg_item = QTableWidgetItem(res.get("suggestion", ""))
            # 理由
            reason_item = QTableWidgetItem(res.get("reason", ""))
            
            # 將資料綁定到章節欄位（方便導航）
            chapter_item.setData(Qt.ItemDataRole.UserRole, {
                "node_id": res.get("node_id"),
                "char_offset": res.get("char_offset"),
                "match_len": res.get("match_len"),
                "result_id": res.get("id"),
                "original_text": res.get("original_text"),
                "category": cat
            })
            
            table.setItem(row, 0, status_item)
            table.setItem(row, 1, chapter_item)
            table.setItem(row, 2, orig_item)
            table.setItem(row, 3, sugg_item)
            table.setItem(row, 4, reason_item)
            
            # 操作按鈕群組
            action_widget = QWidget()
            h_layout = QHBoxLayout(action_widget)
            h_layout.setContentsMargins(2, 2, 2, 2)
            h_layout.setSpacing(4)
            
            btn_done = QPushButton("完成")
            btn_ignore = QPushButton("忽略")
            btn_delete = QPushButton("刪除")
            
            btn_done.clicked.connect(lambda checked, rid=res.get("id"): self.signal_change_status.emit(rid, "done"))
            btn_delete.clicked.connect(lambda checked, rid=res.get("id"): self.signal_change_status.emit(rid, "deleted"))
            btn_ignore.clicked.connect(lambda checked, rid=res.get("id"), word=res.get("original_text"), c=cat: self.handle_ignore_clicked(rid, word, c))
            
            h_layout.addWidget(btn_done)
            h_layout.addWidget(btn_ignore)
            h_layout.addWidget(btn_delete)
            
            table.setCellWidget(row, 5, action_widget)
            
    def handle_ignore_clicked(self, result_id: str, original_text: str, category: str):
        self.signal_ignore_rule.emit(category, original_text, result_id)

    def on_item_double_clicked(self, item: QTableWidgetItem, category: str):
        table = getattr(self, f"table_{category}")
        # 永遠取得同一列的「章節」欄位 (欄位索引 1)，因為我們把 data 存在那裡
        chapter_item = table.item(item.row(), 1)
        if not chapter_item:
            return
            
        data = chapter_item.data(Qt.ItemDataRole.UserRole)
        if data:
            self.signal_navigate_to_match.emit(
                data["node_id"], 
                data["char_offset"], 
                data["match_len"]
            )
