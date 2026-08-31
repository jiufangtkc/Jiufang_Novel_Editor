from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QApplication, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt6.QtGui import QColor, QFont
from utils.font_manager import FontManager


class AIFloatingHUD(QWidget):
    """
    非強制佔用焦點的懸浮 AI 任務進度視窗 (Floating HUD)。
    在作家寫作或瀏覽章節時，無焦點地常駐在畫面角落，即時報告 AI 運算階段與秒數。
    """
    signal_cancel = pyqtSignal()

    def __init__(self, parent=None, title="✨ AI 正在工作中"):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.title_text = title
        self.elapsed_seconds = 0
        self.is_collapsed = False
        self._drag_pos = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_timer)

        self.init_ui()
        self.apply_style()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)

        # 核心 HUD 卡片容器
        self.hud_container = QWidget(self)
        self.hud_container.setObjectName("HUDContainer")
        container_layout = QVBoxLayout(self.hud_container)
        container_layout.setContentsMargins(12, 10, 12, 10)
        container_layout.setSpacing(8)

        # 1. 頂部標題與按鈕列 (支援拖曳)
        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)

        self.lbl_dot = QLabel("🟢")
        self.lbl_dot.setFont(FontManager.get_font(size=8))
        header_layout.addWidget(self.lbl_dot)

        self.lbl_title = QLabel(self.title_text)
        self.lbl_title.setFont(FontManager.get_font(size=9, weight=QFont.Weight.Bold))
        header_layout.addWidget(self.lbl_title, 1)

        self.lbl_time = QLabel("00:00")
        self.lbl_time.setFont(FontManager.get_font(size=8))
        self.lbl_time.setStyleSheet("color: #4fc1ff; font-weight: bold;")
        header_layout.addWidget(self.lbl_time)

        self.btn_toggle_collapse = QPushButton("–")
        self.btn_toggle_collapse.setFixedSize(18, 18)
        self.btn_toggle_collapse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_collapse.setToolTip("收折 / 展開")
        self.btn_toggle_collapse.clicked.connect(self.toggle_collapse)
        header_layout.addWidget(self.btn_toggle_collapse)

        self.btn_cancel = QPushButton("✕")
        self.btn_cancel.setFixedSize(18, 18)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setToolTip("取消此 AI 任務")
        self.btn_cancel.clicked.connect(self._on_cancel_clicked)
        header_layout.addWidget(self.btn_cancel)

        container_layout.addLayout(header_layout)

        # 2. 進度內容區 (可收折)
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 4, 0, 0)
        content_layout.setSpacing(6)

        # 階段文字
        self.lbl_status = QLabel("正在啟動背景任務...")
        self.lbl_status.setFont(FontManager.get_font(size=9))
        self.lbl_status.setWordWrap(True)
        content_layout.addWidget(self.lbl_status)

        # 進度條
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 0)  # 預設為 busy 循環模式
        content_layout.addWidget(self.progress_bar)

        container_layout.addWidget(self.content_widget)
        self.main_layout.addWidget(self.hud_container)

        # 添加陰影
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 4)
        self.hud_container.setGraphicsEffect(shadow)

        self.resize(320, 120)

    def apply_style(self):
        self.setStyleSheet("""
            QWidget#HUDContainer {
                background-color: rgba(26, 30, 38, 0.95);
                border: 1px solid #007acc;
                border-radius: 8px;
            }
            QLabel {
                color: #e3e3e3;
                background-color: transparent;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                color: #cccccc;
                border: 1px solid #3e4451;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #007acc;
                color: #ffffff;
                border-color: #4fc1ff;
            }
            QProgressBar {
                background-color: #21252b;
                border: 1px solid #3e4451;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0e639c, stop:1 #4fc1ff);
                border-radius: 2px;
            }
        """)

    def _update_timer(self):
        self.elapsed_seconds += 1
        m = self.elapsed_seconds // 60
        s = self.elapsed_seconds % 60
        self.lbl_time.setText(f"{m:02d}:{s:02d}")

    def start(self, task_name: str = "✨ AI 分析任務"):
        self.title_text = task_name
        self.lbl_title.setText(task_name)
        self.elapsed_seconds = 0
        self.lbl_time.setText("00:00")
        self.lbl_dot.setText("🟢")
        self.lbl_status.setText("🧠 理解文本中，請稍候...")
        self.progress_bar.setRange(0, 0)
        self.timer.start(1000)

        #  positioning: parent 右下角
        if self.parent():
            parent_geom = self.parent().geometry()
            x = parent_geom.x() + parent_geom.width() - self.width() - 20
            y = parent_geom.y() + parent_geom.height() - self.height() - 40
            self.move(max(20, x), max(20, y))

        self.show()

    def update_progress(self, current_step: int, total_steps: int, message: str):
        self.lbl_status.setText(message)
        if total_steps > 1:
            self.progress_bar.setRange(0, total_steps)
            self.progress_bar.setValue(current_step)
        else:
            self.progress_bar.setRange(0, 0)

    def finish(self, message: str = "✅ 分析完成！"):
        self.timer.stop()
        self.lbl_dot.setText("✨")
        self.lbl_status.setText(message)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        # 1.5 秒後自動淡出關閉
        QTimer.singleShot(1800, self.close)

    def set_error(self, err_msg: str):
        self.timer.stop()
        self.lbl_dot.setText("🔴")
        self.lbl_status.setText(f"❌ 錯誤: {err_msg[:60]}...")
        self.lbl_status.setStyleSheet("color: #f44336;")
        QTimer.singleShot(4000, self.close)

    def toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        self.content_widget.setVisible(not self.is_collapsed)
        self.btn_toggle_collapse.setText("+" if self.is_collapsed else "–")
        self.adjustSize()

    def _on_cancel_clicked(self):
        self.signal_cancel.emit()
        self.close()

    # 支援滑鼠拖曳移動視窗
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
