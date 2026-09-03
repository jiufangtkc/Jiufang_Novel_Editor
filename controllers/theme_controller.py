import sys
from PyQt6.QtWidgets import QApplication, QFontDialog, QInputDialog
from PyQt6.QtGui import QFont, QTextCursor, QTextCharFormat, QColor
from PyQt6.QtCore import QSize
from utils.theme_manager import ThemeManager, set_window_dark_mode, create_custom_icon
from utils.font_manager import FontManager
from views.components.card_widget import CardWidget
from models.models import MARK_COLOR_MAP
from services.app_settings_service import AppSettingsService

class ThemeController:
    """負責主題切換、UI 縮放、全域字型調整、圖示更新與面板收折。"""

    def __init__(self, main_controller):
        self.mc = main_controller

    @property
    def view(self):
        return self.mc.view

    def toggle_left_panel(self):
        is_collapsed = self.view.tree_widget.isHidden()
        if is_collapsed:
            self.view.tree_widget.show()
            self.view.left_bottom_bar.show()
            self.view.lbl_left_title.show()
            self.view.left_widget.setMaximumWidth(16777215)
            self.view.left_widget.setMinimumWidth(150)
            sizes = self.view.splitter.sizes()
            sizes[0] = self.view.last_left_width
            self.view.splitter.setSizes(sizes)
            self.view.btn_toggle_left.setIcon(create_custom_icon("arrow", self.view.arrow_icon_color, self.view.scale_factor, "left"))
            self.view.btn_toggle_left.setToolTip("收折作品面板")
        else:
            sizes = self.view.splitter.sizes()
            if sizes[0] > 40:
                self.view.last_left_width = sizes[0]
            self.view.tree_widget.hide()
            self.view.left_bottom_bar.hide()
            self.view.lbl_left_title.hide()
            self.view.left_widget.setFixedWidth(40)
            self.view.btn_toggle_left.setIcon(create_custom_icon("arrow", self.view.arrow_icon_color, self.view.scale_factor, "right"))
            self.view.btn_toggle_left.setToolTip("展開作品面板")

    def toggle_right_panel(self):
        is_collapsed = self.view.right_panel.main_splitter.isHidden()
        if is_collapsed:
            self.view.right_panel.main_splitter.show()
            self.view.lbl_right_title.show()
            self.view.right_widget.setMaximumWidth(16777215)
            self.view.right_widget.setMinimumWidth(150)
            sizes = self.view.splitter.sizes()
            sizes[2] = self.view.last_right_width
            self.view.splitter.setSizes(sizes)
            self.view.btn_toggle_right.setIcon(create_custom_icon("arrow", self.view.arrow_icon_color, self.view.scale_factor, "right"))
            self.view.btn_toggle_right.setToolTip("收折資料集")
        else:
            sizes = self.view.splitter.sizes()
            if sizes[2] > 40:
                self.view.last_right_width = sizes[2]
            self.view.right_panel.main_splitter.hide()
            self.view.lbl_right_title.hide()
            self.view.right_widget.setFixedWidth(40)
            self.view.btn_toggle_right.setIcon(create_custom_icon("arrow", self.view.arrow_icon_color, self.view.scale_factor, "left"))
            self.view.btn_toggle_right.setToolTip("展開資料集")

    def adjust_global_font(self):
        current_font = FontManager.get_font(family=self.mc.global_font_family, size=self.mc.global_font_size)
        font, ok = QFontDialog.getFont(current_font, self.view, "選擇全文字型")
        if ok:
            self.apply_global_font(font.family(), font.pointSize())

    def adjust_global_size(self):
        size, ok = QInputDialog.getInt(self.view, "調整全文字級", "請輸入字級大小：", value=self.mc.global_font_size, min=6, max=72)
        if ok:
            self.apply_global_font(self.mc.global_font_family, size)

    def apply_global_font(self, family: str, size: int):
        if not family:
            family = FontManager.get_default_font_family()
        self.mc.global_font_family = family
        self.mc.global_font_size = int(size) if size > 0 else 12
        self.mc.project_info.global_font_family = self.mc.global_font_family
        self.mc.project_info.global_font_size = self.mc.global_font_size

        app = QApplication.instance()
        if app:
            app.setFont(FontManager.get_font(family=family, size=10))

        cursor = self.view.editor.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        fmt = QTextCharFormat()
        fmt.setFontFamily(family)
        fmt.setFontPointSize(float(size))
        cursor.mergeCharFormat(fmt)

        self.mc.editor_font_family = family
        self.mc.editor_font_size = int(size)
        self.mc.project_info.editor_font_family = family
        self.mc.project_info.editor_font_size = int(size)

        ed_font = FontManager.get_font(family=family, size=int(size))
        self.view.editor.setFont(ed_font)
        self.view.editor.document().setDefaultFont(ed_font)

        self.view.combo_font.blockSignals(True)
        self.view.combo_font.setCurrentFont(QFont(family))
        self.view.combo_font.blockSignals(False)

        self.view.combo_size.blockSignals(True)
        self.view.combo_size.setCurrentText(str(size))
        self.view.combo_size.blockSignals(False)

        self.set_ui_scale(self.view.scale_factor)

    def apply_editor_font(self, family: str, size: int):
        if not family:
            family = FontManager.get_default_font_family()
        self.mc.editor_font_family = family
        self.mc.editor_font_size = int(size) if size > 0 else 12
        self.mc.project_info.editor_font_family = self.mc.editor_font_family
        self.mc.project_info.editor_font_size = self.mc.editor_font_size

        ed_font = FontManager.get_font(family=family, size=int(size))
        self.view.editor.setFont(ed_font)
        self.view.editor.document().setDefaultFont(ed_font)

        self.view.combo_font.blockSignals(True)
        self.view.combo_font.setCurrentFont(QFont(family))
        self.view.combo_font.blockSignals(False)

        self.view.combo_size.blockSignals(True)
        self.view.combo_size.setCurrentText(str(size))
        self.view.combo_size.blockSignals(False)

    def apply_theme(self, theme_name: str):
        self.view.current_theme = theme_name
        qss = ThemeManager.get_theme_qss(theme_name)

        caption_color = 0x1e1e1e
        text_color = 0xe3e3e3

        if theme_name == "default":
            self.view.folder_icon_color = "#e5c07b"
            self.view.file_icon_color = "#dcdcdc"
            self.view.arrow_icon_color = "#e3e3e3"
            self.view.trash_icon_color = "#e3e3e3"
            caption_color = 0x1e1e1e
            text_color = 0xe3e3e3
            self.view.progress_bar.theme_color_start = QColor("#00e676")
            self.view.progress_bar.theme_color_end = QColor("#69f0ae")
        elif theme_name == "green":
            self.view.folder_icon_color = "#8cb399"
            self.view.file_icon_color = "#c2d6cb"
            self.view.arrow_icon_color = "#d0ded6"
            self.view.trash_icon_color = "#d0ded6"
            caption_color = 0x151b12
            text_color = 0xe0ede5
            self.view.progress_bar.theme_color_start = QColor("#1f4c32")
            self.view.progress_bar.theme_color_end = QColor("#43a047")
        elif theme_name == "celadon":
            self.view.folder_icon_color = "#7ea4b3"
            self.view.file_icon_color = "#bcd2db"
            self.view.arrow_icon_color = "#cbe0e8"
            self.view.trash_icon_color = "#cbe0e8"
            caption_color = 0x211b11
            text_color = 0xcbe0e8
            self.view.progress_bar.theme_color_start = QColor("#1d4e6e")
            self.view.progress_bar.theme_color_end = QColor("#00a8cc")
        elif theme_name == "sepia":
            self.view.folder_icon_color = "#d2b48c"
            self.view.file_icon_color = "#dfd5cc"
            self.view.arrow_icon_color = "#dfd5cc"
            self.view.trash_icon_color = "#dfd5cc"
            caption_color = 0x20262e
            text_color = 0xccd5df
            self.view.progress_bar.theme_color_start = QColor("#6d4c3d")
            self.view.progress_bar.theme_color_end = QColor("#8b5a2b")
        elif theme_name == "polar":
            self.view.folder_icon_color = "#81a1c1"
            self.view.file_icon_color = "#d8dee9"
            self.view.arrow_icon_color = "#d8dee9"
            self.view.trash_icon_color = "#d8dee9"
            caption_color = 0x2a211d
            text_color = 0xe9ded8
            self.view.progress_bar.theme_color_start = QColor("#88c0d0")
            self.view.progress_bar.theme_color_end = QColor("#81a1c1")
        elif theme_name == "forest":
            self.view.folder_icon_color = "#7aa89f"
            self.view.file_icon_color = "#d1dedb"
            self.view.arrow_icon_color = "#d1dedb"
            self.view.trash_icon_color = "#d1dedb"
            caption_color = 0x1a1c15
            text_color = 0xdbded1
            self.view.progress_bar.theme_color_start = QColor("#406b60")
            self.view.progress_bar.theme_color_end = QColor("#528b7c")

        scaled_qss = ThemeManager.scale_qss(qss, self.view.scale_factor)
        self.view.setStyleSheet(scaled_qss)

        if sys.platform == "win32":
            set_window_dark_mode(int(self.view.winId()), caption_color, text_color)

        self.view.progress_bar.update()
        self.update_icons()

    def set_ui_scale(self, scale: float):
        self.view.scale_factor = scale
        current_editor_font = self.view.editor.font()

        fam = self.mc.global_font_family or FontManager.get_default_font_family()
        default_font = FontManager.get_font(family=fam, size=int(9 * scale))
        app = QApplication.instance()
        if app:
            app.setFont(default_font)

        self.view.editor.setFont(current_editor_font)

        # 頂部與編輯區
        self.view.lbl_project_title.setFont(FontManager.get_font(family=fam, size=int(12 * scale), weight=QFont.Weight.Bold))
        if hasattr(self.view, "lbl_project_logline"):
            self.view.lbl_project_logline.setFont(FontManager.get_font(family=fam, size=int(10 * scale)))
        self.view.lbl_left_title.setFont(FontManager.get_font(family=fam, size=int(10 * scale), weight=QFont.Weight.Bold))
        self.view.lbl_right_title.setFont(FontManager.get_font(family=fam, size=int(10 * scale), weight=QFont.Weight.Bold))
        self.view.lbl_current_file.setFont(FontManager.get_font(family=fam, size=int(14 * scale), weight=QFont.Weight.Bold))
        if hasattr(self.view, "lbl_focus_banner"):
            self.view.lbl_focus_banner.setFont(FontManager.get_font(family=fam, size=int(10 * scale)))

        # 格式工具列
        if hasattr(self.view, "combo_font"):
            self.view.combo_font.setFont(FontManager.get_font(family=fam, size=int(9 * scale)))
        if hasattr(self.view, "combo_size"):
            self.view.combo_size.setFont(FontManager.get_font(family=fam, size=int(9 * scale)))
            self.view.combo_size.setFixedWidth(int(70 * scale))
        if hasattr(self.view, "btn_ellipsis"):
            self.view.btn_ellipsis.setFont(FontManager.get_font(family=fam, size=int(10 * scale)))
        if hasattr(self.view, "btn_emdash"):
            self.view.btn_emdash.setFont(FontManager.get_font(family=fam, size=int(10 * scale)))
        if hasattr(self.view, "btn_typewriter"):
            self.view.btn_typewriter.setFont(FontManager.get_font(family=fam, size=int(9 * scale)))

        # 尋找取代列
        if hasattr(self.view, "find_replace_bar") and hasattr(self.view.find_replace_bar, "input_find"):
            self.view.find_replace_bar.input_find.setFont(FontManager.get_font(family=fam, size=int(10 * scale)))
            self.view.find_replace_bar.input_replace.setFont(FontManager.get_font(family=fam, size=int(10 * scale)))

        # 狀態列
        if hasattr(self.view, "lbl_progress"):
            self.view.lbl_progress.setFont(FontManager.get_font(family=fam, size=int(9 * scale)))
        if hasattr(self.view, "progress_bar"):
            self.view.progress_bar.setFixedWidth(int(150 * scale))
            self.view.progress_bar.setFixedHeight(int(14 * scale))
        if hasattr(self.view, "btn_set_target"):
            self.view.btn_set_target.setFont(FontManager.get_font(family=fam, size=int(9 * scale)))
        if hasattr(self.view, "btn_clear_progress"):
            self.view.btn_clear_progress.setFont(FontManager.get_font(family=fam, size=int(9 * scale)))
        if hasattr(self.view, "lbl_word_count"):
            self.view.lbl_word_count.setFont(FontManager.get_font(family=fam, size=int(9 * scale)))
        if hasattr(self.view, "lbl_project_progress"):
            self.view.lbl_project_progress.setFont(FontManager.get_font(family=fam, size=int(9 * scale)))
        if hasattr(self.view, "project_progress_bar"):
            self.view.project_progress_bar.setFixedWidth(int(150 * scale))
            self.view.project_progress_bar.setFixedHeight(int(14 * scale))
        if hasattr(self.view, "btn_set_project_target"):
            self.view.btn_set_project_target.setFont(FontManager.get_font(family=fam, size=int(9 * scale)))

        # 垃圾桶頁面
        if hasattr(self.view, "btn_restore"):
            self.view.btn_restore.setFont(FontManager.get_font(family=fam, size=int(9 * scale)))
        if hasattr(self.view, "btn_delete_permanently"):
            self.view.btn_delete_permanently.setFont(FontManager.get_font(family=fam, size=int(9 * scale)))
        if hasattr(self.view, "btn_clear_trash"):
            self.view.btn_clear_trash.setFont(FontManager.get_font(family=fam, size=int(9 * scale)))
        if hasattr(self.view, "trash_list_widget"):
            self.view.trash_list_widget.setFont(FontManager.get_font(family=fam, size=int(10 * scale)))

        # 面板縮放更新
        if hasattr(self.view, "left_panel") and hasattr(self.view.left_panel, "update_scale"):
            self.view.left_panel.update_scale(scale)
        else:
            self.view.tree_widget.setFont(FontManager.get_font(family=fam, size=int(9 * scale)))
            self.view.tree_widget.setIconSize(QSize(int(16 * scale), int(16 * scale)))
            self.view.btn_toggle_left.setFixedWidth(int(24 * scale))
            self.view.btn_toggle_left.setFixedHeight(int(24 * scale))
            self.view.btn_trash.setFixedWidth(int(24 * scale))
            self.view.btn_trash.setFixedHeight(int(24 * scale))

        if hasattr(self.view, "right_panel") and hasattr(self.view.right_panel, "update_scale"):
            self.view.right_panel.update_scale(scale)
        else:
            self.view.btn_toggle_right.setFixedWidth(int(24 * scale))
            self.view.btn_toggle_right.setFixedHeight(int(24 * scale))

        if hasattr(self.view, "btn_toggle_view_mode"):
            self.view.btn_toggle_view_mode.setFont(FontManager.get_font(family=fam, size=int(9 * scale)))

        for btn in ['btn_add_core_summary', 'btn_add_core_character', 'btn_add_core_world', 'btn_add_core_timeline']:
            if hasattr(self.view, btn):
                getattr(self.view, btn).setFont(FontManager.get_font(family=fam, size=int(9 * scale)))

        for card in self.view.findChildren(CardWidget):
            card.update_scale(scale)

        if hasattr(self.view, "outline_view") and hasattr(self.view.outline_view, "update_scale"):
            self.view.outline_view.update_scale(scale)

        if hasattr(self.view, "writing_log_dashboard") and hasattr(self.view.writing_log_dashboard, "update_scale"):
            self.view.writing_log_dashboard.update_scale(scale)

        if hasattr(self.view, "find_replace_bar") and hasattr(self.view.find_replace_bar, "update_scale"):
            self.view.find_replace_bar.update_scale(scale)

        self.apply_theme(self.view.current_theme)

        self.update_icons()

        if hasattr(self.mc, "app_settings") and isinstance(self.mc.app_settings, dict):
            self.mc.app_settings["scale_factor"] = scale
            if hasattr(self.mc, "app_dir") and self.mc.app_dir:
                AppSettingsService.save_settings(self.mc.app_settings, self.mc.app_dir)

    def update_icons(self):
        self.view.btn_toggle_left.setIcon(create_custom_icon("arrow", self.view.arrow_icon_color, self.view.scale_factor, "left" if not self.view.tree_widget.isHidden() else "right"))
        self.view.btn_toggle_right.setIcon(create_custom_icon("arrow", self.view.arrow_icon_color, self.view.scale_factor, "right" if not self.view.right_panel.main_splitter.isHidden() else "left"))
        self.view.btn_trash.setIcon(create_custom_icon("trash", self.view.trash_icon_color, self.view.scale_factor))

        def update_tree_item(item):
            data = item.data(0, 0x0100) # Qt.ItemDataRole.UserRole
            if data:
                t_type = data.get("type")
                mark = data.get("mark", "None")
                if t_type == "folder":
                    item.setIcon(0, create_custom_icon("folder", self.view.folder_icon_color, self.view.scale_factor))
                elif t_type == "file":
                    if mark != "None" and mark:
                        if mark in MARK_COLOR_MAP:
                            self.mc.tree.set_item_mark(item, MARK_COLOR_MAP[mark], mark)
                    else:
                        item.setIcon(0, create_custom_icon("file", self.view.file_icon_color, self.view.scale_factor))
                elif t_type == "scene":
                    if mark != "None" and mark:
                        if mark in MARK_COLOR_MAP:
                            self.mc.tree.set_item_mark(item, MARK_COLOR_MAP[mark], mark)
                    else:
                        item.setIcon(0, create_custom_icon("folder", "#7EB8F7", self.view.scale_factor))
            for i in range(item.childCount()):
                update_tree_item(item.child(i))

        self.view.tree_widget.blockSignals(True)
        for i in range(self.view.tree_widget.topLevelItemCount()):
            update_tree_item(self.view.tree_widget.topLevelItem(i))
        self.view.tree_widget.blockSignals(False)

