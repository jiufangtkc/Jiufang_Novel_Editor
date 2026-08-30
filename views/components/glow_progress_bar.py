from PyQt6.QtWidgets import QProgressBar, QGraphicsDropShadowEffect
from PyQt6.QtGui import QColor
from PyQt6.QtCore import pyqtProperty, QPropertyAnimation

class GlowProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTextVisible(False)
        self.is_glowing = False
        
        self.glow_effect = QGraphicsDropShadowEffect(self)
        self.glow_effect.setBlurRadius(15)
        self.glow_effect.setOffset(0, 0)
        self.setGraphicsEffect(self.glow_effect)
        self.glow_effect.setEnabled(False)
        
        self.animation = QPropertyAnimation(self.glow_effect, b"color")
        self.animation.setDuration(1500)
        self.animation.setLoopCount(-1)
        
        self._theme_color_start = QColor("#00e676")
        self._theme_color_end = QColor("#69f0ae")
        self.refresh_style()

    @property
    def theme_color_start(self):
        return self._theme_color_start

    @theme_color_start.setter
    def theme_color_start(self, color):
        self._theme_color_start = color
        self.refresh_style()

    @property
    def theme_color_end(self):
        return self._theme_color_end

    @theme_color_end.setter
    def theme_color_end(self, color):
        self._theme_color_end = color
        self.refresh_style()

    def refresh_style(self):
        start_hex = self._theme_color_start.name()
        end_hex = self._theme_color_end.name()
        
        qss = f"""
        QProgressBar {{
            background-color: #1e1e1e;
            border: 1px solid #444;
            text-align: center;
            border-radius: 4px;
        }}
        QProgressBar::chunk {{
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {start_hex}, stop:1 {end_hex});
        }}
        """
        self.setStyleSheet(qss)
        
        r, g, b = self._theme_color_end.red(), self._theme_color_end.green(), self._theme_color_end.blue()
        self.animation.setKeyValueAt(0.0, QColor(r, g, b, 50))
        self.animation.setKeyValueAt(0.5, QColor(r, g, b, 255))
        self.animation.setKeyValueAt(1.0, QColor(r, g, b, 50))
        if self.is_glowing:
            self.glow_effect.setColor(QColor(r, g, b, 255))

    def setValue(self, val):
        m = self.maximum()
        display_val = m if (m > 0 and val >= m) else val
        super().setValue(display_val)
        self.check_glow_status(val)
        
    def setMaximum(self, max_val):
        super().setMaximum(max_val)
        self.check_glow_status(self.value())

    def check_glow_status(self, current_val=None):
        val = current_val if current_val is not None else self.value()
        m = self.maximum()
        if m > 0 and val >= m:
            if not self.is_glowing:
                self.is_glowing = True
                self.glow_effect.setEnabled(True)
                self.animation.start()
        else:
            if self.is_glowing:
                self.is_glowing = False
                self.animation.stop()
                self.glow_effect.setEnabled(False)
