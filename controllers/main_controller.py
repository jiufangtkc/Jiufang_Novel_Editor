import sys
import os
from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import QApplication, QMessageBox, QDialog
from PyQt6.QtCore import QTimer

from views.main_window import MainWindow
from views.dialogs.startup_dialog import StartupDialog
from views.dialogs.initial_scale_dialog import InitialScaleDialog
from utils.theme_manager import set_window_dark_mode
from utils.font_manager import FontManager
from services.database import DatabaseService
from services.app_settings_service import AppSettingsService
from models.models import ProjectInfo, WritingLogEntry

from controllers.tree_controller import TreeController
from controllers.editor_controller import EditorController
from controllers.stats_controller import StatsController
from controllers.project_controller import ProjectController
from controllers.theme_controller import ThemeController
from controllers.card_controller import CardController
from controllers.export_controller import ExportController
from controllers.import_controller import ImportController
from controllers.ai_controller import AIController
from controllers.search_controller import SearchController
from controllers.snapshot_controller import SnapshotController
from controllers.backup_controller import BackupController
from controllers.autosave_controller import AutosaveController

class MainController:
    """主控制器（聚合器），負責協調各子控制器、持有共享狀態並連接 UI 信號。"""

    def __init__(self, view: MainWindow, interactive_startup: bool = False, app_dir: Optional[str] = None):
        self.view = view
        self.interactive_startup = interactive_startup

        # 全域字型與編輯狀態
        default_font_fam = FontManager.get_default_font_family()
        self.is_wysiwyg_mode: bool = False
        self.typewriter_mode: bool = False
        self.global_font_family: str = default_font_fam
        self.global_font_size: int = 12
        self.editor_font_family: str = default_font_fam
        self.editor_font_size: int = 12

        # 專案共享核心資料（統一採用 dataclass）
        self.project_info: ProjectInfo = ProjectInfo(
            title="請點擊輸入書名",
            logline="點擊輸入一句話大綱(logline)",
            global_font_family=default_font_fam,
            global_font_size=12,
            editor_font_family=default_font_fam,
            editor_font_size=12
        )
        self.project_cards: Dict[str, list] = {
            "summary": [], "character": [], "world": [], "timeline": [], "ai_chat": []
        }
        self._project_category_order: list = [
            "summary", "character", "world", "timeline", "ai_chat"
        ]
        self.writing_logs: List[WritingLogEntry] = []
        self.file_word_stats: Dict[str, dict] = {}
        self.trash_bin: list = []

        # 編輯與寫作追蹤狀態
        self.current_file_item = None
        self.today_target: int = getattr(self.project_info, "daily_target_word_count", 1000)
        self.today_written_count: int = 0
        self.current_file_last_word_count: int = 0
        self.last_known_word_count: int = 0
        self.active_session: Optional[dict] = None
        self.is_dirty: bool = False

        # 寫作閒置檢測計時器
        self.writing_timer = QTimer(self.view)
        self.writing_timer.setInterval(1000)
        self.writing_timer.timeout.connect(self.check_writing_inactivity)
        self.writing_timer.start()

        # 實體化 12 個子控制器
        self.tree = TreeController(self)
        self.editor = EditorController(self)
        self.stats = StatsController(self)
        self.project = ProjectController(self)
        self.autosave = AutosaveController(self)
        self.theme = ThemeController(self)
        self.card = CardController(self)
        self.export_controller = ExportController(self)
        self.import_controller = ImportController(self)
        self.ai_controller = AIController(self)
        self.search = SearchController(self)
        self.snapshot = SnapshotController(self)
        self.backup = BackupController(self)

        # 連結 View 信號
        self.connect_signals()

        # 初始化預設狀態
        self.update_project_labels()
        self.update_status_bar()
        if sys.platform == "win32":
            set_window_dark_mode(int(self.view.winId()))

        self.should_exit: bool = False

        # 自動防護目錄與全域設定初始化
        if not app_dir:
            local_app_data = os.environ.get('LOCALAPPDATA')
            if not local_app_data:
                local_app_data = os.path.join(os.path.expanduser('~'), 'AppData', 'Local')
            app_dir = os.path.join(local_app_data, 'Jiufang_Novel_Editor')
        self.app_dir = app_dir

        # 載入並套用前一次關閉編輯器時的介面大小與設定
        is_first_launch = AppSettingsService.is_first_launch(self.app_dir)
        self.app_settings = AppSettingsService.load_settings(self.app_dir)
        AppSettingsService.apply_to_window(self.view, self.app_settings)

        # 確保當前生效之存檔目錄 (Story / Temp_doc) 初始化
        curr_storage_path = self.get_storage_path()
        from services.storage_migration_service import StorageMigrationService
        StorageMigrationService.ensure_storage_directories(curr_storage_path)

        # 第一次乾淨開啟時，預設介面在 100%，並詢問使用者的偏好介面大小
        if is_first_launch:
            self.theme.set_ui_scale(1.0)
            if self.interactive_startup:
                scale_dlg = InitialScaleDialog(self.view)
                if scale_dlg.exec() == QDialog.DialogCode.Accepted:
                    chosen_scale = scale_dlg.selected_scale
                    self.theme.set_ui_scale(chosen_scale)
                    self.app_settings["scale_factor"] = chosen_scale
            self.app_settings["has_completed_initial_setup"] = True
            AppSettingsService.save_settings(self.app_settings, self.app_dir)
        elif "scale_factor" in self.app_settings and self.app_settings["scale_factor"] != 1.0:
            self.theme.set_ui_scale(self.app_settings["scale_factor"])

        # 啟動前先套用完整主題與配色，確保視窗背景與對話框顏色正常
        self.theme.apply_theme(self.view.current_theme)

        self.autosave_interval_minutes = int(self.app_settings.get("autosave_interval_minutes", 10))
        self.autosave_max_files = int(self.app_settings.get("autosave_max_files", 100))

        # Crash 判定與啟動選擇
        was_crash = bool(self.app_settings.get("session_active", False) or not self.app_settings.get("last_exit_normal", True))
        temp_dir = self.get_temp_dir()
        has_temp = os.path.exists(temp_dir) and any(
            f.lower().endswith(".db") and os.path.isfile(os.path.join(temp_dir, f)) and os.path.getsize(os.path.join(temp_dir, f)) > 0
            for f in os.listdir(temp_dir)
        )

        if was_crash and has_temp:
            # 只有在 Crash 的時候，才會自動打開暫存檔
            loaded = self.project.auto_load_latest_temp()
            if loaded:
                if self.interactive_startup:
                    QMessageBox.information(self.view, "恢復暫存", "已恢復當機前最新的一個暫存檔。")
            else:
                self.project.init_default_project()
        else:
            # 正常啟動流程
            if self.interactive_startup:
                self._handle_startup_choice()
            else:
                self.project.init_default_project()

        if self.should_exit:
            self.writing_timer.stop()
            self.app_settings["session_active"] = False
            self.app_settings["last_exit_normal"] = True
            AppSettingsService.save_settings(self.app_settings, self.app_dir)
            return

        # 標記當前 session 為活躍（若中途崩潰則下次判定為 Crash）
        self.app_settings["session_active"] = True
        self.app_settings["last_exit_normal"] = False
        AppSettingsService.save_settings(self.app_settings, self.app_dir)

        # 設定自動儲存計時器
        self.auto_save_timer = QTimer(self.view)
        self.auto_save_timer.setInterval(self.autosave_interval_minutes * 60 * 1000)
        self.auto_save_timer.timeout.connect(lambda: self.save_temp_doc(from_timer=True))
        self.auto_save_timer.start()

    def _handle_startup_choice(self):
        """處理正常啟動時使用者的選擇：開啟新專案、讀取上次寫的專案、讀取專案存檔、讀取暫存檔。"""
        while True:
            dialog = StartupDialog(self.view)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                if dialog.selected_action == "new":
                    self.project.init_default_project()
                    break
                elif dialog.selected_action == "open_latest":
                    opened = self.project.load_latest_story_project(notify_if_empty=True)
                    if opened:
                        break
                elif dialog.selected_action == "open":
                    opened = self.project.load_project_file_prompt()
                    if opened:
                        break
                elif dialog.selected_action == "open_temp":
                    opened = self.project.load_temp_file_prompt()
                    if opened:
                        break
                else:
                    self.project.init_default_project()
                    break
            else:
                # 使用者在歡迎視窗按下 X 關閉，直接結束程式
                self.should_exit = True
                break

    def get_writing_logs_as_dict(self) -> List[dict]:
        """將 WritingLogEntry 清單轉換為 UI Dashboard 需要的 dict 清單。"""
        return [
            {
                "date": log.date,
                "duration": log.duration,
                "word_count": log.word_count,
                "ai_continuation_count": getattr(log, "ai_continuation_count", 0),
                "ai_continuation_chars": getattr(log, "ai_continuation_chars", 0),
                "ai_chat_count": getattr(log, "ai_chat_count", 0),
                "ai_details": dict(getattr(log, "ai_details", {})),
                "paste_large_count": getattr(log, "paste_large_count", 0),
                "delete_large_count": getattr(log, "delete_large_count", 0)
            }
            for log in self.writing_logs
        ]


    def connect_signals(self):
        # 覆寫 closeEvent
        self.view.closeEvent = self.project.on_close_event

        # View 自訂信號
        self.view.signal_edit_project_title.connect(self.project.edit_project_title)
        self.view.signal_edit_logline.connect(self.project.edit_logline)
        self.view.signal_tree_context_menu.connect(self.tree.show_tree_context_menu)

        # 左面板 (Left Panel)
        self.view.btn_toggle_left.clicked.connect(self.theme.toggle_left_panel)
        self.view.btn_trash.clicked.connect(self.tree.show_trash_page)
        self.view.tree_widget.itemClicked.connect(self.tree.on_tree_item_clicked)
        self.view.tree_widget.itemChanged.connect(self.tree.on_tree_item_changed)

        # 中央編輯器面板 (Center Panel)
        self.view.combo_font.currentFontChanged.connect(self.editor.change_font)
        self.view.combo_size.currentTextChanged.connect(self.editor.change_font_size)
        self.view.btn_ellipsis.clicked.connect(lambda: self.view.editor.insertPlainText("……"))
        self.view.btn_emdash.clicked.connect(lambda: self.view.editor.insertPlainText("──"))
        self.view.btn_typewriter.toggled.connect(self.editor.toggle_typewriter)

        self.view.editor.textChanged.connect(self.editor.on_editor_text_changed)
        self.view.editor.cursorPositionChanged.connect(self.editor.on_cursor_position_changed)
        self.view.editor.document().contentsChange.connect(self.stats.on_document_contents_change)
        if hasattr(self.view.editor, "signal_text_pasted"):
            self.view.editor.signal_text_pasted.connect(self.stats.on_text_pasted)

        self.view.btn_set_target.clicked.connect(self.stats.set_daily_target)
        self.view.btn_clear_progress.clicked.connect(self.stats.clear_daily_progress)
        if hasattr(self.view, "btn_set_project_target"):
            self.view.btn_set_project_target.clicked.connect(self.stats.set_project_target)
        self.view.btn_restore.clicked.connect(self.tree.restore_selected_trash_item)
        self.view.btn_delete_permanently.clicked.connect(self.tree.delete_selected_trash_item_permanently)
        self.view.btn_clear_trash.clicked.connect(self.tree.clear_all_trash)
        self.view.trash_list_widget.customContextMenuRequested.connect(self.tree.show_trash_context_menu)

        # 右面板 (Right Panel)
        self.view.btn_toggle_right.clicked.connect(self.theme.toggle_right_panel)
        self.card.connect_signals()  # CardController 統一管理右面板信號連接
        self.view.btn_save_scene_info.clicked.connect(self.tree.save_scene_info)

        # 編輯與搜尋 (Edit & Search)
        self.view.find_replace_bar.signal_text_changed.connect(lambda _: self.search.update_search())
        self.view.find_replace_bar.signal_options_changed.connect(self.search.update_search)
        self.view.find_replace_bar.signal_find_next.connect(self.search.find_next)
        self.view.find_replace_bar.signal_find_prev.connect(self.search.find_prev)
        self.view.find_replace_bar.signal_replace.connect(self.search.replace)
        self.view.find_replace_bar.signal_replace_all.connect(self.search.replace_all)
        self.view.find_replace_bar.signal_closed.connect(self.search.close_find_bar)

        self.view.action_find.triggered.connect(self.search.open_find)
        self.view.action_replace.triggered.connect(self.search.open_replace)
        self.view.action_global_search.triggered.connect(self.search.open_global_search_dialog)

        # 檢視模式與大綱 (Views & Outline)
        self.view.action_show_write.triggered.connect(self.tree.show_write_page)
        self.view.action_show_outline.triggered.connect(self.tree.show_outline_page)
        self.view.action_toggle_focus.triggered.connect(self.view.toggle_focus_mode)

        self.view.outline_view.signal_chapter_selected.connect(self.tree.open_chapter_by_id)
        self.view.outline_view.signal_back_to_editor.connect(self.tree.show_write_page)
        self.view.outline_view.signal_mark_changed.connect(self.tree.set_chapter_mark_by_id)

        # 選單動作 (Menus)
        self.view.action_new_book.triggered.connect(self.project.new_book)
        self.view.action_save_project.triggered.connect(lambda: self.project.save_project(silent=True))
        self.view.action_save_project_as.triggered.connect(self.project.save_project_as)
        self.view.action_export.triggered.connect(lambda: self.export_single_document())
        if hasattr(self.view, "action_import"):
            self.view.action_import.triggered.connect(lambda: self.import_controller.show_import_dialog())
        if hasattr(self.view, "action_load_latest_project"):
            self.view.action_load_latest_project.triggered.connect(self.project.load_latest_story_project)
        self.view.action_load_project.triggered.connect(self.project.load_project)
        if hasattr(self.view, "action_load_temp_project"):
            self.view.action_load_temp_project.triggered.connect(self.project.load_temp_file_prompt)
        self.view.action_snapshot_manager.triggered.connect(self.snapshot.manage_snapshots)
        self.view.action_export_backup.triggered.connect(self.backup.export_backup_zip)
        self.view.action_restore_backup.triggered.connect(self.backup.restore_from_backup_zip)
        self.view.action_exit.triggered.connect(self.view.close)
        self.view.action_adjust_global_font.triggered.connect(self.theme.adjust_global_font)
        self.view.action_adjust_global_size.triggered.connect(self.theme.adjust_global_size)

        self.view.action_show_writing_log.triggered.connect(self.stats.show_writing_log_dashboard)
        self.view.action_lint.triggered.connect(self.editor.open_lint_dialog)

        # 設定 (Settings)
        if hasattr(self.view, "action_autosave_settings"):
            self.view.action_autosave_settings.triggered.connect(self.project.open_autosave_settings_dialog)
        if hasattr(self.view, "action_storage_path_settings"):
            self.view.action_storage_path_settings.triggered.connect(self.project.open_storage_path_dialog)
        if hasattr(self.view, "action_word_count_settings"):
            self.view.action_word_count_settings.triggered.connect(self.stats.open_word_count_settings_dialog)


        # 主題 (Themes)
        self.view.action_theme_default.triggered.connect(lambda: self.theme.apply_theme("default"))
        self.view.action_theme_green.triggered.connect(lambda: self.theme.apply_theme("green"))
        self.view.action_theme_celadon.triggered.connect(lambda: self.theme.apply_theme("celadon"))
        self.view.action_theme_sepia.triggered.connect(lambda: self.theme.apply_theme("sepia"))
        self.view.action_theme_polar.triggered.connect(lambda: self.theme.apply_theme("polar"))
        self.view.action_theme_forest.triggered.connect(lambda: self.theme.apply_theme("forest"))

        # AI 助手 (AI Assistant)
        self.view.action_ai_chat.triggered.connect(lambda: self.ai_controller.open_ai_chat_dialog())
        self.view.action_ai_continuation.triggered.connect(self.ai_controller.trigger_ai_continuation)
        self.view.action_ai_settings.triggered.connect(self.ai_controller.open_ai_settings_dialog)
        self.view.action_ai_impression.triggered.connect(lambda: self.ai_controller.trigger_ai_analysis("impression"))
        self.view.action_ai_character.triggered.connect(lambda: self.ai_controller.trigger_ai_analysis("character"))
        self.view.action_ai_world.triggered.connect(lambda: self.ai_controller.trigger_ai_analysis("world"))
        self.view.action_ai_timeline.triggered.connect(lambda: self.ai_controller.trigger_ai_analysis("timeline"))
        self.view.action_ai_proofread.triggered.connect(self.ai_controller.open_ai_proofread_dialog)
        self.view.editor.signal_ai_analyze.connect(self.ai_controller.handle_editor_ai_analyze)
        self.view.editor.signal_ai_chat.connect(self.ai_controller.open_ai_chat_dialog)
        self.view.editor.signal_ai_continuation.connect(self.ai_controller.trigger_ai_continuation)

        # UI 縮放 (Scale)
        for val, act in self.view.scale_actions.items():
            act.triggered.connect(lambda checked, v=val: self.theme.set_ui_scale(v))

    # =========================================================================
    # 轉發方法（轉發至子控制器，維持介面 100% 相容性）
    # =========================================================================

    def mark_dirty(self, dirty: bool = True):
        """標記專案是否有未儲存的變更，並連動更新視窗標題與相關標籤。"""
        if getattr(self, "is_dirty", False) != dirty:
            self.is_dirty = dirty
            self.update_project_labels()

    def update_project_labels(self):
        self.project.update_project_labels()

    def update_status_bar(self):
        self.stats.update_status_bar()

    def save_current_editor_content(self):
        self.editor.save_current_editor_content()

    def save_temp_doc(self, from_timer: bool = False):
        self.project.save_temp_doc(from_timer=from_timer)

    def save_project(self, silent: bool = True) -> bool:
        return self.project.save_project(silent=silent)

    def save_project_as(self) -> bool:
        return self.project.save_project_as()

    def load_project(self):
        self.project.load_project()

    def load_project_data(self, data):
        self.project.load_project_data(data)

    def get_project_data(self) -> dict:
        return self.project.get_project_data()

    def _build_jne_project(self):
        return self.project._build_jne_project()

    def flush_active_writing_session(self):
        self.stats.flush_active_writing_session()

    def check_writing_inactivity(self):
        self.stats.check_writing_inactivity()

    def apply_theme(self, theme_name: str):
        self.theme.apply_theme(theme_name)

    def set_ui_scale(self, scale: float):
        self.theme.set_ui_scale(scale)

    def apply_global_font(self, family: str, size: int):
        self.theme.apply_global_font(family, size)

    def apply_editor_font(self, family: str, size: int):
        self.theme.apply_editor_font(family, size)

    def serialize_card(self, card_widget):
        return self.card.serialize_card(card_widget)

    def serialize_all_cards(self):
        return self.card.serialize_all_cards()

    def deserialize_card(self, card_data, parent_layout, parent_widget=None):
        self.card.deserialize_card(card_data, parent_layout, parent_widget)

    def deserialize_all_cards(self, cards_data):
        self.card.deserialize_all_cards(cards_data)

    def clear_cards_ui(self):
        self.card.clear_cards_ui()

    def update_cards_buttons_state(self):
        self.card.update_cards_buttons_state()

    def export_single_document(self, item=None):
        self.export_controller.export_documents(item)

    def open_ai_settings_dialog(self):
        self.ai_controller.open_ai_settings_dialog()

    def open_ai_chat_dialog(self, context_text: str = ""):
        self.ai_controller.open_ai_chat_dialog(context_text)

    def trigger_ai_continuation(self):
        self.ai_controller.trigger_ai_continuation()

    def handle_editor_ai_analyze(self, task_type: str, text: str):
        self.ai_controller.handle_editor_ai_analyze(task_type, text)

    def trigger_ai_analysis(self, task_type: str):
        self.ai_controller.trigger_ai_analysis(task_type)

    def start_ai_analysis(self, task_type: str, text: str, chapter_title: str = ""):
        self.ai_controller.start_ai_analysis(task_type, text, chapter_title)

    def is_item_valid(self, item) -> bool:
        return self.tree.is_item_valid(item)

    def get_item_id(self, item) -> str:
        return self.tree.get_item_id(item)

    def get_item_path_string(self, item) -> str:
        return self.tree.get_item_path_string(item)

    def add_card_from_ai(self, category: str, title: str, content: str, summary: str = "", tags: list = None):
        self.ai_controller.add_card_from_ai(category, title, content, summary, tags)

    def open_autosave_settings_dialog(self):
        self.project.open_autosave_settings_dialog()

    def open_storage_path_dialog(self):
        self.project.open_storage_path_dialog()

    def get_storage_path(self) -> str:
        """取得當前生效之專案存檔根目錄路徑。"""
        return AppSettingsService.get_current_storage_path(
            settings=getattr(self, "app_settings", None),
            app_dir=getattr(self, "app_dir", None)
        )

    def get_story_dir(self) -> str:
        """取得當前生效之 Story 稿件目錄路徑。"""
        return AppSettingsService.get_story_dir(self.get_storage_path())

    def get_temp_dir(self) -> str:
        """取得當前生效之 Temp_doc 暫存檔目錄路徑。"""
        return AppSettingsService.get_temp_dir(self.get_storage_path())

    def get_export_dir(self) -> str:
        """取得當前生效之 Export 匯出目錄路徑。"""
        return AppSettingsService.get_export_dir(self.get_storage_path())

