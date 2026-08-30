from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
    QLineEdit, QTextEdit, QPushButton, QLabel, QTabWidget,
    QWidget, QMessageBox, QDialogButtonBox, QSpinBox, QCheckBox,
    QGroupBox, QMenu
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from services.ai_service import AIService
from utils.font_manager import FontManager


class TestConnectionWorker(QThread):
    result_signal = pyqtSignal(bool, str)

    def __init__(self, provider, api_url, api_key, model, timeout=90):
        super().__init__()
        self.provider = provider
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def run(self):
        try:
            res = AIService.test_connection(
                self.provider, self.api_url, self.api_key, self.model, timeout=self.timeout
            )
            self.result_signal.emit(True, f"連線成功！回應：{res[:100]}")
        except Exception as e:
            self.result_signal.emit(False, str(e))


class DetectModelsWorker(QThread):
    result_signal = pyqtSignal(list, str)

    def __init__(self, provider, api_url):
        super().__init__()
        self.provider = provider
        self.api_url = api_url

    def run(self):
        try:
            models = AIService.detect_local_models(self.provider, self.api_url)
            self.result_signal.emit(models, "")
        except Exception as e:
            self.result_signal.emit([], str(e))


class AISettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI 助手設定")
        self.resize(580, 580)
        self.setModal(True)
        if parent:
            self.setStyleSheet(parent.styleSheet())

        self.settings = AIService.load_settings()
        self.test_worker = None
        self.detect_worker = None

        self._init_ui()
        self._load_values()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        # Provider 選擇
        header_layout = QHBoxLayout()
        lbl_provider = QLabel("AI 服務供應商 (Provider):")
        lbl_provider.setFont(FontManager.get_font(size=9, weight=QFont.Weight.Bold))
        self.combo_provider = QComboBox()
        self.combo_provider.addItems(["OpenAI", "Google", "Anthropic", "Grok", "Ollama", "LM Studio"])
        self.combo_provider.currentTextChanged.connect(self._on_provider_changed)
        header_layout.addWidget(lbl_provider)
        header_layout.addWidget(self.combo_provider, 1)
        main_layout.addLayout(header_layout)

        # Tab Widget 分頁：基本設定 / 續寫設定 / 提示詞 (Prompts)
        self.tabs = QTabWidget()

        # Tab 1: 連線與模型
        tab_basic = QWidget()
        basic_layout = QFormLayout(tab_basic)
        basic_layout.setContentsMargins(10, 15, 10, 10)
        basic_layout.setSpacing(10)

        self.input_url = QLineEdit()
        self.input_key = QLineEdit()
        self.input_key.setEchoMode(QLineEdit.EchoMode.Password)

        # 顯示/隱藏密碼按鈕
        key_layout = QHBoxLayout()
        key_layout.addWidget(self.input_key, 1)
        self.btn_toggle_key = QPushButton("👁️")
        self.btn_toggle_key.setFixedWidth(30)
        self.btn_toggle_key.setToolTip("顯示/隱藏 API Key")
        self.btn_toggle_key.clicked.connect(self._toggle_key_visibility)
        key_layout.addWidget(self.btn_toggle_key)

        # 模型名稱 + 本地模型自動偵測按鈕
        model_layout = QHBoxLayout()
        self.input_model = QLineEdit()
        model_layout.addWidget(self.input_model, 1)
        self.btn_detect_models = QPushButton("🔍 偵測本機模型")
        self.btn_detect_models.setToolTip("向 Ollama / LM Studio 查詢目前已下載或載入之可用模型清單")
        self.btn_detect_models.clicked.connect(self._detect_local_models)
        model_layout.addWidget(self.btn_detect_models)

        # 逾時時間設定
        self.spin_timeout = QSpinBox()
        self.spin_timeout.setRange(10, 28800)  # 10 秒至 8 小時 (28800 秒)
        self.spin_timeout.setSingleStep(30)
        self.spin_timeout.setValue(300)
        self.spin_timeout.setSuffix(" 秒")
        self.spin_timeout.setToolTip("設定等待 AI 回應的最長逾時時間（預設 300 秒 / 5 分鐘，上限 28800 秒 / 8 小時）。適用於本地慢速模型或思考型模型。")

        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(self.spin_timeout)
        lbl_timeout_hint = QLabel("(預設 300 秒 / 5 分鐘，上限 8 小時)")
        lbl_timeout_hint.setStyleSheet("color: #888888; font-size: 11px;")
        timeout_layout.addWidget(lbl_timeout_hint)
        timeout_layout.addStretch(1)

        basic_layout.addRow("API 端點網址:", self.input_url)
        basic_layout.addRow("API 金鑰 (Key):", key_layout)
        basic_layout.addRow("模型名稱 (Model):", model_layout)
        basic_layout.addRow("請求逾時上限:", timeout_layout)

        # 連線測試按鈕與狀態標籤
        test_layout = QHBoxLayout()
        self.btn_test = QPushButton("測試連線")
        self.btn_test.clicked.connect(self._test_connection)
        self.lbl_test_status = QLabel("")
        self.lbl_test_status.setStyleSheet("color: #888888; font-size: 11px;")
        test_layout.addWidget(self.btn_test)
        test_layout.addWidget(self.lbl_test_status, 1)
        basic_layout.addRow("", test_layout)

        self.tabs.addTab(tab_basic, "連線與模型")

        # Tab 2: AI 智慧擴寫安全機制
        tab_continuation = QWidget()
        continuation_layout = QVBoxLayout(tab_continuation)
        continuation_layout.setContentsMargins(15, 15, 15, 15)
        continuation_layout.setSpacing(12)

        box_continuation = QGroupBox("AI 智慧擴寫安全開關")
        box_layout = QVBoxLayout(box_continuation)
        box_layout.setSpacing(8)

        self.chk_continuation = QCheckBox("啟用 AI 智慧擴寫功能（預設關閉）")
        self.chk_continuation.setFont(FontManager.get_font(size=9, weight=QFont.Weight.Bold))
        self.chk_continuation.clicked.connect(self._on_continuation_clicked)
        box_layout.addWidget(self.chk_continuation)

        lbl_desc = QLabel(
            "【創作者自主性防護說明】\n"
            "AI 智慧擴寫可根據您提供的前後文與擴寫指引自動生成小說段落。\n"
            "首次啟用時需確認閱讀心流影響警告。您亦可隨時在設定中關閉本功能。"
        )
        lbl_desc.setStyleSheet("color: #888888; font-size: 11px; line-height: 1.4;")
        lbl_desc.setWordWrap(True)
        box_layout.addWidget(lbl_desc)

        continuation_layout.addWidget(box_continuation)
        continuation_layout.addStretch(1)
        self.tabs.addTab(tab_continuation, "AI 智慧擴寫")

        # Tab 3: 提示詞自訂
        tab_prompts = QWidget()
        prompts_layout = QVBoxLayout(tab_prompts)
        prompts_layout.setContentsMargins(10, 10, 10, 10)

        self.prompt_tabs = QTabWidget()
        self.prompt_inputs = {}
        prompt_names = [
            ("impression", "評語建議"),
            ("character", "角色提取"),
            ("world", "世界觀提取"),
            ("timeline", "時間軸梳理"),
            ("chat", "多輪對話"),
            ("continuation", "小說擴寫")
        ]
        for key, title in prompt_names:
            txt = QTextEdit()
            self.prompt_inputs[key] = txt
            self.prompt_tabs.addTab(txt, title)

        prompts_layout.addWidget(self.prompt_tabs)
        self.tabs.addTab(tab_prompts, "自訂系統提示詞")

        main_layout.addWidget(self.tabs)

        # 底部按鈕
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self._save_and_accept)
        btn_box.rejected.connect(self.reject)
        main_layout.addWidget(btn_box)

    def _toggle_key_visibility(self):
        if self.input_key.echoMode() == QLineEdit.EchoMode.Password:
            self.input_key.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.input_key.setEchoMode(QLineEdit.EchoMode.Password)

    def _load_values(self):
        cur_provider = self.settings.get("provider", "Google")
        self.combo_provider.setCurrentText(cur_provider)
        self._load_provider_fields(cur_provider)

        timeout_val = int(self.settings.get("timeout", 300))
        self.spin_timeout.setValue(max(10, min(28800, timeout_val)))

        # 載入續寫開關狀態
        self.chk_continuation.setChecked(self.settings.get("ai_continuation_enabled", False))

        prompts = self.settings.get("prompts", {})
        for k, edit in self.prompt_inputs.items():
            edit.setPlainText(prompts.get(k, ""))

    def _load_provider_fields(self, provider):
        urls = self.settings.get("api_urls", {})
        keys = self.settings.get("api_keys", {})
        models = self.settings.get("models", {})

        self.input_url.setText(urls.get(provider, ""))
        self.input_key.setText(keys.get(provider, ""))
        self.input_model.setText(models.get(provider, ""))

        if provider in ("Ollama", "LM Studio"):
            self.input_key.setPlaceholderText("本地模型無需 API Key")
            self.btn_detect_models.setEnabled(True)
        else:
            self.input_key.setPlaceholderText("請輸入 API Key")
            self.btn_detect_models.setEnabled(False)

    def _save_current_provider_fields(self, provider):
        if "api_urls" not in self.settings:
            self.settings["api_urls"] = {}
        if "api_keys" not in self.settings:
            self.settings["api_keys"] = {}
        if "models" not in self.settings:
            self.settings["models"] = {}

        self.settings["api_urls"][provider] = self.input_url.text().strip()
        self.settings["api_keys"][provider] = self.input_key.text().strip()
        self.settings["models"][provider] = self.input_model.text().strip()

    def _on_provider_changed(self, new_provider):
        self._load_provider_fields(new_provider)
        self.lbl_test_status.setText("")

    def _on_continuation_clicked(self, checked):
        if checked:
            if not self.settings.get("ai_continuation_agreed", False):
                # 彈出警告確認
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setWindowTitle("AI 擴寫功能啟用確認")
                msg_box.setText(
                    "本功能將大幅改變寫作心流，同時也可能部分或完全剝奪創作的自主性與獨特性。\n\n"
                    "請在完全理解並同意接受這種影響的狀況下，才開啟本功能。"
                )
                btn_agree = msg_box.addButton("我了解風險，確認開啟", QMessageBox.ButtonRole.AcceptRole)
                btn_cancel = msg_box.addButton("取消", QMessageBox.ButtonRole.RejectRole)
                msg_box.setDefaultButton(btn_cancel)
                msg_box.exec()

                if msg_box.clickedButton() == btn_agree:
                    self.settings["ai_continuation_agreed"] = True
                    self.chk_continuation.setChecked(True)
                else:
                    self.chk_continuation.setChecked(False)
        else:
            self.chk_continuation.setChecked(False)

    def _detect_local_models(self):
        provider = self.combo_provider.currentText()
        url = self.input_url.text().strip()
        if not url:
            QMessageBox.warning(self, "提示", "請先填寫端點網址再進行偵測。")
            return

        self.btn_detect_models.setEnabled(False)
        self.btn_detect_models.setText("偵測中...")

        self.detect_worker = DetectModelsWorker(provider, url)
        self.detect_worker.result_signal.connect(self._on_detect_finished)
        self.detect_worker.start()

    def _on_detect_finished(self, models: list, err: str):
        self.btn_detect_models.setEnabled(True)
        self.btn_detect_models.setText("🔍 偵測本機模型")

        if err:
            QMessageBox.warning(self, "偵測失敗", f"向本地端點查詢模型失敗：\n{err}")
            return

        if not models:
            QMessageBox.information(self, "未找到模型", "端點已回應，但未發現任何已載入或已下載之可用模型。")
            return

        if len(models) == 1:
            self.input_model.setText(models[0])
            QMessageBox.information(self, "偵測成功", f"已成功偵測並填入模型：{models[0]}")
        else:
            # 建立選擇選單
            menu = QMenu(self)
            for m in models:
                act = menu.addAction(m)
                act.triggered.connect(lambda checked=False, name=m: self.input_model.setText(name))
            menu.exec(self.btn_detect_models.mapToGlobal(self.btn_detect_models.rect().bottomLeft()))

    def _test_connection(self):
        provider = self.combo_provider.currentText()
        url = self.input_url.text().strip()
        key = self.input_key.text().strip()
        model = self.input_model.text().strip()
        timeout = self.spin_timeout.value()

        if not url:
            QMessageBox.warning(self, "警告", "請先輸入 API 端點網址！")
            return

        self.btn_test.setEnabled(False)
        self.lbl_test_status.setStyleSheet("color: #ffa500; font-size: 11px;")
        self.lbl_test_status.setText("連線測試中...")

        self.test_worker = TestConnectionWorker(provider, url, key, model, timeout=timeout)
        self.test_worker.result_signal.connect(self._on_test_finished)
        self.test_worker.start()

    def _on_test_finished(self, success, message):
        self.btn_test.setEnabled(True)
        if success:
            self.lbl_test_status.setStyleSheet("color: #4CAF50; font-size: 11px;")
            self.lbl_test_status.setText("連線成功！")
            QMessageBox.information(self, "連線測試成功", message)
        else:
            self.lbl_test_status.setStyleSheet("color: #F44336; font-size: 11px;")
            self.lbl_test_status.setText("連線失敗")
            QMessageBox.critical(self, "連線測試失敗", f"無法連線至 AI 服務：\n{message}")

    def _save_and_accept(self):
        current_provider = self.combo_provider.currentText()
        self.settings["provider"] = current_provider
        self.settings["timeout"] = self.spin_timeout.value()
        self.settings["ai_continuation_enabled"] = self.chk_continuation.isChecked()
        self._save_current_provider_fields(current_provider)

        if "prompts" not in self.settings:
            self.settings["prompts"] = {}
        for k, edit in self.prompt_inputs.items():
            self.settings["prompts"][k] = edit.toPlainText().strip()

        AIService.save_settings(self.settings)
        self.accept()
