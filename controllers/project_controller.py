import os
import sys
import re
import datetime
import uuid
from typing import Union
from PyQt6.QtWidgets import (
    QMessageBox, QInputDialog, QFileDialog, QDialog
)
from PyQt6.QtCore import Qt
from models.models import JneProject, ProjectInfo, ChapterNode, CardNode, WritingLogEntry, MARK_COLOR_MAP
from services.database import DatabaseService
from services.app_settings_service import AppSettingsService
from views.dialogs.new_book_dialog import NewBookDialog
from views.dialogs.autosave_settings_dialog import AutosaveSettingsDialog
from utils.font_manager import FontManager
from utils.theme_manager import ThemeManager
from utils.file_utils import get_temp_db_sort_key

class ProjectController:
    """負責專案生命週期、專案標題/簡介編輯、SQLite 存檔/另存/讀檔/暫存與 Dataclass 序列化。"""

    def __init__(self, main_controller):
        self.mc = main_controller
        self.current_project_path: str = ""

    @property
    def view(self):
        return self.mc.view

    def update_project_labels(self):
        title = self.mc.project_info.title.strip() if self.mc.project_info.title else ""
        self.view.lbl_project_title.setText(title if title else '請點擊輸入書名')
        logline = self.mc.project_info.logline.strip() if self.mc.project_info.logline else ""
        self.view.lbl_project_logline.setText(logline if logline else '點擊輸入一句話大綱(logline)')

    def edit_project_title(self, event):
        curr_title = self.mc.project_info.title if self.mc.project_info.title not in ("請點擊輸入書名", "請點擊兩下輸入書名", "點擊此處輸入書名") else ""
        new_title, ok = QInputDialog.getText(self.view, "修改書名", "請輸入新的書名:", text=curr_title)
        if ok and new_title.strip():
            new_title = new_title.strip()
            self.mc.project_info.title = new_title
            self.update_project_labels()

    def edit_logline(self, event):
        curr_logline = self.mc.project_info.logline if self.mc.project_info.logline not in ("點擊輸入一句話大綱(logline)", "點擊兩下輸入一句話大綱(logline)", "點擊此處輸入一句話大綱(logline)") else ""
        new_logline, ok = QInputDialog.getText(self.view, "修改 Logline", "請輸入新的 Logline:", text=curr_logline)
        if ok:
            self.mc.project_info.logline = new_logline.strip()
            self.update_project_labels()

    def _reset_project_state(self, title: str, logline: str):
        default_font_fam = FontManager.get_default_font_family()
        self.mc.global_font_family = default_font_fam
        self.mc.global_font_size = 12
        self.mc.editor_font_family = default_font_fam
        self.mc.editor_font_size = 12

        self.mc.project_info = ProjectInfo(
            title=title,
            logline=logline,
            global_font_family=default_font_fam,
            global_font_size=12,
            editor_font_family=default_font_fam,
            editor_font_size=12
        )
        self.mc.project_cards = {"summary": [], "character": [], "world": [], "timeline": [], "ai_chat": []}
        self.mc._project_category_order = ["summary", "character", "world", "timeline", "ai_chat"]
        self.mc.card.clear_cards_ui()
        self.update_project_labels()
        self.mc.current_file_item = None
        self.view.tree_widget.clear()
        self.view.editor.clear()

        self.mc.theme.apply_global_font(self.mc.global_font_family, self.mc.global_font_size)
        self.mc.theme.apply_editor_font(self.mc.editor_font_family, self.mc.editor_font_size)
        self.mc.theme.set_ui_scale(1.0)
        self.mc.app_settings["scale_factor"] = 1.0
        AppSettingsService.save_settings(self.mc.app_settings, self.mc.app_dir)
        self.view.lbl_current_file.setText("請選擇左側文件進行編輯")

        self.mc.file_word_stats.clear()
        self.mc.today_written_count = 0
        self.mc.current_file_last_word_count = 0
        self.mc.writing_logs = []
        self.mc.active_session = None
        self.mc.last_known_word_count = 0
        self.view.writing_log_dashboard.refresh_data(self.mc.get_writing_logs_as_dict())

        # 建立預設樹狀結構：第一卷 -> 第一章 -> 第一幕
        vol_item = self.mc.tree.create_item("第一卷", is_folder=True)
        self.view.tree_widget.addTopLevelItem(vol_item)
        chap_item = self.mc.tree.create_item("第一章", is_folder=False)
        vol_item.addChild(chap_item)
        vol_item.setExpanded(True)
        scene_item = self.mc.tree.create_item("第一幕", is_scene=True)
        chap_item.addChild(scene_item)
        chap_item.setExpanded(True)

        for it in (chap_item, scene_item):
            item_id = self.mc.tree.get_item_id(it)
            if item_id:
                self.mc.file_word_stats[item_id] = {"valid": 0, "spaces": 0, "alpha": 0, "sym": 0}

        self.mc.update_status_bar()
        self.view.tree_widget.setCurrentItem(scene_item)
        self.mc.tree.on_tree_item_clicked(scene_item, 0)

    def new_book(self):
        dialog = NewBookDialog(self.view)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            title, logline = dialog.get_data()
            if not title:
                title = "請點擊輸入書名"
            if not logline:
                logline = "點擊輸入一句話大綱(logline)"
            self._reset_project_state(title, logline)

    def init_default_project(self):
        self._reset_project_state("請點擊輸入書名", "點擊輸入一句話大綱(logline)")

    def auto_load_latest_temp(self) -> bool:
        """軟體啟動時自動檢查 Temp_doc 與存檔目錄，並優先載入最新暫存檔。"""
        temp_dir = os.path.join(self.mc.app_dir, "Temp_doc")

        # 1. 優先檢查 Temp_doc 下的 .db 暫存檔
        if os.path.exists(temp_dir):
            db_files = [
                os.path.join(temp_dir, f) for f in os.listdir(temp_dir)
                if f.lower().endswith(".db") and os.path.isfile(os.path.join(temp_dir, f))
            ]
            db_files = [f for f in db_files if os.path.getsize(f) > 0]
            if db_files:
                db_files.sort(key=get_temp_db_sort_key, reverse=True)
                for db_file in db_files:
                    try:
                        loaded_project = DatabaseService.load_project(db_file)
                        if loaded_project and (loaded_project.tree or (loaded_project.project_info and loaded_project.project_info.title)):
                            self.load_project_data(loaded_project)
                            return True
                    except Exception as e:
                        print(f"嘗試載入暫存檔 {db_file} 失敗: {e}", file=sys.stderr)

            # 2. 若無可用 .db 檔案，檢查是否有舊版 .json 暫存檔
            json_files = [
                os.path.join(temp_dir, f) for f in os.listdir(temp_dir)
                if f.lower().endswith(".json") and os.path.isfile(os.path.join(temp_dir, f))
            ]
            json_files = [f for f in json_files if os.path.getsize(f) > 0]
            if json_files:
                json_files.sort(key=get_temp_db_sort_key, reverse=True)
                for json_file in json_files:
                    try:
                        from services.storage import StorageService
                        data = StorageService.load_data(json_file)
                        if data:
                            self.load_project_data(data)
                            return True
                    except Exception as e:
                        print(f"嘗試載入舊版 JSON 暫存檔 {json_file} 失敗: {e}", file=sys.stderr)

        # 3. 若 Temp_doc 無可用暫存檔，檢查 story/ 正式存檔目錄作為保底
        story_dir = os.path.join(self.mc.app_dir, "story")
        if os.path.exists(story_dir):
            story_files = []
            for root, _, files in os.walk(story_dir):
                for f in files:
                    if f.lower().endswith(".db"):
                        full_p = os.path.join(root, f)
                        if os.path.isfile(full_p) and os.path.getsize(full_p) > 0:
                            story_files.append(full_p)
            if story_files:
                story_files.sort(key=get_temp_db_sort_key, reverse=True)
                for s_file in story_files:
                    try:
                        loaded_project = DatabaseService.load_project(s_file)
                        if loaded_project:
                            self.load_project_data(loaded_project)
                            self.current_project_path = s_file
                            return True
                    except Exception as e:
                        print(f"嘗試載入正式存檔 {s_file} 失敗: {e}", file=sys.stderr)

        return False

    def clean_files_limit(self, folder_path: str, limit: int = None):
        if limit is None:
            limit = getattr(self.mc, "autosave_max_files", 100)
        if not os.path.exists(folder_path):
            return
        try:
            files = [os.path.join(folder_path, f) for f in os.listdir(folder_path)]
            files = [f for f in files if os.path.isfile(f)]
            if len(files) > limit:
                files.sort(key=get_temp_db_sort_key)
                delete_count = len(files) - limit
                for i in range(delete_count):
                    try:
                        os.remove(files[i])
                    except Exception:
                        pass
        except Exception:
            pass

    def on_close_event(self, event):
        self.mc.flush_active_writing_session()
        self.save_temp_doc()
        # 儲存介面調整的大小與偏好設定，並標記正常退出
        settings = AppSettingsService.extract_from_window(self.view)
        settings["autosave_interval_minutes"] = getattr(self.mc, "autosave_interval_minutes", 10)
        settings["autosave_max_files"] = getattr(self.mc, "autosave_max_files", 100)
        settings["last_exit_normal"] = True
        settings["session_active"] = False
        if hasattr(self, "current_project_path") and self.current_project_path:
            settings["last_project_path"] = self.current_project_path
        self.mc.app_settings.update(settings)
        AppSettingsService.save_settings(self.mc.app_settings, self.mc.app_dir)
        event.accept()

    def _build_jne_project(self) -> JneProject:
        """從 UI 與共享狀態建構 JneProject dataclass。"""
        self.mc.save_current_editor_content()

        project = JneProject(
            project_info=ProjectInfo(
                title=self.mc.project_info.title,
                logline=self.mc.project_info.logline,
                global_font_family=self.mc.global_font_family,
                global_font_size=self.mc.global_font_size,
                editor_font_family=self.mc.editor_font_family,
                editor_font_size=self.mc.editor_font_size
            ),
            current_theme=self.view.current_theme
        )

        # 直接從 mc.project_cards（CardNode 列表）填入 project
        for cat, card_list in self.mc.project_cards.items():
            project.project_cards[cat] = list(card_list)
        # 填入額外分類（如有自訂分類，確保 project.project_cards 有對應 key）
        # 加入 category_order
        project.category_order = getattr(self.mc, '_project_category_order',
                                         list(self.mc.project_cards.keys()))

        def serialize_tree_item_to_node(item) -> ChapterNode:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            node_type = data.get("type", "file") if data else "file"
            node = ChapterNode(
                name=item.text(0),
                node_type=node_type,
                id=data.get("id", str(uuid.uuid4())) if data else str(uuid.uuid4()),
                content=data.get("content", "") if data and node_type in ("file", "scene") else "",
                mark=data.get("mark", "None") if data and node_type in ("file", "scene") else "None",
                scene_summary=data.get("scene_summary", "") if data and node_type == "scene" else "",
                scene_pov=data.get("scene_pov", "") if data and node_type == "scene" else "",
                scene_location=data.get("scene_location", "") if data and node_type == "scene" else ""
            )
            for i in range(item.childCount()):
                node.children.append(serialize_tree_item_to_node(item.child(i)))
            return node

        for i in range(self.view.tree_widget.topLevelItemCount()):
            top_node = serialize_tree_item_to_node(self.view.tree_widget.topLevelItem(i))
            project.tree.append(top_node)


        for log in self.mc.writing_logs:
            project.writing_logs.append(WritingLogEntry(
                date=log.date,
                duration=log.duration,
                word_count=log.word_count,
                ai_continuation_count=getattr(log, "ai_continuation_count", 0),
                ai_continuation_chars=getattr(log, "ai_continuation_chars", 0),
                ai_chat_count=getattr(log, "ai_chat_count", 0)
            ))

        return project

    def _migrate_legacy_dict_to_jne_project(self, data: dict) -> JneProject:
        """將舊版 JSON 專案字典轉換為 JneProject dataclass。"""
        p_dict = data.get("project", {})
        title = p_dict.get("title", "未命名專案")
        logline = p_dict.get("logline", "")
        default_fam = FontManager.get_default_font_family()
        global_fam = data.get("global_font_family") or p_dict.get("global_font_family") or default_fam
        global_sz = int(data.get("global_font_size") or p_dict.get("global_font_size", 12))
        editor_fam = data.get("editor_font_family") or p_dict.get("editor_font_family") or default_fam
        editor_sz = int(data.get("editor_font_size") or p_dict.get("editor_font_size", 12))

        project = JneProject(
            project_info=ProjectInfo(
                title=title, logline=logline,
                global_font_family=global_fam, global_font_size=global_sz,
                editor_font_family=editor_fam, editor_font_size=editor_sz
            ),
            current_theme=data.get("current_theme", "default")
        )

        def parse_dict_node(node_data: dict) -> ChapterNode:
            c_node = ChapterNode(
                name=node_data.get("name", ""),
                node_type=node_data.get("type", "file"),
                id=node_data.get("id", str(uuid.uuid4())),
                content=node_data.get("content", ""),
                mark=node_data.get("mark", "None")
            )
            for ch in node_data.get("children", []):
                c_node.children.append(parse_dict_node(ch))
            return c_node

        for tr in data.get("tree", []):
            project.tree.append(parse_dict_node(tr))

        cards_source = p_dict.get("cards", {})
        for cat in ["summary", "character", "world", "timeline"]:
            if cat in cards_source:
                def parse_card_dict(cd: dict) -> CardNode:
                    c_card = CardNode(
                        title=cd.get("title", ""),
                        id=cd.get("id", str(uuid.uuid4())),
                        content=cd.get("content", ""),
                        color=cd.get("color", "#3C3F41"),
                        is_collapsed=cd.get("is_collapsed", False)
                    )
                    for ch in cd.get("children", []):
                        c_card.children.append(parse_card_dict(ch))
                    return c_card
                project.project_cards[cat] = [parse_card_dict(c) for c in cards_source[cat]]

        for log in data.get("writing_logs", []):
            project.writing_logs.append(WritingLogEntry(
                date=log.get("date", log.get("start_time", "").split(" ")[0]),
                duration=log.get("duration", 0),
                word_count=log.get("word_count", 0)
            ))

        return project

    def load_project_data(self, data: Union[JneProject, dict]):
        """載入專案資料（支援 JneProject dataclass 與相容 legacy dict）。"""
        if isinstance(data, dict):
            project = self._migrate_legacy_dict_to_jne_project(data)
        else:
            project = data

        self.mc.project_info = project.project_info

        # 套用字型
        self.mc.theme.apply_global_font(project.project_info.global_font_family, project.project_info.global_font_size)
        self.mc.theme.apply_editor_font(project.project_info.editor_font_family, project.project_info.editor_font_size)

        # 載入卡片（Data-driven：直接把 CardNode 存入 mc.project_cards，再重建樹狀 UI）
        from models.models import BUILTIN_CATEGORIES
        self.mc.project_cards = {}
        for cat, card_list in project.project_cards.items():
            self.mc.project_cards[cat] = list(card_list)  # 直接使用 CardNode 列表
        # 確保所有內建分類存在
        for cat in BUILTIN_CATEGORIES:
            if cat not in self.mc.project_cards:
                self.mc.project_cards[cat] = []
        # 同步 category_order
        loaded_order = getattr(project, 'category_order', None)
        if loaded_order:
            merged = list(loaded_order)
            for builtin in BUILTIN_CATEGORIES:
                if builtin not in merged:
                    merged.append(builtin)
            self.mc._project_category_order = merged
        else:
            self.mc._project_category_order = list(self.mc.project_cards.keys())
        # 重建樹狀導航 UI
        self.mc.card.rebuild_card_tree()

        # 載入日誌
        self.mc.writing_logs = [
            WritingLogEntry(
                date=l.date, duration=l.duration, word_count=l.word_count,
                ai_continuation_count=getattr(l, "ai_continuation_count", 0),
                ai_continuation_chars=getattr(l, "ai_continuation_chars", 0),
                ai_chat_count=getattr(l, "ai_chat_count", 0)
            )
            for l in project.writing_logs
        ]
        self.view.writing_log_dashboard.refresh_data(self.mc.get_writing_logs_as_dict())

        # 主題映射
        internal_theme = ThemeManager.THEME_NAME_MAP.get(project.current_theme, "default")
        self.mc.theme.apply_theme(internal_theme)

        self.update_project_labels()
        self.mc.current_file_item = None
        self.view.tree_widget.blockSignals(True)
        self.view.tree_widget.clear()
        self.view.editor.clear()
        self.mc.theme.apply_editor_font(self.mc.editor_font_family, self.mc.editor_font_size)
        self.view.lbl_current_file.setText("請選擇左側文件進行編輯")

        self.mc.file_word_stats.clear()
        self.mc.today_written_count = 0
        self.mc.current_file_last_word_count = 0

        def deserialize_chapter_node(node: ChapterNode, parent_item=None):
            is_scene = node.node_type == "scene"
            item = self.mc.tree.create_item(
                node.name,
                is_folder=(node.node_type == "folder"),
                is_scene=is_scene
            )
            if node.node_type in ("file", "scene"):
                data = item.data(0, Qt.ItemDataRole.UserRole)
                data["content"] = node.content
                data["mark"] = node.mark
                data["id"] = node.id
                if is_scene:
                    data["scene_summary"] = node.scene_summary
                    data["scene_pov"] = node.scene_pov
                    data["scene_location"] = node.scene_location
                item.setData(0, Qt.ItemDataRole.UserRole, data)

                if node.mark in MARK_COLOR_MAP:
                    self.mc.tree.set_item_mark(item, MARK_COLOR_MAP[node.mark], node.mark)

                if node.id:
                    self.mc.file_word_stats[node.id] = self.mc.stats.analyze_exclusions_from_markdown(node.content)

            if parent_item:
                parent_item.addChild(item)
            else:
                self.view.tree_widget.addTopLevelItem(item)

            for child_node in node.children:
                deserialize_chapter_node(child_node, item)

        for root_chapter in project.tree:
            deserialize_chapter_node(root_chapter)
        self.view.tree_widget.blockSignals(False)


        self.update_project_labels()
        self.mc.update_status_bar()


        def find_first_file(item):
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("type") in ("file", "scene"):
                return item
            for i in range(item.childCount()):
                res = find_first_file(item.child(i))
                if res:
                    return res
            return None

        first_file = None
        for i in range(self.view.tree_widget.topLevelItemCount()):
            first_file = find_first_file(self.view.tree_widget.topLevelItem(i))
            if first_file:
                break
        if first_file:
            self.view.tree_widget.setCurrentItem(first_file)
            self.mc.tree.on_tree_item_clicked(first_file, 0)

        self.mc.last_known_word_count = sum(x["valid"] for x in self.mc.file_word_stats.values())

    def get_project_data(self) -> dict:
        """導出專案資料字典（供相容性需求使用）。"""
        project = self._build_jne_project()
        return {
            "project": {
                "title": project.project_info.title,
                "logline": project.project_info.logline,
                "global_font_family": project.project_info.global_font_family,
                "global_font_size": project.project_info.global_font_size,
                "editor_font_family": project.project_info.editor_font_family,
                "editor_font_size": project.project_info.editor_font_size,
                "cards": self.mc.card.serialize_all_cards()
            },
            "tree": [
                {
                    "name": n.name, "type": n.node_type, "id": n.id,
                    "content": n.content, "mark": n.mark
                }
                for n in project.tree
            ],
            "current_theme": project.current_theme,
            "global_font_family": project.project_info.global_font_family,
            "global_font_size": project.project_info.global_font_size,
            "editor_font_family": project.project_info.editor_font_family,
            "editor_font_size": project.project_info.editor_font_size,
            "writing_logs": self.mc.get_writing_logs_as_dict()
        }

    def open_autosave_settings_dialog(self):
        """開啟暫存與自動存檔設定對話框。"""
        curr_interval = getattr(self.mc, "autosave_interval_minutes", 10)
        curr_max_files = getattr(self.mc, "autosave_max_files", 100)

        dialog = AutosaveSettingsDialog(self.view, interval_minutes=curr_interval, max_files=curr_max_files)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            interval, max_files = dialog.get_settings()
            self.mc.autosave_interval_minutes = interval
            self.mc.autosave_max_files = max_files
            self.mc.auto_save_timer.setInterval(interval * 60 * 1000)

            # 更新並儲存偏好設定
            self.mc.app_settings["autosave_interval_minutes"] = interval
            self.mc.app_settings["autosave_max_files"] = max_files
            AppSettingsService.save_settings(self.mc.app_settings, self.mc.app_dir)

            # 立即執行一次清理上限檢查
            temp_dir = os.path.join(self.mc.app_dir, "Temp_doc")
            self.clean_files_limit(temp_dir, limit=max_files)

            QMessageBox.information(
                self.view,
                "設定成功",
                f"暫存與自動存檔設定已更新！\n\n• 自動存檔間隔：{interval} 分鐘\n• 最多保留暫存檔：{max_files} 個"
            )

    def load_project_file_prompt(self) -> bool:
        """彈出選擇檔案視窗讓使用者選擇要開啟的專案存檔 (.db)。"""
        story_dir = os.path.join(self.mc.app_dir, "story")
        file_path, _ = QFileDialog.getOpenFileName(
            self.view, "讀取專案存檔", story_dir if os.path.exists(story_dir) else "",
            "SQLite 資料庫 (*.db)"
        )
        if not file_path:
            return False
        try:
            project = DatabaseService.load_project(file_path)
            self.load_project_data(project)
            self.current_project_path = file_path
            self.mc.app_settings["last_project_path"] = file_path
            AppSettingsService.save_settings(self.mc.app_settings, self.mc.app_dir)
            return True
        except Exception as e:
            QMessageBox.critical(self.view, "錯誤", f"讀取專案存檔失敗: {e}")
            return False

    def save_temp_doc(self):
        """暫存使用 SQLite .db 格式"""
        self.mc.flush_active_writing_session()
        try:
            temp_dir = os.path.join(self.mc.app_dir, "Temp_doc")
            os.makedirs(temp_dir, exist_ok=True)

            project = self._build_jne_project()
            now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_file_name = f"temp_{now_str}.db"
            temp_file_path = os.path.join(temp_dir, temp_file_name)

            DatabaseService.save_project(project, temp_file_path)
            max_files = getattr(self.mc, "autosave_max_files", 100)
            self.clean_files_limit(temp_dir, limit=max_files)
        except Exception as e:
            print(f"暫存失敗: {e}", file=sys.stderr)

    def save_project(self):
        """正式存檔為 SQLite .db 格式"""
        self.mc.flush_active_writing_session()
        try:
            story_dir = os.path.join(self.mc.app_dir, "story")
            os.makedirs(story_dir, exist_ok=True)

            book_title = self.mc.project_info.title.strip() if self.mc.project_info.title else ""
            if not book_title:
                book_title = "未命名專案"

            clean_title = re.sub(r'[\/\\\:\*\?\"\'<>\|]', '_', book_title)
            book_dir = os.path.join(story_dir, clean_title)
            os.makedirs(book_dir, exist_ok=True)

            project = self._build_jne_project()
            now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"{clean_title}_{now_str}.db"
            file_path = os.path.join(book_dir, file_name)

            DatabaseService.save_project(project, file_path)
            self.current_project_path = file_path
            self.mc.app_settings["last_project_path"] = file_path
            AppSettingsService.save_settings(self.mc.app_settings, self.mc.app_dir)
            self.clean_files_limit(book_dir, limit=100)
            self.save_temp_doc()
            QMessageBox.information(self.view, "成功", f"稿件已成功儲存至：\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self.view, "錯誤", f"儲存時發生錯誤: {e}")

    def save_project_as(self):
        """另存新檔：採用 SQLite .db 格式"""
        self.mc.flush_active_writing_session()
        file_path, _ = QFileDialog.getSaveFileName(
            self.view, "另存新檔", "",
            "SQLite 資料庫 (*.db)"
        )
        if not file_path:
            return
        if not file_path.lower().endswith('.db'):
            file_path += '.db'
        project = self._build_jne_project()
        try:
            DatabaseService.save_project(project, file_path)
            self.current_project_path = file_path
            self.mc.app_settings["last_project_path"] = file_path
            AppSettingsService.save_settings(self.mc.app_settings, self.mc.app_dir)
            QMessageBox.information(self.view, "成功", f"專案另存成功！\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self.view, "錯誤", f"另存時發生錯誤: {e}")

    def load_project(self):
        """讀取專案：採用 SQLite .db 格式"""
        file_path, _ = QFileDialog.getOpenFileName(
            self.view, "讀取專案", "",
            "SQLite 資料庫 (*.db)"
        )
        if not file_path:
            return
        try:
            project = DatabaseService.load_project(file_path)
            self.load_project_data(project)
            self.current_project_path = file_path
            self.mc.app_settings["last_project_path"] = file_path
            AppSettingsService.save_settings(self.mc.app_settings, self.mc.app_dir)
            QMessageBox.information(self.view, "成功", "專案讀取成功！")
        except Exception as e:
            QMessageBox.critical(self.view, "錯誤", f"讀取時發生錯誤: {e}")

    # =========================================================================
    # Phase 10：快照與備份控制器邏輯
    # =========================================================================

    def get_active_db_path(self) -> str:
        """取得當前可用之 SQLite 資料庫路徑（若無正式存檔則使用最新暫存檔）。"""
        if hasattr(self, 'current_project_path') and self.current_project_path and os.path.isfile(self.current_project_path):
            return self.current_project_path

        # 檢查 Temp_doc 最新暫存檔
        temp_dir = os.path.join(self.mc.app_dir, "Temp_doc")
        if os.path.exists(temp_dir):
            db_files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if f.lower().endswith(".db")]
            db_files = [f for f in db_files if os.path.isfile(f) and os.path.getsize(f) > 0]
            if db_files:
                db_files.sort(key=get_temp_db_sort_key, reverse=True)
                return db_files[0]

        # 若皆無，先觸發一次暫存並回傳該暫存檔
        self.save_temp_doc()
        if os.path.exists(temp_dir):
            db_files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if f.lower().endswith(".db")]
            db_files = [f for f in db_files if os.path.isfile(f) and os.path.getsize(f) > 0]
            if db_files:
                db_files.sort(key=get_temp_db_sort_key, reverse=True)
                return db_files[0]
        return ""

