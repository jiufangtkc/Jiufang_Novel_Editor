from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QAbstractItemView
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from utils.theme_manager import create_custom_icon
from utils.font_manager import FontManager

class LeftPanelView(QWidget):
    """左側作品面板元件，包含作品樹狀目錄、收折按鈕與垃圾桶按鈕。"""
    
    signal_tree_context_menu = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        left_layout = QVBoxLayout(self)
        left_layout.setContentsMargins(5, 5, 5, 5)

        # 頂部標題列
        left_header = QWidget()
        left_header_layout = QHBoxLayout(left_header)
        left_header_layout.setContentsMargins(0, 0, 0, 5)

        self.lbl_left_title = QLabel("作品面板")
        self.lbl_left_title.setFont(FontManager.get_font(size=10, weight=QFont.Weight.Bold))

        self.btn_toggle_left = QPushButton()
        self.btn_toggle_left.setObjectName("btn_toggle_left")
        self.btn_toggle_left.setIcon(create_custom_icon("arrow", direction="left"))
        self.btn_toggle_left.setToolTip("收折作品面板")
        self.btn_toggle_left.setFixedWidth(24)

        left_header_layout.addWidget(self.btn_toggle_left)
        left_header_layout.addStretch()
        left_header_layout.addWidget(self.lbl_left_title)
        left_layout.addWidget(left_header)

        # 樹狀目錄
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.setDragEnabled(True)
        self.tree_widget.setAcceptDrops(True)
        self.tree_widget.setDropIndicatorShown(True)
        self.tree_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.tree_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(lambda pos: self.signal_tree_context_menu.emit(pos))
        self.tree_widget.setFont(FontManager.get_font(size=10))
        left_layout.addWidget(self.tree_widget)

        # 底部列（垃圾桶按鈕）
        self.left_bottom_bar = QWidget()
        left_bottom_layout = QHBoxLayout(self.left_bottom_bar)
        left_bottom_layout.setContentsMargins(0, 5, 0, 0)

        self.btn_trash = QPushButton()
        self.btn_trash.setObjectName("btn_trash")
        self.btn_trash.setToolTip("查看垃圾桶")
        self.btn_trash.setIcon(create_custom_icon("trash"))
        self.btn_trash.setIconSize(QSize(16, 16))
        self.btn_trash.setFixedWidth(24)

        left_bottom_layout.addWidget(self.btn_trash)
        left_bottom_layout.addStretch()
        left_layout.addWidget(self.left_bottom_bar)

    def update_scale(self, scale: float):
        """介面縮放比例更新。"""
        self.lbl_left_title.setFont(FontManager.get_font(size=int(10 * scale), weight=QFont.Weight.Bold))
        self.btn_toggle_left.setFixedWidth(int(24 * scale))
        self.btn_toggle_left.setFixedHeight(int(24 * scale))
        self.tree_widget.setFont(FontManager.get_font(size=int(10 * scale)))
        self.tree_widget.setIconSize(QSize(int(16 * scale), int(16 * scale)))
        self.btn_trash.setFixedWidth(int(24 * scale))
        self.btn_trash.setFixedHeight(int(24 * scale))
        self.btn_trash.setIconSize(QSize(int(16 * scale), int(16 * scale)))
