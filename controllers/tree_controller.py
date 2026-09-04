import uuid
from PyQt6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QMenu, QMessageBox, QInputDialog
)
from PyQt6.QtGui import QAction, QColor, QPixmap, QPainter, QIcon
from PyQt6.QtCore import Qt
from utils.theme_manager import create_custom_icon
from views.dialogs.scene_metadata_dialog import SceneMetadataDialog
from models.models import MARK_COLOR_MAP

class TreeController:
    """負責章節樹 CRUD、拖放、右鍵選單、刪除/復原與標記管理。"""

    def __init__(self, main_controller):
        self.mc = main_controller

    @property
    def view(self):
        return self.mc.view

    def is_item_valid(self, item) -> bool:
        if not item:
            return False
        try:
            item.text(0)
            return True
        except RuntimeError:
            return False

    def get_item_id(self, item) -> str:
        if not self.is_item_valid(item):
            return None
        try:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            return data.get("id") if data else None
        except RuntimeError:
            return None

    def create_item(self, text: str, is_folder: bool = False,
                    content: str = "", is_scene: bool = False) -> QTreeWidgetItem:
        item = QTreeWidgetItem([text])
        item_id = str(uuid.uuid4())
        if is_folder:
            icon = create_custom_icon("folder", self.view.folder_icon_color, self.view.scale_factor)
            item.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder", "id": item_id})
        elif is_scene:
            # scene 節點：使用小型檔案圖示並標注顏色加以區分
            icon = create_custom_icon("folder", "#7EB8F7", self.view.scale_factor)
            item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "scene",
                "content": content,
                "mark": "Draft",
                "id": item_id,
                "scene_summary": "",
                "scene_pov": "",
                "scene_location": "",
                "cards": {"summary": [], "character": [], "world": [], "timeline": []}
            })
        else:
            icon = create_custom_icon("file", self.view.file_icon_color, self.view.scale_factor)
            item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "file",
                "content": content,
                "mark": "None",
                "id": item_id,
                "cards": {"summary": [], "character": [], "world": [], "timeline": []}
            })
        item.setIcon(0, icon)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        return item

    def show_tree_context_menu(self, pos):
        item = self.view.tree_widget.itemAt(pos)
        menu = QMenu(self.view)

        if item:
            node_data = item.data(0, Qt.ItemDataRole.UserRole) or {}
            node_type = node_data.get("type", "")

            # ── 1. 新增項目 ─────────────────────────────
            action_new_folder = QAction("📁 新增卷", self.view)
            action_new_folder.triggered.connect(lambda: self.add_tree_node(item, is_folder=True))
            menu.addAction(action_new_folder)

            action_new_file = QAction("📄 新增章", self.view)
            action_new_file.triggered.connect(lambda: self.add_tree_node(item, is_folder=False))
            menu.addAction(action_new_file)

            action_new_scene = QAction("🎬 新增幕", self.view)
            action_new_scene.triggered.connect(lambda: self.add_scene_node(item))
            menu.addAction(action_new_scene)

            menu.addSeparator()

            # ── 2. 編輯與複製 ───────────────────────────
            action_rename = QAction("✏️ 重新命名", self.view)
            action_rename.triggered.connect(lambda: self.rename_tree_node(item))
            menu.addAction(action_rename)

            action_duplicate = QAction("📋 建立副本", self.view)
            action_duplicate.triggered.connect(lambda: self.duplicate_tree_node(item))
            menu.addAction(action_duplicate)

            if node_type == "scene":
                action_edit_scene = QAction("⚙️ 編輯幕屬性", self.view)
                action_edit_scene.triggered.connect(lambda: self.edit_scene_metadata(item))
                menu.addAction(action_edit_scene)

            menu.addSeparator()

            # ── 3. 進度標記 ─────────────────────────────
            if node_type in ("file", "scene"):
                mark_menu = menu.addMenu("🏷️ 設定進度標記")
                marks = [
                    ("草稿 (灰)", MARK_COLOR_MAP.get("Draft", "#808080"), "Draft"),
                    ("一次校稿 (藍)", MARK_COLOR_MAP.get("1st Edit", "#0000FF"), "1st Edit"),
                    ("二次校稿 (黃)", MARK_COLOR_MAP.get("2nd Edit", "#FFFF00"), "2nd Edit"),
                    ("完稿 (綠)", MARK_COLOR_MAP.get("Final", "#008000"), "Final"),
                    ("廢稿 (紅)", MARK_COLOR_MAP.get("Discarded", "#FF0000"), "Discarded"),
                ]
                for label, color_code, mark_val in marks:
                    action = QAction(label, self.view)
                    action.triggered.connect(lambda checked, i=item, c=color_code, v=mark_val: self.set_item_mark(i, c, v))
                    mark_menu.addAction(action)

                action_clear_mark = QAction("無標記 (清除)", self.view)
                action_clear_mark.triggered.connect(lambda: self.clear_item_mark(item))
                mark_menu.addAction(action_clear_mark)

                menu.addSeparator()

            # ── 4. 排序與展開/收合 ──────────────────────
            action_up = QAction("⬆️ 上移", self.view)
            action_up.triggered.connect(lambda: self.move_item_up(item))
            menu.addAction(action_up)

            action_down = QAction("⬇️ 下移", self.view)
            action_down.triggered.connect(lambda: self.move_item_down(item))
            menu.addAction(action_down)

            if item.childCount() > 0 or node_type == "folder":
                action_expand = QAction("▼ 全部展開", self.view)
                action_expand.triggered.connect(lambda: self._set_item_expanded_recursive(item, True))
                menu.addAction(action_expand)

                action_collapse = QAction("▶ 全部收合", self.view)
                action_collapse.triggered.connect(lambda: self._set_item_expanded_recursive(item, False))
                menu.addAction(action_collapse)

            menu.addSeparator()

            # ── 5. 匯入文件 ─────────────────────────────
            action_import = QAction("📥 匯入文件至此...", self.view)
            action_import.triggered.connect(lambda: self.mc.import_controller.show_import_dialog(item))
            menu.addAction(action_import)

            menu.addSeparator()

            # ── 6. 刪除 ─────────────────────────────────
            action_delete = QAction("🗑️ 移至垃圾桶", self.view)
            action_delete.triggered.connect(lambda: self.delete_tree_node(item))
            menu.addAction(action_delete)

        else:
            # 空白區域右鍵點擊
            action_new_folder = QAction("📁 新增頂層卷", self.view)
            action_new_folder.triggered.connect(lambda: self.add_tree_node(None, is_folder=True))
            menu.addAction(action_new_folder)

            action_new_file = QAction("📄 新增頂層章", self.view)
            action_new_file.triggered.connect(lambda: self.add_tree_node(None, is_folder=False))
            menu.addAction(action_new_file)

            action_new_scene = QAction("🎬 新增頂層幕", self.view)
            action_new_scene.triggered.connect(lambda: self.add_scene_node(None))
            menu.addAction(action_new_scene)

            menu.addSeparator()

            action_import = QAction("📥 匯入文件...", self.view)
            action_import.triggered.connect(lambda: self.mc.import_controller.show_import_dialog(None))
            menu.addAction(action_import)

            menu.addSeparator()

            action_expand_all = QAction("▼ 全部展開", self.view)
            action_expand_all.triggered.connect(self.view.tree_widget.expandAll)
            menu.addAction(action_expand_all)

            action_collapse_all = QAction("▶ 全部收合", self.view)
            action_collapse_all.triggered.connect(self.view.tree_widget.collapseAll)
            menu.addAction(action_collapse_all)

        menu.exec(self.view.tree_widget.viewport().mapToGlobal(pos))

    def rename_tree_node(self, item: QTreeWidgetItem):
        """重新命名樹狀節點。"""
        if not self.is_item_valid(item):
            return
        old_name = item.text(0)
        new_name, ok = QInputDialog.getText(
            self.view, "重新命名", "請輸入新名稱：", text=old_name
        )
        if ok and new_name.strip():
            new_name = new_name.strip()
            item.setText(0, new_name)
            if item == self.mc.current_file_item:
                self.view.lbl_current_file.setText(new_name)
            self.mc.project.save_temp_doc()

    def duplicate_tree_node(self, item: QTreeWidgetItem):
        """建立選中節點的副本（包括子節點），並插入在同層位置。"""
        if not self.is_item_valid(item):
            return

        self.mc.save_current_editor_content()

        clone_item = self._clone_item_recursive(item, is_root=True)
        parent = item.parent()
        if parent:
            idx = parent.indexOfChild(item)
            parent.insertChild(idx + 1, clone_item)
            parent.setExpanded(True)
        else:
            idx = self.view.tree_widget.indexOfTopLevelItem(item)
            self.view.tree_widget.insertTopLevelItem(idx + 1, clone_item)

        self.mc.update_status_bar()
        self.mc.last_known_word_count = sum(x["valid"] for x in self.mc.file_word_stats.values())
        self.view.tree_widget.setCurrentItem(clone_item)
        self.on_tree_item_clicked(clone_item, 0)
        self.mc.project.save_temp_doc()

    def _clone_item_recursive(self, src_item: QTreeWidgetItem, is_root: bool = True) -> QTreeWidgetItem:
        """遞迴複製 QTreeWidgetItem 及其子項目，生成新 UUID 並更新字數統計。"""
        src_data = src_item.data(0, Qt.ItemDataRole.UserRole)
        node_type = src_data.get("type", "file") if src_data else "file"

        name = src_item.text(0)
        if is_root:
            name = f"{name} (副本)"

        new_data = dict(src_data) if src_data else {}
        new_id = str(uuid.uuid4())
        new_data["id"] = new_id

        is_folder = (node_type == "folder")
        is_scene = (node_type == "scene")
        content = new_data.get("content", "")

        new_item = self.create_item(name, is_folder=is_folder, content=content, is_scene=is_scene)
        new_item.setData(0, Qt.ItemDataRole.UserRole, new_data)

        # 恢復標記圖示
        mark_val = new_data.get("mark", "None")
        if mark_val and mark_val != "None" and mark_val in MARK_COLOR_MAP:
            self.set_item_mark(new_item, MARK_COLOR_MAP[mark_val], mark_val)

        # 若為文字檔案或幕，更新字數快取
        if node_type in ("file", "scene"):
            stats = self.mc.stats.analyze_exclusions(content)
            self.mc.file_word_stats[new_id] = stats

        # 複製子項目
        for i in range(src_item.childCount()):
            child_clone = self._clone_item_recursive(src_item.child(i), is_root=False)
            new_item.addChild(child_clone)

        return new_item

    def move_item_up(self, item: QTreeWidgetItem):
        """將節點在其父層（或頂層）向上移動一位。"""
        if not self.is_item_valid(item):
            return
        parent = item.parent()
        if parent:
            idx = parent.indexOfChild(item)
            if idx > 0:
                parent.takeChild(idx)
                parent.insertChild(idx - 1, item)
                self.view.tree_widget.setCurrentItem(item)
                self.mc.project.save_temp_doc()
        else:
            idx = self.view.tree_widget.indexOfTopLevelItem(item)
            if idx > 0:
                self.view.tree_widget.takeTopLevelItem(idx)
                self.view.tree_widget.insertTopLevelItem(idx - 1, item)
                self.view.tree_widget.setCurrentItem(item)
                self.mc.project.save_temp_doc()

    def move_item_down(self, item: QTreeWidgetItem):
        """將節點在其父層（或頂層）向下移動一位。"""
        if not self.is_item_valid(item):
            return
        parent = item.parent()
        if parent:
            idx = parent.indexOfChild(item)
            if idx < parent.childCount() - 1:
                parent.takeChild(idx)
                parent.insertChild(idx + 1, item)
                self.view.tree_widget.setCurrentItem(item)
                self.mc.project.save_temp_doc()
        else:
            idx = self.view.tree_widget.indexOfTopLevelItem(item)
            if idx < self.view.tree_widget.topLevelItemCount() - 1:
                self.view.tree_widget.takeTopLevelItem(idx)
                self.view.tree_widget.insertTopLevelItem(idx + 1, item)
                self.view.tree_widget.setCurrentItem(item)
                self.mc.project.save_temp_doc()

    def _set_item_expanded_recursive(self, item: QTreeWidgetItem, expanded: bool):
        """遞迴展開或收合節點及其子項目。"""
        item.setExpanded(expanded)
        for i in range(item.childCount()):
            self._set_item_expanded_recursive(item.child(i), expanded)

    def clear_item_mark(self, item: QTreeWidgetItem):
        """清除進度標記並還原原始圖示。"""
        if not self.is_item_valid(item):
            return
        data = item.data(0, Qt.ItemDataRole.UserRole) or {}
        data['mark'] = "None"
        self.view.tree_widget.blockSignals(True)
        item.setData(0, Qt.ItemDataRole.UserRole, data)
        self.view.tree_widget.blockSignals(False)

        node_type = data.get("type", "file")
        if node_type == "scene":
            icon = create_custom_icon("folder", "#7EB8F7", self.view.scale_factor)
        else:
            icon = create_custom_icon("file", self.view.file_icon_color, self.view.scale_factor)
        item.setIcon(0, icon)
        self.mc.project.save_temp_doc()

    def add_tree_node(self, parent_item, is_folder: bool):
        name = "新卷" if is_folder else "新章"
        new_item = self.create_item(name, is_folder)
        if parent_item:
            parent_item.addChild(new_item)
            parent_item.setExpanded(True)
        else:
            self.view.tree_widget.addTopLevelItem(new_item)

        if not is_folder:
            item_id = self.get_item_id(new_item)
            if item_id:
                self.mc.file_word_stats[item_id] = {"valid": 0, "spaces": 0, "alpha": 0, "sym": 0}
            self.mc.update_status_bar()
            self.mc.last_known_word_count = sum(x["valid"] for x in self.mc.file_word_stats.values())

        self.view.tree_widget.setCurrentItem(new_item)
        self.on_tree_item_clicked(new_item, 0)

    def add_scene_node(self, parent_item):
        """新增一個 scene 節點。"""
        new_item = self.create_item("新幕", is_scene=True)
        if parent_item:
            parent_item.addChild(new_item)
            parent_item.setExpanded(True)
        else:
            self.view.tree_widget.addTopLevelItem(new_item)
        # 初始化字數快取
        item_id = self.get_item_id(new_item)
        if item_id:
            self.mc.file_word_stats[item_id] = {"valid": 0, "spaces": 0, "alpha": 0, "sym": 0}
        self.mc.update_status_bar()
        self.view.tree_widget.setCurrentItem(new_item)
        self.on_tree_item_clicked(new_item, 0)

    def edit_scene_metadata(self, item):
        """開啟 SceneMetadataDialog 編輯場景屬性，並將結果寫回 UserRole data。"""
        if not self.is_item_valid(item):
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") != "scene":
            return

        dlg = SceneMetadataDialog(
            parent=self.view,
            scene_name=item.text(0),
            scene_summary=data.get("scene_summary", ""),
            scene_pov=data.get("scene_pov", ""),
            scene_location=data.get("scene_location", "")
        )
        if dlg.exec() == SceneMetadataDialog.DialogCode.Accepted:
            meta = dlg.get_metadata()
            data["scene_summary"] = meta["scene_summary"]
            data["scene_pov"] = meta["scene_pov"]
            data["scene_location"] = meta["scene_location"]
            self.view.tree_widget.blockSignals(True)
            item.setData(0, Qt.ItemDataRole.UserRole, data)
            self.view.tree_widget.blockSignals(False)
            # 觸發暫存以保留 metadata
            self.mc.project.save_temp_doc()

    def delete_tree_node(self, item):
        reply = QMessageBox.question(
            self.view, "確認刪除", f"您確定要將「{item.text(0)}」移至垃圾桶嗎？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.No:
            return

        is_current_or_parent = False
        curr = self.mc.current_file_item
        while curr:
            try:
                if curr == item:
                    is_current_or_parent = True
                    break
                curr = curr.parent()
            except RuntimeError:
                is_current_or_parent = True
                break

        if is_current_or_parent:
            self.mc.current_file_item = None
            self.view.editor.clear()
            self.view.lbl_current_file.setText("請選擇左側文件進行編輯")
            self.mc.current_file_last_word_count = 0

        parent = item.parent()
        if parent:
            index = parent.indexOfChild(item)
            parent.removeChild(item)
            parent_ref = parent
        else:
            index = self.view.tree_widget.indexOfTopLevelItem(item)
            self.view.tree_widget.takeTopLevelItem(index)
            parent_ref = None

        def remove_from_cache(target_item):
            t_id = self.get_item_id(target_item)
            if t_id and t_id in self.mc.file_word_stats:
                del self.mc.file_word_stats[t_id]
            for i in range(target_item.childCount()):
                remove_from_cache(target_item.child(i))
        remove_from_cache(item)

        self.mc.trash_bin.append({
            "item": item,
            "parent": parent_ref,
            "index": index,
            "name": item.text(0),
            "path": self.get_item_path_string(item),
            "type": "folder" if item.data(0, Qt.ItemDataRole.UserRole).get("type") == "folder" else "file"
        })

        if self.view.center_stack.currentIndex() == 1:
            self.refresh_trash_ui()

        self.mc.update_status_bar()
        self.mc.last_known_word_count = sum(x["valid"] for x in self.mc.file_word_stats.values())

    def set_item_mark(self, item, color_code: str, mark_value: str):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        data['mark'] = mark_value
        self.view.tree_widget.blockSignals(True)
        item.setData(0, Qt.ItemDataRole.UserRole, data)
        self.view.tree_widget.blockSignals(False)

        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QColor(color_code))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 12, 12)
        painter.end()
        item.setIcon(0, QIcon(pixmap))


    def on_tree_item_changed(self, item, column):
        if not self.is_item_valid(item):
            return
        if item == self.mc.current_file_item:
            self.view.lbl_current_file.setText(item.text(0))

    def on_tree_item_clicked(self, item, column):
        self.view.center_stack.setCurrentIndex(0)
        if not self.is_item_valid(item):
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        node_type = data.get("type") if data else ""

        # 處理資料集右側「幕」頁籤的顯示與隱藏
        if hasattr(self.view, 'scene_tab_index'):
            if node_type == "scene":
                self.view.tabs.setTabVisible(self.view.scene_tab_index, True)
                self.view.scene_info_pov_edit.setText(data.get("scene_pov", ""))
                self.view.scene_info_location_edit.setText(data.get("scene_location", ""))
                self.view.scene_info_summary_edit.setPlainText(data.get("scene_summary", ""))
                self.view.tabs.setCurrentIndex(self.view.scene_tab_index)
            else:
                self.view.tabs.setTabVisible(self.view.scene_tab_index, False)
                if self.view.tabs.currentIndex() == self.view.scene_tab_index:
                    self.view.tabs.setCurrentIndex(0)

        if data and node_type in ("file", "scene"):
            if not self.is_item_valid(self.mc.current_file_item):
                self.mc.current_file_item = None
            self.mc.save_current_editor_content()
            if self.mc.current_file_item:
                t_id = self.get_item_id(self.mc.current_file_item)
                if t_id:
                    self.mc.file_word_stats[t_id] = self.mc.stats.analyze_exclusions(self.view.editor.toPlainText())

            self.mc.current_file_item = item
            self.view.lbl_current_file.setText(item.text(0))

            content = data.get("content", "")
            self.view.editor.blockSignals(True)
            if hasattr(self.view.editor, "set_markdown"):
                self.view.editor.set_markdown(content)
            else:
                self.view.editor.setPlainText(content)
            self.view.editor.blockSignals(False)

            stats = self.mc.stats.analyze_exclusions(self.view.editor.toPlainText())
            self.mc.current_file_last_word_count = stats["valid"]

            item_id = self.get_item_id(item)
            if item_id:
                self.mc.file_word_stats[item_id] = stats
            self.mc.update_status_bar()

    def save_scene_info(self):
        """將幕屬性編輯頁籤的內容寫回當前選取的 scene 節點並觸發暫存"""
        if not self.is_item_valid(self.mc.current_file_item):
            return
        data = self.mc.current_file_item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "scene":
            data["scene_pov"] = self.view.scene_info_pov_edit.text().strip()
            data["scene_location"] = self.view.scene_info_location_edit.text().strip()
            data["scene_summary"] = self.view.scene_info_summary_edit.toPlainText().strip()
            self.view.tree_widget.blockSignals(True)
            self.mc.current_file_item.setData(0, Qt.ItemDataRole.UserRole, data)
            self.view.tree_widget.blockSignals(False)
            self.mc.project.save_temp_doc()
            # 顯示短暫的成功提示 (可選)
            self.mc.update_status_bar()

    def get_item_path_string(self, item) -> str:
        path = []
        curr = item.parent()
        while curr:
            path.insert(0, curr.text(0))
            curr = curr.parent()
        if not path:
            return "根目錄"
        return " / ".join(path)

    def refresh_trash_ui(self):
        self.view.trash_list_widget.clear()
        for idx, trash_info in enumerate(self.mc.trash_bin):
            item_type_str = "【資料夾】" if trash_info["type"] == "folder" else "【文件】"
            display_text = f"{item_type_str} {trash_info['name']} (原位置: {trash_info['path']})"
            self.view.trash_list_widget.addItem(display_text)

    def show_trash_page(self):
        self.view.tree_widget.clearSelection()
        self.view.center_stack.setCurrentIndex(1)
        self.refresh_trash_ui()

    def restore_selected_trash_item(self):
        selected_row = self.view.trash_list_widget.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self.view, "提示", "請先選擇要復原的項目。")
            return

        trash_info = self.mc.trash_bin.pop(selected_row)
        item = trash_info["item"]
        parent = trash_info["parent"]
        index = trash_info["index"]

        if parent and parent.treeWidget() is not None:
            if 0 <= index <= parent.childCount():
                parent.insertChild(index, item)
            else:
                parent.addChild(item)
            parent.setExpanded(True)
        else:
            top_count = self.view.tree_widget.topLevelItemCount()
            if 0 <= index <= top_count:
                self.view.tree_widget.insertTopLevelItem(index, item)
            else:
                self.view.tree_widget.addTopLevelItem(item)

        def restore_cache(target_item):
            data = target_item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("type") in ("file", "scene"):
                t_id = self.get_item_id(target_item)
                if t_id:
                    self.mc.file_word_stats[t_id] = self.mc.stats.analyze_exclusions_from_markdown(data.get("content", ""))
            for i in range(target_item.childCount()):
                restore_cache(target_item.child(i))
        restore_cache(item)

        self.refresh_trash_ui()
        self.mc.update_status_bar()
        self.mc.last_known_word_count = sum(x["valid"] for x in self.mc.file_word_stats.values())
        QMessageBox.information(self.view, "成功", f"已成功復原「{trash_info['name']}」！")

    def delete_selected_trash_item_permanently(self):
        """永久刪除垃圾桶中當前選取的項目。"""
        selected_row = self.view.trash_list_widget.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self.view, "提示", "請先選擇要永久刪除的項目。")
            return

        trash_info = self.mc.trash_bin[selected_row]
        reply = QMessageBox.question(
            self.view,
            "確認永久刪除",
            f"您確定要永久刪除「{trash_info['name']}」嗎？\n此操作將無法復原！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        del_info = self.mc.trash_bin.pop(selected_row)
        self.refresh_trash_ui()
        self.mc.project.save_temp_doc()
        QMessageBox.information(self.view, "成功", f"已永久刪除「{del_info['name']}」！")

    def clear_all_trash(self):
        """清空垃圾桶中所有項目。"""
        if not self.mc.trash_bin:
            QMessageBox.information(self.view, "提示", "垃圾桶目前沒有任何項目。")
            return

        reply = QMessageBox.question(
            self.view,
            "確認清空垃圾桶",
            f"您確定要清空垃圾桶中的所有 {len(self.mc.trash_bin)} 個項目嗎？\n此操作將永久刪除且無法復原！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.mc.trash_bin.clear()
        self.refresh_trash_ui()
        self.mc.project.save_temp_doc()
        QMessageBox.information(self.view, "成功", "已成功清空垃圾桶！")

    def show_trash_context_menu(self, pos):
        """顯示垃圾桶清單右鍵選單。"""
        item = self.view.trash_list_widget.itemAt(pos)
        menu = QMenu(self.view)

        if item:
            action_restore = QAction("復原此項目", self.view)
            action_restore.triggered.connect(self.restore_selected_trash_item)
            menu.addAction(action_restore)

            action_delete_perm = QAction("永久刪除", self.view)
            action_delete_perm.triggered.connect(self.delete_selected_trash_item_permanently)
            menu.addAction(action_delete_perm)

            menu.addSeparator()

        action_clear_all = QAction("清空垃圾桶", self.view)
        action_clear_all.triggered.connect(self.clear_all_trash)
        menu.addAction(action_clear_all)

        menu.exec(self.view.trash_list_widget.viewport().mapToGlobal(pos))

    def find_item_by_id(self, item_id: str, parent=None) -> QTreeWidgetItem:
        """根據 item_id 在章節樹中遞迴查找節點。"""
        if not item_id:
            return None
        count = parent.childCount() if parent else self.view.tree_widget.topLevelItemCount()
        for i in range(count):
            item = parent.child(i) if parent else self.view.tree_widget.topLevelItem(i)
            if self.get_item_id(item) == item_id:
                return item
            found = self.find_item_by_id(item_id, item)
            if found:
                return found
        return None

    def show_outline_page(self):
        """切換至全書大綱總覽模式 (Page 3)。"""
        self.mc.save_current_editor_content()
        self.view.outline_view.populate_from_tree(
            self.view.tree_widget,
            self.view.folder_icon_color,
            self.view.file_icon_color,
            self.view.scale_factor
        )
        self.view.center_stack.setCurrentIndex(3)

    def show_write_page(self):
        """切換回寫作編輯器模式 (Page 0)。"""
        self.view.center_stack.setCurrentIndex(0)

    def open_chapter_by_id(self, item_id: str):
        """透過章節 ID 開啟並載入至編輯器。"""
        item = self.find_item_by_id(item_id)
        if item:
            self.view.tree_widget.setCurrentItem(item)
            self.on_tree_item_clicked(item, 0)
        self.view.center_stack.setCurrentIndex(0)

    def set_chapter_mark_by_id(self, item_id: str, mark_value: str):
        """透過章節 ID 修改其進度標記並同步更新大綱視圖。"""
        item = self.find_item_by_id(item_id)
        if not item:
            return

        color_code = MARK_COLOR_MAP.get(mark_value, "#808080")
        self.set_item_mark(item, color_code, mark_value)
        self.view.outline_view.populate_from_tree(
            self.view.tree_widget,
            self.view.folder_icon_color,
            self.view.file_icon_color,
            self.view.scale_factor
        )
        self.mc.project.save_temp_doc()
