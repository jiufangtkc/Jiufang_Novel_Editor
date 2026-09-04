from typing import List, Optional
from PyQt6.QtWidgets import QDialog, QMessageBox, QTreeWidgetItem
from PyQt6.QtCore import Qt

from models.models import ChapterNode, MARK_COLOR_MAP
from views.dialogs.import_preview_dialog import ImportPreviewDialog


class ImportController:
    """負責外部檔案匯入並整合至專案樹狀結構的控制器。"""

    def __init__(self, main_controller):
        self.mc = main_controller
        self.view = main_controller.view

    def show_import_dialog(self, target_item: Optional[QTreeWidgetItem] = None):
        """開啟匯入對話框並處理使用者確認之章節注入。"""
        self.mc.save_current_editor_content()

        curr_item = target_item
        if curr_item is None:
            curr_item = self.view.tree_widget.currentItem()
        
        target_name = ""
        if curr_item and self.mc.tree.is_item_valid(curr_item):
            target_name = curr_item.text(0)

        dialog = ImportPreviewDialog(
            parent=self.view,
            default_file_path="",
            current_target_name=target_name
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        selected_nodes = dialog.get_selected_nodes()
        if not selected_nodes:
            return

        target_mode = dialog.get_import_target()
        self._apply_imported_nodes(selected_nodes, target_mode, curr_item)

    def _apply_imported_nodes(self, nodes: List[ChapterNode], target_mode: str, target_item: Optional[QTreeWidgetItem]):
        """將 ChapterNode 列表批次反序列化為 QTreeWidgetItem 並掛載至作品樹。"""
        first_file_item = None
        imported_count = 0

        def instantiate_node(node: ChapterNode, parent_tree_item=None) -> QTreeWidgetItem:
            nonlocal first_file_item, imported_count
            is_scene = (node.node_type == "scene")
            is_folder = (node.node_type == "folder")

            item = self.mc.tree.create_item(
                node.name,
                is_folder=is_folder,
                is_scene=is_scene,
                content=node.content
            )

            if node.node_type in ("file", "scene"):
                data = item.data(0, Qt.ItemDataRole.UserRole) or {}
                data["content"] = node.content
                data["mark"] = getattr(node, "mark", "Draft")
                data["id"] = node.id
                if is_scene:
                    data["scene_summary"] = getattr(node, "scene_summary", "")
                    data["scene_pov"] = getattr(node, "scene_pov", "")
                    data["scene_location"] = getattr(node, "scene_location", "")
                item.setData(0, Qt.ItemDataRole.UserRole, data)

                if data["mark"] in MARK_COLOR_MAP:
                    self.mc.tree.set_item_mark(item, MARK_COLOR_MAP[data["mark"]], data["mark"])

                # 字數統計快取
                if node.id:
                    self.mc.file_word_stats[node.id] = self.mc.stats.analyze_exclusions_from_markdown(node.content)

                if first_file_item is None:
                    first_file_item = item

            imported_count += 1

            # 掛載到樹上
            if parent_tree_item is not None:
                parent_tree_item.addChild(item)

            for child in node.children:
                instantiate_node(child, item)

            item.setExpanded(getattr(node, "is_expanded", True))
            return item

        self.view.tree_widget.blockSignals(True)

        if target_mode == "new_book":
            # 建立全新專案（重置專案狀態與卡片）
            self.mc.project._reset_project_state("未命名作品", "")
            # 清空預設的未命名章節
            self.view.tree_widget.clear()
            for root_node in nodes:
                item = instantiate_node(root_node, parent_tree_item=None)
                self.view.tree_widget.addTopLevelItem(item)

        elif target_mode == "insert" and target_item and self.mc.tree.is_item_valid(target_item):
            # 判斷 target_item 是否為資料夾
            item_data = target_item.data(0, Qt.ItemDataRole.UserRole) or {}
            is_folder = (item_data.get("type") == "folder")

            if is_folder:
                for root_node in nodes:
                    instantiate_node(root_node, parent_tree_item=target_item)
                target_item.setExpanded(True)
            else:
                # 插入在同一層級該項目之後
                parent_of_target = target_item.parent()
                if parent_of_target:
                    insert_idx = parent_of_target.indexOfChild(target_item) + 1
                    for root_node in reversed(nodes):
                        item = instantiate_node(root_node, parent_tree_item=None)
                        parent_of_target.insertChild(insert_idx, item)
                else:
                    insert_idx = self.view.tree_widget.indexOfTopLevelItem(target_item) + 1
                    for root_node in reversed(nodes):
                        item = instantiate_node(root_node, parent_tree_item=None)
                        self.view.tree_widget.insertTopLevelItem(insert_idx, item)
        else:
            # 預設：追加至最下方頂層
            for root_node in nodes:
                item = instantiate_node(root_node, parent_tree_item=None)
                self.view.tree_widget.addTopLevelItem(item)

        self.view.tree_widget.blockSignals(False)

        # 狀態標記與統計重算
        self.mc.mark_dirty(True)
        self.mc.stats.recalculate_all_word_stats()
        self.mc.update_status_bar()

        # 自動選取並載入第一個新匯入的章節
        if first_file_item:
            self.view.tree_widget.setCurrentItem(first_file_item)
            self.mc.tree.on_tree_item_clicked(first_file_item, 0)

        QMessageBox.information(
            self.view,
            "匯入成功",
            f"已成功匯入 {imported_count} 個項目（含分卷與章節）至作品面板！"
        )
