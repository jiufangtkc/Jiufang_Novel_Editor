import html
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QWidget, QFrame, QCheckBox, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QKeySequence, QShortcut, QTextCursor
from services.ai_service import AIService, AIChatWorker
from utils.font_manager import FontManager


class AIChatInputEdit(QTextEdit):
    """自訂對話輸入框：支援 Ctrl+Enter 發送、Shift+Enter 換行與強制無格式貼上"""
    signal_send_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptRichText(False)

    def insertFromMimeData(self, source):
        if source.hasText():
            self.insertPlainText(source.text())
        else:
            super().insertFromMimeData(source)

    def keyPressEvent(self, event):
        modifiers = event.modifiers()
        key = event.key()

        if (key in (Qt.Key.Key_Return, Qt.Key.Key_Enter)) and (modifiers == Qt.KeyboardModifier.ControlModifier):
            self.signal_send_requested.emit()
            event.accept()
            return

        super().keyPressEvent(event)


class AIChatDialog(QDialog):
    """AI 多輪對話對話框"""
    signal_insert_to_editor = pyqtSignal(str)
    signal_save_as_card = pyqtSignal(str, str)  # (title, content)

    def __init__(self, parent=None, initial_context: str = ""):
        super().__init__(parent)
        self.main_window = parent
        self.initial_context = initial_context.strip()
        self.messages = []  # list of {"role": "user"|"assistant", "content": str}
        self.worker = None
        self.last_assistant_reply = ""

        self.setWindowTitle("✨ AI 對話助手")
        self.scale_factor = getattr(parent, "scale_factor", 1.0) if parent else 1.0
        self.resize(int(720 * self.scale_factor), int(680 * self.scale_factor))
        self.setMinimumSize(int(540 * self.scale_factor), int(480 * self.scale_factor))
        if parent:
            self.setStyleSheet(parent.styleSheet())

        self._init_ui()
        self._load_provider_info()

        # 快速鍵
        QShortcut(QKeySequence("Ctrl+Return"), self, self._on_send_clicked)
        QShortcut(QKeySequence("Ctrl+Enter"), self, self._on_send_clicked)

    def _init_ui(self):
        sf = self.scale_factor
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(int(10 * sf))
        main_layout.setContentsMargins(int(12 * sf), int(12 * sf), int(12 * sf), int(12 * sf))

        # 頂部狀態列
        top_bar = QHBoxLayout()
        self.lbl_provider_info = QLabel("✨ AI 對話助手")
        self.lbl_provider_info.setFont(FontManager.get_font(size=int(10 * sf), weight=QFont.Weight.Bold))
        top_bar.addWidget(self.lbl_provider_info, 1)

        self.btn_clear = QPushButton("🗑️ 清空對話")
        self.btn_clear.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_clear.clicked.connect(self._clear_chat)
        top_bar.addWidget(self.btn_clear)

        main_layout.addLayout(top_bar)

        # 上下文區域（若有傳入 initial_context）
        if self.initial_context:
            ctx_frame = QFrame()
            ctx_frame.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); border: 1px dashed #555; border-radius: 4px; padding: 6px;")
            ctx_layout = QVBoxLayout(ctx_frame)
            ctx_layout.setContentsMargins(6, 4, 6, 4)
            ctx_layout.setSpacing(4)

            self.chk_include_context = QCheckBox("📌 附帶引用上下文（選取的文本）")
            self.chk_include_context.setChecked(True)
            self.chk_include_context.setFont(FontManager.get_font(size=int(9 * sf), weight=QFont.Weight.Bold))
            ctx_layout.addWidget(self.chk_include_context)

            self.lbl_context_preview = QLabel(self.initial_context[:200] + ("..." if len(self.initial_context) > 200 else ""))
            self.lbl_context_preview.setFont(FontManager.get_font(size=int(9 * sf)))
            self.lbl_context_preview.setStyleSheet("color: #aaaaaa;")
            self.lbl_context_preview.setWordWrap(True)
            ctx_layout.addWidget(self.lbl_context_preview)

            main_layout.addWidget(ctx_frame)
        else:
            self.chk_include_context = None

        # 對話紀錄顯示區 (HTML/Markdown 呈現)
        self.chat_history_edit = QTextEdit()
        self.chat_history_edit.setReadOnly(True)
        self.chat_history_edit.setFont(FontManager.get_font(size=int(10 * sf)))
        self.chat_history_edit.setStyleSheet("background-color: rgba(0, 0, 0, 0.2); border: 1px solid #444; border-radius: 6px; padding: 8px;")
        main_layout.addWidget(self.chat_history_edit, 1)

        # 初始歡迎文字
        self._append_system_message("你好！我是你的 AI 寫作助手。你可以隨時向我提問劇情、角色設定、修辭潤飾或故事構想。")

        # 輸入區
        input_container = QVBoxLayout()
        input_container.setSpacing(int(6 * sf))

        self.input_edit = AIChatInputEdit()
        self.input_edit.setFont(FontManager.get_font(size=int(10 * sf)))
        self.input_edit.setPlaceholderText("輸入訊息或寫作問題... (按 Ctrl+Enter 發送)")
        self.input_edit.setMaximumHeight(int(90 * sf))
        self.input_edit.signal_send_requested.connect(self._on_send_clicked)
        input_container.addWidget(self.input_edit)

        # 按鈕列
        btn_layout = QHBoxLayout()
        self.lbl_status = QLabel("")
        self.lbl_status.setFont(FontManager.get_font(size=int(9 * sf)))
        self.lbl_status.setStyleSheet("color: #ffa500;")
        btn_layout.addWidget(self.lbl_status, 1)

        self.btn_insert = QPushButton("📝 插入編輯器")
        self.btn_insert.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_insert.setToolTip("將最新回覆插入至當前章節編輯器")
        self.btn_insert.setEnabled(False)
        self.btn_insert.clicked.connect(self._insert_to_editor)
        btn_layout.addWidget(self.btn_insert)

        self.btn_save_card = QPushButton("🃏 存為卡片")
        self.btn_save_card.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_save_card.setToolTip("將最新回覆新增為資料集卡片")
        self.btn_save_card.setEnabled(False)
        self.btn_save_card.clicked.connect(self._save_as_card)
        btn_layout.addWidget(self.btn_save_card)

        self.btn_copy = QPushButton("📋 複製回覆")
        self.btn_copy.setFont(FontManager.get_font(size=int(9 * sf)))
        self.btn_copy.setToolTip("複製最新 AI 回覆內容")
        self.btn_copy.setEnabled(False)
        self.btn_copy.clicked.connect(self._copy_last_reply)
        btn_layout.addWidget(self.btn_copy)

        self.btn_send = QPushButton("發送 (Ctrl+Enter)")
        self.btn_send.setFont(FontManager.get_font(size=int(9 * sf), weight=QFont.Weight.Bold))
        self.btn_send.setDefault(True)
        self.btn_send.clicked.connect(self._on_send_clicked)
        btn_layout.addWidget(self.btn_send)

        input_container.addLayout(btn_layout)
        main_layout.addLayout(input_container)

    def _load_provider_info(self):
        settings = AIService.load_settings()
        provider = settings.get("provider", "Google")
        model = settings.get("models", {}).get(provider, "")
        self.lbl_provider_info.setText(f"✨ AI 對話助手 — {provider} ({model})")

    def _append_system_message(self, text: str):
        safe_text = html.escape(text).replace("\n", "<br>")
        msg_html = f"<div style='margin: 6px 0; color: #888888; font-style: italic; font-size: 11px;'>🤖 {safe_text}</div>"
        self.chat_history_edit.append(msg_html)

    def _append_user_message(self, text: str):
        safe_text = html.escape(text).replace("\n", "<br>")
        msg_html = f"""
        <div style='margin: 10px 0; text-align: right;'>
            <div style='display: inline-block; background-color: #2b5278; color: #ffffff; padding: 8px 12px; border-radius: 8px; max-width: 80%; text-align: left;'>
                <b>你：</b><br>{safe_text}
            </div>
        </div>
        """
        self.chat_history_edit.append(msg_html)

    def _append_assistant_message(self, text: str):
        safe_text = html.escape(text).replace("\n", "<br>")
        msg_html = f"""
        <div style='margin: 10px 0; text-align: left;'>
            <div style='display: inline-block; background-color: #2d3136; color: #e0e0e0; border: 1px solid #444; padding: 8px 12px; border-radius: 8px; max-width: 90%;'>
                <b style='color: #4CAF50;'>AI 助手：</b><br>{safe_text}
            </div>
        </div>
        """
        self.chat_history_edit.append(msg_html)

    def _on_send_clicked(self):
        user_input = self.input_edit.toPlainText().strip()
        if not user_input:
            return

        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "提示", "AI 正在回應中，請稍候...")
            return

        self._append_user_message(user_input)
        self.input_edit.clear()

        # 組裝 messages
        if not self.messages and self.initial_context and getattr(self, "chk_include_context", None) and self.chk_include_context.isChecked():
            first_user_content = f"【參考上下文】\n{self.initial_context}\n\n【提問】\n{user_input}"
            self.messages.append({"role": "user", "content": first_user_content})
        else:
            self.messages.append({"role": "user", "content": user_input})

        self.btn_send.setEnabled(False)
        self.lbl_status.setText("✨ AI 正在思考中...")

        self.worker = AIChatWorker(self.messages)
        self.worker.finished_signal.connect(self._on_worker_finished)
        self.worker.error_signal.connect(self._on_worker_error)
        self.worker.start()

    def _on_worker_finished(self, reply_text: str):
        self.lbl_status.setText("")
        self.btn_send.setEnabled(True)
        self.last_assistant_reply = reply_text
        self.messages.append({"role": "assistant", "content": reply_text})

        self._append_assistant_message(reply_text)

        self.btn_copy.setEnabled(True)
        self.btn_insert.setEnabled(True)
        self.btn_save_card.setEnabled(True)

    def _on_worker_error(self, err_msg: str):
        self.lbl_status.setText("❌ 回應失敗")
        self.btn_send.setEnabled(True)
        self._append_system_message(f"發生錯誤：{err_msg}")
        QMessageBox.critical(self, "AI 回應失敗", f"連線或生成失敗：\n{err_msg}")

    def _clear_chat(self):
        reply = QMessageBox.question(self, "清空確認", "確定要清空當前對話紀錄嗎？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.messages.clear()
            self.chat_history_edit.clear()
            self.last_assistant_reply = ""
            self.btn_copy.setEnabled(False)
            self.btn_insert.setEnabled(False)
            self.btn_save_card.setEnabled(False)
            self._append_system_message("對話已清空。")

    def _copy_last_reply(self):
        if self.last_assistant_reply:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.last_assistant_reply)
            self.lbl_status.setText("✅ 已複製到剪貼簿")

    def _insert_to_editor(self):
        if self.last_assistant_reply:
            self.signal_insert_to_editor.emit(self.last_assistant_reply)
            self.lbl_status.setText("✅ 已插入編輯器")

    def _save_as_card(self):
        if self.last_assistant_reply:
            title = f"AI 對話摘要 ({len(self.messages)//2}輪)"
            self.signal_save_as_card.emit(title, self.last_assistant_reply)
            self.lbl_status.setText("✅ 已儲存至資料卡片")
