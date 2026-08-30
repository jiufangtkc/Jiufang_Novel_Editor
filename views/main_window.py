from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QLabel, QPushButton,
    QComboBox, QFontComboBox, QToolBar,
    QStackedWidget, QListWidget
)
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt, QSize, pyqtSignal

from views.components.glow_progress_bar import GlowProgressBar
from views.components.card_widget import CardWidget
from views.components.writing_chart_view import WritingChartView
from views.components.writing_log_dashboard import WritingLogDashboard
from views.components.jne_text_edit import JNE_TextEdit
from views.components.find_replace_bar import FindReplaceBar
from views.components.outline_view import OutlineView
from views.components.menu_builder import MenuBuilder
from views.components.left_panel_view import LeftPanelView
from views.components.right_panel_view import RightPanelView
from utils.theme_manager import create_custom_icon, ThemeManager, set_window_dark_mode
from utils.font_manager import FontManager

class AdaptiveStackedWidget(QStackedWidget):
    """自適應堆疊視窗，避免隱藏子頁面的較大 minimumSizeHint 限制父分割容器。"""
    def minimumSizeHint(self):
        curr = self.currentWidget()
        if curr:
            return QSize(min(curr.minimumSizeHint().width(), 240), min(curr.minimumSizeHint().height(), 200))
        return QSize(200, 200)

class JNEStatusBar(QWidget):
    """狀態列元件，具備彈性最小尺寸提示。"""
    def minimumSizeHint(self):
        return QSize(200, 44)

class MainWindow(QMainWindow):
    # Signals for things that don't have built-in signals we can easily hook, or custom events
    # Example: custom context menu
    signal_tree_context_menu = pyqtSignal(object)
    signal_edit_project_title = pyqtSignal(object)
    signal_edit_logline = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("九方小說編輯器 (Jiufang Novel Editor)")
        self.resize(1200, 800)

        self.scale_factor = 1.0
        self.current_theme = "default"
        self.folder_icon_color = "#e5c07b"
        self.file_icon_color = "#dcdcdc"
        self.arrow_icon_color = "#e3e3e3"
        self.trash_icon_color = "#e3e3e3"
        self.last_left_width = 240
        self.last_right_width = 480
        self.card_layouts = {}
        
        # 沉浸模式狀態
        self.is_focus_mode = False
        self._saved_splitter_sizes = [240, 480, 480]
        self._saved_is_maximized = False
        
        self.init_ui()
        self.setup_menus()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Top Bar
        self.top_bar = QWidget()
        top_layout = QHBoxLayout(self.top_bar)
        self.lbl_project_title = QLabel("")
        self.lbl_project_title.setFont(FontManager.get_font(size=12, weight=QFont.Weight.Bold))
        self.lbl_project_title.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lbl_project_title.mousePressEvent = lambda e: self.signal_edit_project_title.emit(e)
        self.lbl_project_logline = QLabel("")
        self.lbl_project_logline.setFont(FontManager.get_font(size=10))
        self.lbl_project_logline.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lbl_project_logline.mousePressEvent = lambda e: self.signal_edit_logline.emit(e)

        top_layout.addWidget(self.lbl_project_title)
        top_layout.addWidget(self.lbl_project_logline)
        top_layout.addStretch()
        main_layout.addWidget(self.top_bar)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter, 1)

        # 1. Left Panel
        self.left_panel = LeftPanelView(self)
        self.left_widget = self.left_panel
        self.tree_widget = self.left_panel.tree_widget
        self.btn_toggle_left = self.left_panel.btn_toggle_left
        self.lbl_left_title = self.left_panel.lbl_left_title
        self.left_bottom_bar = self.left_panel.left_bottom_bar
        self.btn_trash = self.left_panel.btn_trash
        self.left_panel.signal_tree_context_menu.connect(lambda pos: self.signal_tree_context_menu.emit(pos))

        # 2. Center Panel
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(5, 5, 5, 5)

        self.center_stack = AdaptiveStackedWidget()

        # Page 0: Editor
        self.write_page = QWidget()
        self.write_page_layout = QVBoxLayout(self.write_page)
        self.write_page_layout.setContentsMargins(0, 0, 0, 0)

        # 沉浸模式提示列
        self.lbl_focus_banner = QLabel("✨ 沉浸寫作模式 — 按 Esc 或 F11 退出")
        self.lbl_focus_banner.setObjectName("lbl_focus_banner")
        self.lbl_focus_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_focus_banner.setFont(FontManager.get_font(size=10))
        self.lbl_focus_banner.hide()
        self.write_page_layout.addWidget(self.lbl_focus_banner)

        self.lbl_current_file = QLabel("請選擇左側文件進行編輯")
        self.lbl_current_file.setObjectName("lbl_current_file")
        self.lbl_current_file.setFont(FontManager.get_font(size=14, weight=QFont.Weight.Bold))
        self.write_page_layout.addWidget(self.lbl_current_file)

        self.format_toolbar = QToolBar()
        self.combo_font = QFontComboBox()
        self.combo_font.setCurrentFont(QFont(FontManager.get_default_font_family()))
        self.format_toolbar.addWidget(self.combo_font)

        self.combo_size = QComboBox()
        self.combo_size.addItems([str(i) for i in [8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 36, 48]])
        self.combo_size.setCurrentText("12")
        self.combo_size.setFixedWidth(70)
        self.format_toolbar.addWidget(self.combo_size)

        self.btn_ellipsis = QPushButton("……")
        self.btn_ellipsis.setFont(FontManager.get_font(size=10))
        self.btn_ellipsis.setToolTip("插入省略號 (……)")
        self.format_toolbar.addWidget(self.btn_ellipsis)

        self.btn_emdash = QPushButton("──")
        self.btn_emdash.setFont(FontManager.get_font(size=10))
        self.btn_emdash.setToolTip("插入破折號 (──)")
        self.format_toolbar.addWidget(self.btn_emdash)

        from PyQt6.QtWidgets import QSizePolicy
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.format_toolbar.addWidget(spacer)

        self.btn_typewriter = QPushButton("打字機模式: 關")
        self.btn_typewriter.setFont(FontManager.get_font(size=9))
        self.btn_typewriter.setCheckable(True)
        self.format_toolbar.addWidget(self.btn_typewriter)

        self.write_page_layout.addWidget(self.format_toolbar)

        self.find_replace_bar = FindReplaceBar(self)
        self.find_replace_bar.hide()
        self.write_page_layout.addWidget(self.find_replace_bar)

        self.editor = JNE_TextEdit(self)
        self.editor.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
        default_editor_font = FontManager.get_font(size=12)
        self.editor.setFont(default_editor_font)
        self.editor.document().setDefaultFont(default_editor_font)
        self.write_page_layout.addWidget(self.editor)

        # Status Bar
        self.status_bar = JNEStatusBar()
        self.status_bar.setObjectName("statusBar")
        status_root_layout = QVBoxLayout(self.status_bar)
        status_root_layout.setContentsMargins(10, 4, 10, 4)
        status_root_layout.setSpacing(4)

        # Row 1: 今日進度
        row1_layout = QHBoxLayout()
        row1_layout.setContentsMargins(0, 0, 0, 0)
        row1_layout.setSpacing(8)

        self.lbl_progress = QLabel("今日進度: 0 / 1000 字 (0%)")
        self.lbl_progress.setFont(FontManager.get_font(size=9))
        self.progress_bar = GlowProgressBar()
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedWidth(150)
        self.progress_bar.setTextVisible(False)

        self.btn_set_target = QPushButton("設定目標")
        self.btn_set_target.setFont(FontManager.get_font(size=9))
        self.btn_clear_progress = QPushButton("清除進度")
        self.btn_clear_progress.setFont(FontManager.get_font(size=9))

        row1_layout.addWidget(self.lbl_progress)
        row1_layout.addWidget(self.progress_bar)
        row1_layout.addWidget(self.btn_set_target)
        row1_layout.addWidget(self.btn_clear_progress)
        row1_layout.addStretch()

        self.lbl_word_count = QLabel("本頁: 0 字 | 全文: 0 字")
        self.lbl_word_count.setFont(FontManager.get_font(size=9))
        row1_layout.addWidget(self.lbl_word_count)

        status_root_layout.addLayout(row1_layout)

        # Row 2: 寫作專案總進度
        row2_layout = QHBoxLayout()
        row2_layout.setContentsMargins(0, 0, 0, 0)
        row2_layout.setSpacing(8)

        self.lbl_project_progress = QLabel("專案總進度: 0 / 100000 字 (0%)")
        self.lbl_project_progress.setFont(FontManager.get_font(size=9))
        self.project_progress_bar = GlowProgressBar()
        self.project_progress_bar.setRange(0, 100000)
        self.project_progress_bar.setValue(0)
        self.project_progress_bar.setFixedWidth(150)
        self.project_progress_bar.setTextVisible(False)

        self.btn_set_project_target = QPushButton("設定專案目標")
        self.btn_set_project_target.setFont(FontManager.get_font(size=9))

        row2_layout.addWidget(self.lbl_project_progress)
        row2_layout.addWidget(self.project_progress_bar)
        row2_layout.addWidget(self.btn_set_project_target)
        row2_layout.addStretch()

        status_root_layout.addLayout(row2_layout)

        self.write_page_layout.addWidget(self.status_bar)

        # Page 1: Trash
        self.trash_page = QWidget()
        trash_page_layout = QVBoxLayout(self.trash_page)
        trash_page_layout.setContentsMargins(10, 10, 10, 10)

        trash_header_layout = QHBoxLayout()
        lbl_trash_title = QLabel("垃圾桶 (已刪除項目)")
        lbl_trash_title.setFont(FontManager.get_font(size=14, weight=QFont.Weight.Bold))
        
        self.btn_restore = QPushButton("復原選取項目")
        self.btn_restore.setFont(FontManager.get_font(size=9))

        self.btn_delete_permanently = QPushButton("永久刪除選取項目")
        self.btn_delete_permanently.setFont(FontManager.get_font(size=9))

        self.btn_clear_trash = QPushButton("清空垃圾桶")
        self.btn_clear_trash.setFont(FontManager.get_font(size=9))

        trash_header_layout.addWidget(lbl_trash_title)
        trash_header_layout.addStretch()
        trash_header_layout.addWidget(self.btn_restore)
        trash_header_layout.addWidget(self.btn_delete_permanently)
        trash_header_layout.addWidget(self.btn_clear_trash)
        trash_page_layout.addLayout(trash_header_layout)

        self.trash_list_widget = QListWidget()
        self.trash_list_widget.setObjectName("trash_list_widget")
        self.trash_list_widget.setFont(FontManager.get_font(size=10))
        self.trash_list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        trash_page_layout.addWidget(self.trash_list_widget)

        # Page 2: Dashboard
        self.writing_log_dashboard = WritingLogDashboard(self)
        
        # Page 3: Outline View
        self.outline_view = OutlineView(self)

        self.center_stack.addWidget(self.write_page)
        self.center_stack.addWidget(self.trash_page)
        self.center_stack.addWidget(self.writing_log_dashboard)
        self.center_stack.addWidget(self.outline_view)
        center_layout.addWidget(self.center_stack)

        # 3. Right Panel
        self.right_panel = RightPanelView(self)
        self.right_widget = self.right_panel
        self.lbl_right_title = self.right_panel.lbl_right_title
        self.btn_toggle_right = self.right_panel.btn_toggle_right
        # 新版樹狀導航：主要操作元件
        self.card_tree = self.right_panel.card_tree
        self.btn_add_card = self.right_panel.btn_add_card
        self.btn_add_category = self.right_panel.btn_add_category
        self.combo_add_category = self.right_panel.combo_add_category
        # 幕屬性編輯（保留向後相容）
        self.scene_tab_widget = self.right_panel.scene_tab_widget
        self.scene_info_pov_edit = self.right_panel.scene_info_pov_edit
        self.scene_info_location_edit = self.right_panel.scene_info_location_edit
        self.scene_info_summary_edit = self.right_panel.scene_info_summary_edit
        self.btn_save_scene_info = self.right_panel.btn_save_scene_info
        self.scene_tab_index = self.right_panel.scene_tab_index
        # 向後相容：虛擬屬性（不再使用，但避免舊呼叫崩潰）
        self.card_layouts = self.right_panel.card_layouts
        self.tabs = self.right_panel.tabs
        self.btn_add_core_summary = self.right_panel.btn_add_core_summary
        self.btn_add_core_character = self.right_panel.btn_add_core_character
        self.btn_add_core_world = self.right_panel.btn_add_core_world
        self.btn_add_core_timeline = self.right_panel.btn_add_core_timeline

        self.splitter.addWidget(self.left_widget)
        self.splitter.addWidget(center_widget)
        self.splitter.addWidget(self.right_widget)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 2)
        self.splitter.setStretchFactor(2, 2)
        self.splitter.setSizes([240, 480, 480])

    def setup_menus(self):
        MenuBuilder.build_menus(self)

    # =========================================================================
    # 沉浸模式 (Focus Mode) 控制方法
    # =========================================================================

    def enter_focus_mode(self):
        """進入沉浸模式（隱藏所有干擾介面，限制邊距並全螢幕）。"""
        if self.is_focus_mode:
            return
        self.is_focus_mode = True
        self._saved_splitter_sizes = self.splitter.sizes()
        self._saved_is_maximized = self.isMaximized()

        self.top_bar.hide()
        self.left_widget.hide()
        self.right_widget.hide()
        self.format_toolbar.hide()
        self.find_replace_bar.hide()
        self.status_bar.hide()
        self.menuBar().hide()
        
        # 確保在寫作編輯器頁面 (Page 0)
        self.center_stack.setCurrentIndex(0)
        self.write_page_layout.setContentsMargins(100, 15, 100, 15)
        self.lbl_focus_banner.show()
        self.showFullScreen()

    def exit_focus_mode(self):
        """退出沉浸模式，恢復各面板可見性與視窗尺寸。"""
        if not self.is_focus_mode:
            return
        self.is_focus_mode = False
        
        self.lbl_focus_banner.hide()
        self.write_page_layout.setContentsMargins(0, 0, 0, 0)
        self.top_bar.show()
        self.left_widget.show()
        self.right_widget.show()
        self.format_toolbar.show()
        self.status_bar.show()
        self.menuBar().show()
        
        if self._saved_splitter_sizes:
            self.splitter.setSizes(self._saved_splitter_sizes)
            
        if self._saved_is_maximized:
            self.showMaximized()
        else:
            self.showNormal()

    def toggle_focus_mode(self):
        """切換沉浸模式開關。"""
        if self.is_focus_mode:
            self.exit_focus_mode()
        else:
            self.enter_focus_mode()

    def showEvent(self, event):
        """主視窗首次顯示時，確保套用正確的分隔槽比例與尺寸。"""
        super().showEvent(event)
        if not getattr(self, "_has_shown_initial_layout", False):
            self._has_shown_initial_layout = True
            if hasattr(self, "_saved_splitter_sizes") and self._saved_splitter_sizes:
                self.splitter.setSizes(self._saved_splitter_sizes)

    def keyPressEvent(self, event):
        """全域鍵盤快捷鍵處理。"""
        if event.key() == Qt.Key.Key_F11:
            self.toggle_focus_mode()
            event.accept()
            return
        elif event.key() == Qt.Key.Key_Escape and self.is_focus_mode:
            self.exit_focus_mode()
            event.accept()
            return
        super().keyPressEvent(event)
