from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QAbstractItemView, QSplitter,
    QComboBox, QFrame, QLineEdit, QPlainTextEdit, QFormLayout,
    QSizePolicy, QMenu, QStackedWidget, QTextEdit
)
from PyQt6.QtGui import QFont, QIcon, QAction
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from utils.theme_manager import create_custom_icon
from utils.font_manager import FontManager
from utils.markdown_highlighter import MarkdownHighlighter
from utils.markdown_utils import markdown_to_html
from models.models import (
    BUILTIN_CATEGORIES, CATEGORY_DISPLAY_NAMES, CATEGORY_ICONS
)

# UserRole 用法：
#   Qt.ItemDataRole.UserRole     → card_id (str) 或 None（分類節點）
#   Qt.ItemDataRole.UserRole + 1 → category key (str)
#   Qt.ItemDataRole.UserRole + 2 → "category" | "card" | "child_card"
ROLE_CARD_ID  = Qt.ItemDataRole.UserRole
ROLE_CATEGORY = Qt.ItemDataRole.UserRole + 1
ROLE_NODE_TYPE = Qt.ItemDataRole.UserRole + 2


class RightPanelCardEditor(QTextEdit):
    """資料集卡片文字編輯器：支援 Markdown 即時語法高亮、強制純文字貼上與快速鍵"""
    signal_save_requested = pyqtSignal()
    signal_ai_chat = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptRichText(False)
        self.highlighter = MarkdownHighlighter(self.document())

    def insertFromMimeData(self, source):
        """過濾所有外部 HTML / 富文本格式，一律以純文字插入"""
        if source.hasText():
            self.insertPlainText(source.text())
        else:
            super().insertFromMimeData(source)

    def keyPressEvent(self, event):
        modifiers = event.modifiers()
        key = event.key()

        # Ctrl+S 快捷鍵儲存
        if modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_S:
            self.signal_save_requested.emit()
            event.accept()
            return

        # Ctrl+B 粗體快捷鍵
        if modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_B:
            self.wrap_selection("**", "**")
            event.accept()
            return

        # Ctrl+I 斜體快捷鍵
        if modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_I:
            self.wrap_selection("*", "*")
            event.accept()
            return

        super().keyPressEvent(event)

    def wrap_selection(self, prefix: str, suffix: str):
        """將目前選取文字包裹指定前後標記，若無選取則插入標記並將光標置中"""
        cursor = self.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText()
            if text.startswith(prefix) and text.endswith(suffix) and len(text) >= len(prefix) + len(suffix):
                unwrapped = text[len(prefix):len(text)-len(suffix)]
                cursor.insertText(unwrapped)
            else:
                cursor.insertText(f"{prefix}{text}{suffix}")
        else:
            pos = cursor.position()
            cursor.insertText(f"{prefix}{suffix}")
            cursor.setPosition(pos + len(prefix))
            self.setTextCursor(cursor)
        self.setFocus()

    def toggle_line_prefix(self, prefix: str):
        """為當前行或選取行增加或移除指定行首前綴（例如標題 ### 或清單 - ）"""
        cursor = self.textCursor()
        cursor.beginEditBlock()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        cursor.setPosition(start)
        cursor.movePosition(cursor.MoveOperation.StartOfLine)
        cursor.setPosition(end, cursor.MoveMode.KeepAnchor)
        cursor.movePosition(cursor.MoveOperation.EndOfLine, cursor.MoveMode.KeepAnchor)

        selected_text = cursor.selectedText()
        lines = selected_text.split("\u2029")
        all_have_prefix = all(l.startswith(prefix) for l in lines if l.strip())
        new_lines = []
        for l in lines:
            if all_have_prefix:
                if l.startswith(prefix):
                    new_lines.append(l[len(prefix):])
                else:
                    new_lines.append(l)
            else:
                new_lines.append(prefix + l if l.strip() else l)

        cursor.insertText("\n".join(new_lines))
        cursor.endEditBlock()
        self.setFocus()

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        menu.addSeparator()

        selected_text = self.textCursor().selectedText().strip()
        has_selection = bool(selected_text)
        target_text = selected_text if has_selection else self.toPlainText().strip()
        scope_text = "選取內容" if has_selection else "卡片全文"

        act_chat = QAction(f"💬 與 AI 討論 ({scope_text})...", self)
        act_chat.setEnabled(bool(target_text))
        act_chat.triggered.connect(lambda: self.signal_ai_chat.emit(target_text))
        menu.addAction(act_chat)

        menu.exec(event.globalPos())


class RightPanelView(QWidget):
    """右側資料集面板：樹狀導航（上方） + 卡片內容/幕資訊展示區（下方）。"""

    # 從 View 發出的信號（由 CardController 連接）
    signal_card_selected = pyqtSignal(object)          # 點擊卡片節點，傳遞 QTreeWidgetItem
    signal_context_menu_requested = pyqtSignal(object, object)  # (QTreeWidgetItem | None, QPoint)
    signal_add_card_requested = pyqtSignal(str)        # 使用者要求新增卡片，傳遞分類 key
    signal_add_category_requested = pyqtSignal()       # 使用者要求新增自訂分類
    signal_card_dropped = pyqtSignal()                 # 拖放完成，通知 Controller 同步資料
    signal_save_scene_info = pyqtSignal()              # 幕屬性儲存
    signal_card_saved = pyqtSignal(str, str, str)      # 下方欄位儲存卡片變更: (card_id, new_title, new_content)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scale_factor = 1.0
        self.current_editing_card_id = None
        self.init_ui()

    def init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(5, 5, 5, 5)
        outer_layout.setSpacing(0)

        # ── 頂部標題列 ──────────────────────────────────────────────
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 5)

        self.lbl_right_title = QLabel("資料集")
        self.lbl_right_title.setFont(FontManager.get_font(size=10, weight=QFont.Weight.Bold))

        self.btn_toggle_right = QPushButton()
        self.btn_toggle_right.setObjectName("btn_toggle_right")
        self.btn_toggle_right.setIcon(create_custom_icon("arrow", direction="right"))
        self.btn_toggle_right.setToolTip("收折資料集")
        self.btn_toggle_right.setFixedWidth(24)

        header_layout.addWidget(self.lbl_right_title)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_toggle_right)
        outer_layout.addWidget(header)

        # ── 主體：垂直 Splitter（上下兩欄）─────────────────────────
        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        self.main_splitter.setHandleWidth(4)
        outer_layout.addWidget(self.main_splitter, 1)

        # ── 上方欄位：卡片樹狀導航 ──────────────────────────────────
        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        tree_layout.setSpacing(2)

        self.card_tree = QTreeWidget()
        self.card_tree.setObjectName("card_tree")
        self.card_tree.setHeaderHidden(True)
        self.card_tree.setFont(FontManager.get_font(size=9))
        self.card_tree.setDragEnabled(True)
        self.card_tree.setAcceptDrops(True)
        self.card_tree.setDropIndicatorShown(True)
        self.card_tree.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.card_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.card_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.card_tree.setIndentation(14)
        self.card_tree.setAnimated(True)
        # 樹狀節點點擊信號
        self.card_tree.itemClicked.connect(self._on_item_clicked)
        self.card_tree.customContextMenuRequested.connect(self._on_context_menu)
        # 拖放完成後通知
        original_drop = self.card_tree.dropEvent
        def _patched_drop(event):
            original_drop(event)
            self.signal_card_dropped.emit()
        self.card_tree.dropEvent = _patched_drop

        tree_layout.addWidget(self.card_tree)
        self.main_splitter.addWidget(tree_container)

        # ── 下方欄位：Stack 切換（提示頁 / 卡片內容編輯頁 / 幕資訊頁）───
        self.bottom_stack = QStackedWidget()
        self.bottom_stack.setObjectName("bottom_stack")

        # 1. 預設提示頁 (Index 0)
        self.placeholder_panel = QFrame()
        self.placeholder_panel.setFrameShape(QFrame.Shape.StyledPanel)
        ph_layout = QVBoxLayout(self.placeholder_panel)
        ph_layout.setContentsMargins(10, 10, 10, 10)
        ph_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_placeholder = QLabel("點擊上方卡片以檢視內容")
        self.lbl_placeholder.setFont(FontManager.get_font(size=9))
        self.lbl_placeholder.setStyleSheet("color: #888888;")
        ph_layout.addWidget(self.lbl_placeholder)
        self.bottom_stack.addWidget(self.placeholder_panel)

        # 2. 卡片內容編輯頁 (Index 1)
        self.card_detail_panel = QFrame()
        self.card_detail_panel.setFrameShape(QFrame.Shape.StyledPanel)
        cd_layout = QVBoxLayout(self.card_detail_panel)
        cd_layout.setContentsMargins(6, 6, 6, 6)
        cd_layout.setSpacing(4)

        # 卡片頂部資訊行：分類標籤與卡片標題輸入框
        header_card_row = QHBoxLayout()
        header_card_row.setSpacing(4)
        self.lbl_card_category = QLabel("📁 卡片")
        self.lbl_card_category.setFont(FontManager.get_font(size=9, weight=QFont.Weight.Bold))
        header_card_row.addWidget(self.lbl_card_category)
        
        self.card_title_edit = QLineEdit()
        self.card_title_edit.setPlaceholderText("卡片名稱...")
        self.card_title_edit.setFont(FontManager.get_font(size=9, weight=QFont.Weight.Bold))
        header_card_row.addWidget(self.card_title_edit, 1)
        cd_layout.addLayout(header_card_row)

        # Markdown 格式化工具列
        self.card_toolbar = QWidget()
        toolbar_layout = QHBoxLayout(self.card_toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(2)

        self.btn_format_bold = QPushButton("B")
        self.btn_format_bold.setFont(FontManager.get_font(size=8, weight=QFont.Weight.Bold))
        self.btn_format_bold.setToolTip("粗體 (Ctrl+B) — **文字**")
        self.btn_format_bold.setFixedWidth(24)
        self.btn_format_bold.setFixedHeight(22)
        self.btn_format_bold.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_format_bold.clicked.connect(lambda: self.card_content_edit.wrap_selection("**", "**"))
        toolbar_layout.addWidget(self.btn_format_bold)

        self.btn_format_italic = QPushButton("I")
        self.btn_format_italic.setFont(FontManager.get_font(size=8, italic=True))
        self.btn_format_italic.setToolTip("斜體 (Ctrl+I) — *文字*")
        self.btn_format_italic.setFixedWidth(24)
        self.btn_format_italic.setFixedHeight(22)
        self.btn_format_italic.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_format_italic.clicked.connect(lambda: self.card_content_edit.wrap_selection("*", "*"))
        toolbar_layout.addWidget(self.btn_format_italic)

        self.btn_format_header = QPushButton("H")
        self.btn_format_header.setFont(FontManager.get_font(size=8, weight=QFont.Weight.Bold))
        self.btn_format_header.setToolTip("標題 — ### 標題")
        self.btn_format_header.setFixedWidth(24)
        self.btn_format_header.setFixedHeight(22)
        self.btn_format_header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_format_header.clicked.connect(lambda: self.card_content_edit.toggle_line_prefix("### "))
        toolbar_layout.addWidget(self.btn_format_header)

        self.btn_format_list = QPushButton("•")
        self.btn_format_list.setFont(FontManager.get_font(size=9, weight=QFont.Weight.Bold))
        self.btn_format_list.setToolTip("清單項目 — - 項目")
        self.btn_format_list.setFixedWidth(24)
        self.btn_format_list.setFixedHeight(22)
        self.btn_format_list.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_format_list.clicked.connect(lambda: self.card_content_edit.toggle_line_prefix("- "))
        toolbar_layout.addWidget(self.btn_format_list)

        self.btn_format_strike = QPushButton("~S~")
        self.btn_format_strike.setFont(FontManager.get_font(size=7))
        self.btn_format_strike.setToolTip("刪除線 — ~~文字~~")
        self.btn_format_strike.setFixedWidth(28)
        self.btn_format_strike.setFixedHeight(22)
        self.btn_format_strike.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_format_strike.clicked.connect(lambda: self.card_content_edit.wrap_selection("~~", "~~"))
        toolbar_layout.addWidget(self.btn_format_strike)

        self.btn_format_ellipsis = QPushButton("……")
        self.btn_format_ellipsis.setFont(FontManager.get_font(size=7))
        self.btn_format_ellipsis.setToolTip("插入省略號 (……)")
        self.btn_format_ellipsis.setFixedWidth(26)
        self.btn_format_ellipsis.setFixedHeight(22)
        self.btn_format_ellipsis.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_format_ellipsis.clicked.connect(lambda: self.card_content_edit.insertPlainText("……"))
        toolbar_layout.addWidget(self.btn_format_ellipsis)

        self.btn_format_emdash = QPushButton("──")
        self.btn_format_emdash.setFont(FontManager.get_font(size=7))
        self.btn_format_emdash.setToolTip("插入破折號 (──)")
        self.btn_format_emdash.setFixedWidth(26)
        self.btn_format_emdash.setFixedHeight(22)
        self.btn_format_emdash.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_format_emdash.clicked.connect(lambda: self.card_content_edit.insertPlainText("──"))
        toolbar_layout.addWidget(self.btn_format_emdash)

        toolbar_layout.addStretch()

        self.btn_toggle_card_preview = QPushButton("📖 預覽")
        self.btn_toggle_card_preview.setFont(FontManager.get_font(size=8, weight=QFont.Weight.Bold))
        self.btn_toggle_card_preview.setToolTip("切換 Markdown 富文本渲染預覽與編輯模式")
        self.btn_toggle_card_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_card_preview.setFixedHeight(22)
        self.btn_toggle_card_preview.clicked.connect(self._toggle_card_preview_mode)
        toolbar_layout.addWidget(self.btn_toggle_card_preview)

        cd_layout.addWidget(self.card_toolbar)

        # 內容堆疊：Markdown 編輯器 (Index 0) / 富文本 HTML 預覽 (Index 1)
        self.card_content_stack = QStackedWidget()

        self.card_content_edit = RightPanelCardEditor()
        self.card_content_edit.setPlaceholderText("在此輸入卡片內容（支援 Markdown 語法高亮）...")
        self.card_content_edit.setFont(FontManager.get_font(size=9))
        self.card_content_edit.signal_save_requested.connect(self._on_save_card_clicked)
        self.card_content_edit.signal_ai_chat.connect(self._open_ai_chat_for_card)
        self.card_content_stack.addWidget(self.card_content_edit)

        self.card_preview_browser = QTextEdit()
        self.card_preview_browser.setReadOnly(True)
        self.card_preview_browser.setFont(FontManager.get_font(size=9))
        self.card_content_stack.addWidget(self.card_preview_browser)

        cd_layout.addWidget(self.card_content_stack, 1)

        # 儲存卡片按鈕
        self.btn_save_card_content = QPushButton("儲存卡片變更")
        self.btn_save_card_content.setObjectName("btn_save_card_content")
        self.btn_save_card_content.setFont(FontManager.get_font(size=9, weight=QFont.Weight.Bold))
        self.btn_save_card_content.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_card_content.setFixedHeight(26)
        self.btn_save_card_content.clicked.connect(self._on_save_card_clicked)
        cd_layout.addWidget(self.btn_save_card_content)

        self.bottom_stack.addWidget(self.card_detail_panel)

        # 3. 幕屬性編輯頁 (Index 2)
        self.scene_panel = QFrame()
        self.scene_panel.setFrameShape(QFrame.Shape.StyledPanel)
        scene_inner = QVBoxLayout(self.scene_panel)
        scene_inner.setContentsMargins(8, 8, 8, 8)
        scene_inner.setSpacing(6)

        scene_title_lbl = QLabel("🎬 幕屬性編輯")
        scene_title_lbl.setFont(FontManager.get_font(size=10, weight=QFont.Weight.Bold))
        scene_inner.addWidget(scene_title_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        scene_inner.addWidget(sep)

        scene_form = QFormLayout()
        scene_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.scene_info_pov_edit = QLineEdit()
        self.scene_info_pov_edit.setPlaceholderText("例：主角小明（第一人稱）")
        scene_form.addRow("視角角色：", self.scene_info_pov_edit)

        self.scene_info_location_edit = QLineEdit()
        self.scene_info_location_edit.setPlaceholderText("例：咖啡廳二樓角落")
        scene_form.addRow("場景地點：", self.scene_info_location_edit)

        scene_inner.addLayout(scene_form)

        scene_summary_lbl = QLabel("幕摘要：")
        scene_inner.addWidget(scene_summary_lbl)

        self.scene_info_summary_edit = QPlainTextEdit()
        self.scene_info_summary_edit.setPlaceholderText("簡短描述本幕發生的事件（100 字以內）...")
        self.scene_info_summary_edit.setFixedHeight(80)
        scene_inner.addWidget(self.scene_info_summary_edit)

        self.btn_save_scene_info = QPushButton("儲存幕資訊")
        self.btn_save_scene_info.setObjectName("btn_save_scene_info")
        self.btn_save_scene_info.setFont(FontManager.get_font(size=10, weight=QFont.Weight.Bold))
        self.btn_save_scene_info.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_scene_info.clicked.connect(self.signal_save_scene_info.emit)
        scene_inner.addWidget(self.btn_save_scene_info)

        self.bottom_stack.addWidget(self.scene_panel)

        self.main_splitter.addWidget(self.bottom_stack)
        self.main_splitter.setSizes([260, 260])
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 1)

        # 預設顯示提示頁
        self.bottom_stack.setCurrentIndex(0)

        # ── 向後相容 stub 屬性（不放入可見 UI，避免舊呼叫或測試報錯）─────
        self.combo_add_category = QComboBox()
        self.combo_add_category.hide()
        self.btn_add_card = QPushButton("＋ 新增卡片")
        self.btn_add_card.hide()
        self.btn_add_category = QPushButton("⊕")
        self.btn_add_category.hide()

        # 初始化分類（若有需要）
        self._rebuild_default_combo()

    def _rebuild_default_combo(self):
        """根據內建分類初始化下拉選單（相容用）。"""
        self.combo_add_category.clear()
        for key in BUILTIN_CATEGORIES:
            if key == "ai_chat":
                continue
            display = CATEGORY_DISPLAY_NAMES.get(key, key)
            icon_char = CATEGORY_ICONS.get(key, "📁")
            self.combo_add_category.addItem(f"{icon_char} {display}", key)

    def rebuild_category_combo(self, category_order: list, custom_categories: list):
        """CardController 呼叫以同步自訂分類到下拉選單（相容用）。"""
        self.combo_add_category.clear()
        for key in category_order:
            if key == "ai_chat":
                continue
            display = CATEGORY_DISPLAY_NAMES.get(key, key)
            icon_char = CATEGORY_ICONS.get(key, CATEGORY_ICONS["_custom"])
            self.combo_add_category.addItem(f"{icon_char} {display}", key)

    def show_placeholder(self):
        """切換為下方提示頁面。"""
        self.current_editing_card_id = None
        self.bottom_stack.setCurrentIndex(0)

    def show_card_detail(self, card_id: str, title: str, content: str, category_name: str):
        """切換並顯示下方卡片內容編輯頁面。"""
        self.current_editing_card_id = card_id
        self.lbl_card_category.setText(f"📁 {category_name}")
        self.card_title_edit.setText(title)
        self.card_content_edit.setPlainText(content)
        # 若當前處於預覽模式，同步更新預覽 HTML
        if self.card_content_stack.currentIndex() == 1:
            self.card_preview_browser.setHtml(markdown_to_html(content))
        self.bottom_stack.setCurrentIndex(1)

    def _toggle_card_preview_mode(self):
        """切換卡片內容的編輯與 Markdown 富文本預覽模式"""
        if self.card_content_stack.currentIndex() == 0:
            # 切換到預覽
            content = self.card_content_edit.toPlainText()
            html_content = markdown_to_html(content)
            self.card_preview_browser.setHtml(html_content)
            self.card_content_stack.setCurrentIndex(1)
            self.btn_toggle_card_preview.setText("📝 編輯")
            self._set_formatting_buttons_enabled(False)
        else:
            # 切換回編輯
            self.card_content_stack.setCurrentIndex(0)
            self.btn_toggle_card_preview.setText("📖 預覽")
            self._set_formatting_buttons_enabled(True)

    def _set_formatting_buttons_enabled(self, enabled: bool):
        for btn in [
            self.btn_format_bold, self.btn_format_italic,
            self.btn_format_header, self.btn_format_list,
            self.btn_format_strike, self.btn_format_ellipsis,
            self.btn_format_emdash
        ]:
            btn.setEnabled(enabled)

    def _open_ai_chat_for_card(self, context_text: str):
        """開啟 AI 對話視窗並引用卡片文字"""
        try:
            from views.dialogs.ai_chat_dialog import AIChatDialog
            dlg = AIChatDialog(self, initial_context=context_text)
            dlg.signal_insert_to_editor.connect(lambda text: self.card_content_edit.insertPlainText(text))
            dlg.exec()
        except Exception:
            pass

    def set_scene_panel_visible(self, visible: bool):
        """控制幕屬性編輯面板的顯示。"""
        if visible:
            self.current_editing_card_id = None
            self.bottom_stack.setCurrentIndex(2)
        else:
            if self.bottom_stack.currentIndex() == 2:
                self.bottom_stack.setCurrentIndex(0)

    # ── 內部事件處理器 ────────────────────────────────────────────────

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        node_type = item.data(0, ROLE_NODE_TYPE)
        if node_type == "card":
            self.signal_card_selected.emit(item)
        else:
            # 點擊分類節點時切換為提示頁
            self.show_placeholder()

    def _on_context_menu(self, pos):
        item = self.card_tree.itemAt(pos)
        global_pos = self.card_tree.viewport().mapToGlobal(pos)
        self.signal_context_menu_requested.emit(item, global_pos)

    def _on_add_card_clicked(self):
        category_key = self.combo_add_category.currentData()
        if category_key:
            self.signal_add_card_requested.emit(category_key)

    def _on_save_card_clicked(self):
        if self.current_editing_card_id:
            title = self.card_title_edit.text()
            content = self.card_content_edit.toPlainText()
            self.signal_card_saved.emit(self.current_editing_card_id, title, content)

    # ── 樹狀節點建立輔助 ─────────────────────────────────────────────

    def make_category_item(self, category_key: str, display_name: str) -> QTreeWidgetItem:
        """建立分類頂層節點。"""
        icon_char = CATEGORY_ICONS.get(category_key, CATEGORY_ICONS["_custom"])
        item = QTreeWidgetItem()
        item.setText(0, f"{icon_char}  {display_name}")
        item.setData(0, ROLE_CARD_ID, None)
        item.setData(0, ROLE_CATEGORY, category_key)
        item.setData(0, ROLE_NODE_TYPE, "category")
        item.setFlags(
            Qt.ItemFlag.ItemIsEnabled |
            Qt.ItemFlag.ItemIsDropEnabled  # 允許拖放至分類節點
        )
        font = FontManager.get_font(size=int(9 * self.scale_factor), weight=QFont.Weight.Bold)
        item.setFont(0, font)
        return item

    def make_card_item(self, card_id: str, title: str, category_key: str,
                       color_hex: str = "#3C3F41", is_child: bool = False) -> QTreeWidgetItem:
        """建立卡片節點。"""
        item = QTreeWidgetItem()
        display_title = title.strip() if title.strip() else "（未命名卡片）"
        item.setText(0, f"  {display_title}")
        item.setData(0, ROLE_CARD_ID, card_id)
        item.setData(0, ROLE_CATEGORY, category_key)
        item.setData(0, ROLE_NODE_TYPE, "card")
        item.setFlags(
            Qt.ItemFlag.ItemIsEnabled |
            Qt.ItemFlag.ItemIsSelectable |
            Qt.ItemFlag.ItemIsDragEnabled |
            Qt.ItemFlag.ItemIsDropEnabled
        )
        item.setFont(0, FontManager.get_font(size=int(9 * self.scale_factor)))
        return item

    def update_scale(self, scale: float):
        """介面縮放比例更新。"""
        self.scale_factor = scale
        self.lbl_right_title.setFont(FontManager.get_font(size=int(10 * scale), weight=QFont.Weight.Bold))
        self.btn_toggle_right.setFixedWidth(int(24 * scale))
        self.btn_toggle_right.setFixedHeight(int(24 * scale))
        self.card_tree.setFont(FontManager.get_font(size=int(9 * scale)))
        self.card_tree.setIconSize(QSize(int(16 * scale), int(16 * scale)))

        # 遞迴更新樹狀節點字型
        def _update_items(item: QTreeWidgetItem):
            node_type = item.data(0, ROLE_NODE_TYPE)
            if node_type == "category":
                item.setFont(0, FontManager.get_font(size=int(9 * scale), weight=QFont.Weight.Bold))
            else:
                item.setFont(0, FontManager.get_font(size=int(9 * scale)))
            for i in range(item.childCount()):
                _update_items(item.child(i))

        for i in range(self.card_tree.topLevelItemCount()):
            _update_items(self.card_tree.topLevelItem(i))

        self.lbl_placeholder.setFont(FontManager.get_font(size=int(9 * scale)))
        self.lbl_card_category.setFont(FontManager.get_font(size=int(9 * scale), weight=QFont.Weight.Bold))
        self.card_title_edit.setFont(FontManager.get_font(size=int(9 * scale), weight=QFont.Weight.Bold))
        self.card_content_edit.setFont(FontManager.get_font(size=int(9 * scale)))
        self.card_preview_browser.setFont(FontManager.get_font(size=int(9 * scale)))

        if hasattr(self, "btn_format_bold"):
            self.btn_format_bold.setFont(FontManager.get_font(size=int(8 * scale), weight=QFont.Weight.Bold))
            self.btn_format_bold.setFixedSize(int(24 * scale), int(22 * scale))
            self.btn_format_italic.setFont(FontManager.get_font(size=int(8 * scale), italic=True))
            self.btn_format_italic.setFixedSize(int(24 * scale), int(22 * scale))
            self.btn_format_header.setFont(FontManager.get_font(size=int(8 * scale), weight=QFont.Weight.Bold))
            self.btn_format_header.setFixedSize(int(24 * scale), int(22 * scale))
            self.btn_format_list.setFont(FontManager.get_font(size=int(9 * scale), weight=QFont.Weight.Bold))
            self.btn_format_list.setFixedSize(int(24 * scale), int(22 * scale))
            self.btn_format_strike.setFont(FontManager.get_font(size=int(7 * scale)))
            self.btn_format_strike.setFixedSize(int(28 * scale), int(22 * scale))
            self.btn_format_ellipsis.setFont(FontManager.get_font(size=int(7 * scale)))
            self.btn_format_ellipsis.setFixedSize(int(26 * scale), int(22 * scale))
            self.btn_format_emdash.setFont(FontManager.get_font(size=int(7 * scale)))
            self.btn_format_emdash.setFixedSize(int(26 * scale), int(22 * scale))
            self.btn_toggle_card_preview.setFont(FontManager.get_font(size=int(8 * scale), weight=QFont.Weight.Bold))
            self.btn_toggle_card_preview.setFixedHeight(int(22 * scale))

        self.btn_save_card_content.setFont(FontManager.get_font(size=int(9 * scale), weight=QFont.Weight.Bold))
        self.btn_save_card_content.setFixedHeight(int(26 * scale))

        self.combo_add_category.setFont(FontManager.get_font(size=int(9 * scale)))
        self.combo_add_category.setFixedHeight(int(26 * scale))
        self.btn_add_card.setFont(FontManager.get_font(size=int(9 * scale), weight=QFont.Weight.Bold))
        self.btn_add_card.setFixedHeight(int(26 * scale))
        self.btn_add_category.setFont(FontManager.get_font(size=int(11 * scale)))
        self.btn_add_category.setFixedSize(int(26 * scale), int(26 * scale))

        if hasattr(self, "btn_save_scene_info"):
            self.btn_save_scene_info.setFont(FontManager.get_font(size=int(10 * scale), weight=QFont.Weight.Bold))
            self.scene_info_pov_edit.setFont(FontManager.get_font(size=int(9 * scale)))
            self.scene_info_location_edit.setFont(FontManager.get_font(size=int(9 * scale)))
            self.scene_info_summary_edit.setFont(FontManager.get_font(size=int(9 * scale)))

    # ── 公開屬性（向後相容橋接用）──────────────────────────────────

    @property
    def scene_tab_widget(self):
        """向後相容：回傳幕屬性面板容器。"""
        return self.scene_panel

    @property
    def scene_tab_index(self):
        """向後相容：固定回傳 0，幕面板已改為顯示/隱藏控制。"""
        return 0

    # 向後相容：空的 card_layouts dict（不再使用，保留避免舊呼叫崩潰）
    @property
    def card_layouts(self):
        return {}

    # 向後相容：假的 Tab 元件屬性
    @property
    def tabs(self):
        return _DummyTabs()

    # 向後相容：舊的「新增卡片」按鈕屬性（統一導向到 btn_add_card）
    @property
    def btn_add_core_summary(self):
        return self.btn_add_card

    @property
    def btn_add_core_character(self):
        return self.btn_add_card

    @property
    def btn_add_core_world(self):
        return self.btn_add_card

    @property
    def btn_add_core_timeline(self):
        return self.btn_add_card


class _DummyTabs:
    """向後相容：讓舊的 self.view.tabs.currentIndex() 等呼叫不崩潰。"""
    def currentIndex(self): return 0
    def setCurrentIndex(self, idx): pass
    def setTabVisible(self, idx, visible): pass
    def addTab(self, widget, label): pass
