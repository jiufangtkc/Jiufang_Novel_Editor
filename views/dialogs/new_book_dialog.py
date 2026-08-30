import sys
import json
import uuid
import re
import os
import datetime
import csv
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTreeWidget, QTreeWidgetItem, QTextEdit, QTabWidget,
    QMenuBar, QMenu, QFileDialog, QDialog, QLineEdit, QLabel, QPushButton,
    QComboBox, QFontComboBox, QToolBar, QAbstractItemView, QFormLayout,
    QMessageBox, QInputDialog, QDialogButtonBox, QStyle, QSizePolicy,
    QStackedWidget, QListWidget, QProgressBar, QFontDialog, QGraphicsDropShadowEffect,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QScrollArea, QColorDialog
)
from PyQt6.QtGui import (
    QFont, QIcon, QPixmap, QColor, QPainter, QAction, QTextCursor,
    QFontDatabase, QTextCharFormat, QKeySequence, QDragEnterEvent, QDropEvent,
    QTextDocument, QLinearGradient, QBrush, QPen, QPainterPath
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QSize, QPoint, QVariantAnimation, QTimer,
    pyqtProperty, QPropertyAnimation
)

class NewBookDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("開啟新書")
        self.setModal(True)
        self.resize(400, 150)

        layout = QFormLayout(self)
        self.title_input = QLineEdit()
        self.logline_input = QLineEdit()
        
        layout.addRow("書名:", self.title_input)
        layout.addRow("Logline (一句話大綱):", self.logline_input)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self):
        return self.title_input.text().strip(), self.logline_input.text().strip()
