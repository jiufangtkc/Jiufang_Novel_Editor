from PyQt6.QtWidgets import QDialog
from utils.theme_manager import ThemeManager

class BaseDialog(QDialog):
    """
    自訂的對話框基底類別。
    自動繼承父視窗（或自身）的 scale_factor，並在初始化後套用主題樣式。
    所有子類別在 __init__ 的結尾或呼叫 super().__init__(parent) 後，
    都應該已經擁有這項功能。
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scale_factor = getattr(parent, "scale_factor", 1.0) if parent else 1.0
        ThemeManager.apply_theme_to_dialog(self, parent)
