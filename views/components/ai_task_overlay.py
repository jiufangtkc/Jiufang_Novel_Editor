from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton, QApplication
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from utils.font_manager import FontManager


class AITaskOverlay(QWidget):
    """
    非強制佔用的浮動視窗，用來顯示 AI 任務狀態與流式輸出。
    """
    signal_insert_text = pyqtSignal(str)

    def __init__(self, parent=None, title="AI 工作狀態"):
        # 使用 Window 屬性讓它可以浮動，但保留父視窗關聯以便跟隨關閉
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle(title)
        self.resize(400, 500)
        
        # 若有 parent，複製其 stylesheet 以保持風格
        if parent:
            self.setStyleSheet(parent.styleSheet())

        self.elapsed_seconds = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_timer)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 狀態區
        status_layout = QHBoxLayout()
        self.lbl_status = QLabel("🔵 準備中...")
        self.lbl_status.setFont(FontManager.get_font(size=10, weight=FontManager.QFont.Weight.Bold))
        
        self.lbl_time = QLabel("00:00:00")
        self.lbl_time.setFont(FontManager.get_font(size=10))
        self.lbl_time.setStyleSheet("color: #888888;")
        
        status_layout.addWidget(self.lbl_status)
        status_layout.addStretch(1)
        status_layout.addWidget(self.lbl_time)
        
        layout.addLayout(status_layout)

        # 輸出顯示區
        self.text_output = QTextEdit()
        self.text_output.setReadOnly(True)
        self.text_output.setPlaceholderText("等待 AI 回應中...")
        layout.addWidget(self.text_output)

        # 底部操作區
        bottom_layout = QHBoxLayout()
        
        self.btn_insert = QPushButton("📥 插入至游標處")
        self.btn_insert.setEnabled(False)
        self.btn_insert.clicked.connect(self._on_insert)
        
        self.btn_copy = QPushButton("📋 複製全文")
        self.btn_copy.setEnabled(False)
        self.btn_copy.clicked.connect(self._on_copy)
        
        self.btn_close = QPushButton("關閉")
        self.btn_close.clicked.connect(self.close)
        
        bottom_layout.addWidget(self.btn_insert)
        bottom_layout.addWidget(self.btn_copy)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(self.btn_close)
        
        layout.addLayout(bottom_layout)

    def _update_timer(self):
        self.elapsed_seconds += 1
        h = self.elapsed_seconds // 3600
        m = (self.elapsed_seconds % 3600) // 60
        s = self.elapsed_seconds % 60
        self.lbl_time.setText(f"{h:02d}:{m:02d}:{s:02d}")

    def start_task(self):
        self.elapsed_seconds = 0
        self.lbl_time.setText("00:00:00")
        self.timer.start(1000)
        self.set_status("understanding")
        self.text_output.clear()
        self.btn_insert.setEnabled(False)
        self.btn_copy.setEnabled(False)
        self.show()

    def set_status(self, status: str):
        if status == "understanding":
            self.lbl_status.setText("🧠 理解中...")
            self.lbl_status.setStyleSheet("color: #2196F3;")
        elif status == "thinking":
            self.lbl_status.setText("⏳ 思考中...")
            self.lbl_status.setStyleSheet("color: #FF9800;")
        elif status == "working":
            self.lbl_status.setText("✍️ 正在工作中...")
            self.lbl_status.setStyleSheet("color: #4CAF50;")
        elif status == "finished":
            self.lbl_status.setText("✅ 工作完成")
            self.lbl_status.setStyleSheet("color: #4CAF50;")
            self.timer.stop()
            if self.text_output.toPlainText().strip():
                self.btn_insert.setEnabled(True)
                self.btn_copy.setEnabled(True)
        elif status == "error":
            self.lbl_status.setText("❌ 發生錯誤")
            self.lbl_status.setStyleSheet("color: #F44336;")
            self.timer.stop()

    def append_chunk(self, chunk: str):
        # 將 scroll bar 移到底部並插入文字
        cursor = self.text_output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(chunk)
        self.text_output.setTextCursor(cursor)
        self.text_output.ensureCursorVisible()

    def finish_task(self):
        self.set_status("finished")

    def error_task(self, msg: str):
        self.set_status("error")
        self.append_chunk(f"\n\n【錯誤】\n{msg}")

    def _on_insert(self):
        text = self.text_output.toPlainText()
        if text:
            self.signal_insert_text.emit(text)

    def _on_copy(self):
        text = self.text_output.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
