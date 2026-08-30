"""
場景屬性編輯對話框（SceneMetadataDialog）

讓使用者編輯 scene 節點的三個 metadata：
  - 場景摘要（scene_summary）
  - 視角角色（scene_pov）
  - 場景地點（scene_location）

注意：此對話框不直接存取 Controller，呼叫方負責讀取 result() 後更新 data。
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QDialogButtonBox, QFrame
)
from PyQt6.QtCore import Qt


class SceneMetadataDialog(QDialog):
    """場景 metadata 編輯對話框。"""

    def __init__(self, parent=None,
                 scene_name: str = "",
                 scene_summary: str = "",
                 scene_pov: str = "",
                 scene_location: str = ""):
        super().__init__(parent)
        self.setWindowTitle("場景屬性")
        self.setMinimumWidth(460)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        self._init_ui(scene_name, scene_summary, scene_pov, scene_location)

    # ------------------------------------------------------------------
    # UI 建立
    # ------------------------------------------------------------------

    def _init_ui(self, scene_name: str, scene_summary: str,
                 scene_pov: str, scene_location: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 16)

        # 場景名稱（唯讀標題）
        title_lbl = QLabel(f"🎬 場景：{scene_name}")
        title_lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_lbl)

        # 分隔線
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        # 表單欄位
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(10)

        # 視角角色
        self.pov_edit = QLineEdit()
        self.pov_edit.setText(scene_pov)
        self.pov_edit.setPlaceholderText("例：主角小明（第一人稱）")
        self.pov_edit.setObjectName("scene_pov_edit")
        form.addRow("視角角色：", self.pov_edit)

        # 場景地點
        self.location_edit = QLineEdit()
        self.location_edit.setText(scene_location)
        self.location_edit.setPlaceholderText("例：咖啡廳二樓角落")
        self.location_edit.setObjectName("scene_location_edit")
        form.addRow("場景地點：", self.location_edit)

        layout.addLayout(form)

        # 場景摘要（多行）
        summary_lbl = QLabel("場景摘要：")
        layout.addWidget(summary_lbl)

        self.summary_edit = QPlainTextEdit()
        self.summary_edit.setPlainText(scene_summary)
        self.summary_edit.setPlaceholderText("簡短描述本場景發生的事件（100 字以內）...")
        self.summary_edit.setMinimumHeight(100)
        self.summary_edit.setMaximumHeight(200)
        self.summary_edit.setObjectName("scene_summary_edit")
        layout.addWidget(self.summary_edit)

        # 確認 / 取消按鈕
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.button(QDialogButtonBox.StandardButton.Ok).setText("確認儲存")
        btn_box.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    # ------------------------------------------------------------------
    # 讀取結果
    # ------------------------------------------------------------------

    def get_metadata(self) -> dict:
        """
        返回使用者輸入的 metadata dict。
        於 accept() 後呼叫。
        """
        return {
            "scene_summary": self.summary_edit.toPlainText().strip(),
            "scene_pov": self.pov_edit.text().strip(),
            "scene_location": self.location_edit.text().strip(),
        }
