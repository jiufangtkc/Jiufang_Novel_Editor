from views.common.base_dialog import BaseDialog
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
    QLineEdit, QPushButton, QLabel,
    QMessageBox, QDialogButtonBox, QSpinBox, QMenu
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from services.ai_service import AIService
from services.ai_settings_service import DEFAULT_SETTINGS
from utils.font_manager import FontManager


class TestConnectionWorker(QThread):
    result_signal = pyqtSignal(bool, str)

    def __init__(self, provider, api_url, api_key="", model="", timeout=90):
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


class AISettingsDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI 助手設定")
        self.resize(int(520 * self.scale_factor), int(380 * self.scale_factor))
        self.setFont(FontManager.get_font(size=int(9 * self.scale_factor)))
        self.setModal(True)
        if parent:
            self.setStyleSheet(parent.styleSheet())

        self.settings = AIService.load_settings()
        self.test_worker = None
        self.detect_worker = None

        self._init_ui()
        self._load_values()

    def _init_ui(self):
        sf = self.scale_factor
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(int(14 * sf))

        # Provider 選擇
        header_layout = QHBoxLayout()
        lbl_provider = QLabel("本機 AI 服務供應商 (Provider):")
        lbl_provider.setFont(FontManager.get_font(size=int(9 * sf), weight=QFont.Weight.Bold))
        self.combo_provider = QComboBox()
        self.combo_provider.addItems(["Ollama", "LM Studio"])
        self.combo_provider.currentTextChanged.connect(self._on_provider_changed)
        header_layout.addWidget(lbl_provider)
        header_layout.addWidget(self.combo_provider, 1)
        main_layout.addLayout(header_layout)

        # 基本連線與模型表單
        basic_layout = QFormLayout()
        basic_layout.setContentsMargins(10, 10, 10, 10)
        basic_layout.setSpacing(12)

        self.input_url = QLineEdit()

        # 模型名稱 + 本地模型自動偵測按鈕
        model_layout = QHBoxLayout()
        self.input_model = QLineEdit()
        model_layout.addWidget(self.input_model, 1)
        self.btn_detect_models = QPushButton("偵測本機模型")
        self.btn_detect_models.setToolTip("向 Ollama / LM Studio 查詢目前已下載或載入之可用模型清單")
        self.btn_detect_models.clicked.connect(self._detect_local_models)
        model_layout.addWidget(self.btn_detect_models)

        # Context 上限設定
        self.spin_context_limit = QSpinBox()
        self.spin_context_limit.setRange(1024, 2097152)  # 1,024 至 2,097,152 Tokens
        self.spin_context_limit.setSingleStep(1024)
        self.spin_context_limit.setValue(8192)
        self.spin_context_limit.setSuffix(" Tokens")
        self.spin_context_limit.setToolTip("設定目前 AI 服務之上下文長度 (Context Limit)。本機模型偵測時可自動同步；亦可在此手動調整。")

        ctx_layout = QHBoxLayout()
        ctx_layout.addWidget(self.spin_context_limit)
        self.lbl_ctx_hint = QLabel("(本機模型偵測時可自動同步)")
        self.lbl_ctx_hint.setStyleSheet("color: #a0aec0; font-size: 11px;")
        ctx_layout.addWidget(self.lbl_ctx_hint)
        ctx_layout.addStretch(1)

        # 逾時時間設定
        self.spin_timeout = QSpinBox()
        self.spin_timeout.setRange(10, 28800)  # 10 秒至 8 小時
        self.spin_timeout.setSingleStep(30)
        self.spin_timeout.setValue(300)
        self.spin_timeout.setSuffix(" 秒")
        self.spin_timeout.setToolTip("設定等待 AI 回應的最長逾時時間（預設 300 秒 / 5 分鐘，上限 28800 秒 / 8 小時）。適用於本地慢速模型或思考型模型。")

        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(self.spin_timeout)
        lbl_timeout_hint = QLabel("(預設 300 秒 / 5 分鐘，上限 8 小時)")
        lbl_timeout_hint.setStyleSheet("color: #a0aec0; font-size: 11px;")
        timeout_layout.addWidget(lbl_timeout_hint)
        timeout_layout.addStretch(1)

        basic_layout.addRow("API 端點網址:", self.input_url)
        basic_layout.addRow("模型名稱 (Model):", model_layout)
        basic_layout.addRow("Context 上限:", ctx_layout)
        basic_layout.addRow("請求逾時上限:", timeout_layout)

        # 連線測試按鈕與狀態標籤
        test_layout = QHBoxLayout()
        self.btn_test = QPushButton("測試連線")
        self.btn_test.clicked.connect(self._test_connection)
        self.lbl_test_status = QLabel("")
        self.lbl_test_status.setStyleSheet("color: #a0aec0; font-size: 11px;")
        test_layout.addWidget(self.btn_test)
        test_layout.addWidget(self.lbl_test_status, 1)
        basic_layout.addRow("", test_layout)

        main_layout.addLayout(basic_layout)
        main_layout.addStretch(1)

        # 底部按鈕
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self._save_and_accept)
        btn_box.rejected.connect(self.reject)
        main_layout.addWidget(btn_box)

    def _load_values(self):
        cur_provider = self.settings.get("provider", "Ollama")
        if cur_provider not in ("Ollama", "LM Studio"):
            cur_provider = "Ollama"
        self.combo_provider.setCurrentText(cur_provider)
        self._load_provider_fields(cur_provider)

        timeout_val = int(self.settings.get("timeout", 300))
        self.spin_timeout.setValue(max(10, min(28800, timeout_val)))

    def _load_provider_fields(self, provider):
        urls = self.settings.get("api_urls", {})
        models = self.settings.get("models", {})

        default_url = DEFAULT_SETTINGS.get("api_urls", {}).get(provider, "")
        self.input_url.setText(urls.get(provider, default_url))
        self.input_model.setText(models.get(provider, ""))
        self.btn_detect_models.setEnabled(True)

        context_limits = self.settings.get("context_limits", {})
        default_ctx = DEFAULT_SETTINGS.get("context_limits", {}).get(provider, 8192)
        self.spin_context_limit.setValue(int(context_limits.get(provider, default_ctx)))

    def _save_current_provider_fields(self, provider):
        if "api_urls" not in self.settings:
            self.settings["api_urls"] = {}
        if "models" not in self.settings:
            self.settings["models"] = {}
        if "context_limits" not in self.settings:
            self.settings["context_limits"] = {}

        self.settings["api_urls"][provider] = self.input_url.text().strip()
        self.settings["models"][provider] = self.input_model.text().strip()
        self.settings["context_limits"][provider] = self.spin_context_limit.value()

    def _on_provider_changed(self, new_provider):
        self._load_provider_fields(new_provider)
        self.lbl_test_status.setText("")

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
        self.btn_detect_models.setText("偵測本機模型")

        if err:
            QMessageBox.warning(self, "偵測失敗", f"向本地端點查詢模型失敗：\n{err}")
            return

        if not models:
            QMessageBox.information(self, "未找到模型", "端點已回應，但未發現任何已載入或已下載之可用模型。")
            return

        provider = self.combo_provider.currentText()
        url = self.input_url.text().strip()

        def _update_model_and_context(name: str):
            self.input_model.setText(name)
            ctx = AIService.fetch_context_limit(provider, url, name)
            if ctx:
                self.spin_context_limit.setValue(ctx)
                self.lbl_ctx_hint.setText(f"(已同步 Context: {ctx:,})")

        if len(models) == 1:
            _update_model_and_context(models[0])
            QMessageBox.information(self, "偵測成功", f"已成功偵測並填入模型：{models[0]}")
        else:
            menu = QMenu(self)
            for m in models:
                act = menu.addAction(m)
                act.triggered.connect(lambda checked=False, name=m: _update_model_and_context(name))
            if models:
                _update_model_and_context(models[0])
            menu.exec(self.btn_detect_models.mapToGlobal(self.btn_detect_models.rect().bottomLeft()))

    def _test_connection(self):
        provider = self.combo_provider.currentText()
        url = self.input_url.text().strip()
        model = self.input_model.text().strip()
        timeout = self.spin_timeout.value()

        if not url:
            QMessageBox.warning(self, "警告", "請先輸入 API 端點網址！")
            return

        self.btn_test.setEnabled(False)
        self.lbl_test_status.setStyleSheet("color: #ffa500; font-size: 11px;")
        self.lbl_test_status.setText("連線測試中...")

        key = self.settings.get("api_keys", {}).get(provider, "")
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
        self._save_current_provider_fields(current_provider)
        AIService.save_settings(self.settings)
        self.accept()
