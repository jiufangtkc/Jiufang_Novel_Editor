import os
import re
import json
import uuid
from PyQt6.QtWidgets import QDialog, QFileDialog, QMessageBox

from models.models import CATEGORY_DISPLAY_NAMES, CardNode
from views.dialogs.dataset_export_dialog import DatasetExportDialog
from utils.dataset_formatter import DatasetFormatter

class DatasetController:
    def __init__(self, mc):
        self.mc = mc
        self.view = mc.view

    def export_dataset(self):
        """開啟資料集匯出精靈並依據選擇格式匯出。"""
        # 透過 card controller 序列化
        all_cards_data = self.mc.card.serialize_all_cards()
        all_cats_meta = {**CATEGORY_DISPLAY_NAMES, **getattr(self.mc.project_info, 'categories_meta', {})}
        dialog = DatasetExportDialog(
            parent=self.view,
            cards_data=all_cards_data,
            categories_meta=all_cats_meta
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        filtered_cards = dialog.get_filtered_cards_data()
        if not filtered_cards:
            QMessageBox.warning(self.view, "提示", "未選取任何欲匯出的卡片。")
            return

        fmt = dialog.get_export_format()
        book_title = getattr(self.mc.project_info, "title", "未命名作品") or "未命名作品"
        clean_title = re.sub(r'[\/\\\:\*\?\"\<\>\|]', '_', book_title)

        default_dir = self.mc.get_export_dir()
        os.makedirs(default_dir, exist_ok=True)

        if fmt == "docx":
            filter_str = "Word 文件 (*.docx);;所有檔案 (*)"
            default_ext = ".docx"
        elif fmt == "md":
            filter_str = "Markdown 檔案 (*.md);;所有檔案 (*)"
            default_ext = ".md"
        else:
            filter_str = "JSON 資料集備份檔 (*.json);;所有檔案 (*)"
            default_ext = ".json"

        default_filename = os.path.join(default_dir, f"{clean_title}_設定資料集{default_ext}")
        file_path, _ = QFileDialog.getSaveFileName(
            self.view, "匯出設定資料集", default_filename, filter_str
        )
        if not file_path:
            return

        try:
            if fmt == "json":
                data = {
                    "version": "1.0",
                    "categories_meta": all_cats_meta,
                    "cards": filtered_cards
                }
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            elif fmt == "md":
                md_content = DatasetFormatter.format_to_markdown(
                    cards_data=filtered_cards,
                    categories_meta=all_cats_meta,
                    book_title=book_title
                )
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(md_content)
            elif fmt == "docx":
                from docx import Document
                from utils.markdown_converter import MarkdownConverter
                md_content = DatasetFormatter.format_to_markdown(
                    cards_data=filtered_cards,
                    categories_meta=all_cats_meta,
                    book_title=book_title
                )
                doc = Document()
                font_family = getattr(self.mc.project_info, "global_font_family", "Iansui") or "Iansui"
                MarkdownConverter.render_to_docx(md_content, doc, font_family=font_family)
                doc.save(file_path)

            QMessageBox.information(self.view, "匯出成功", f"資料集已成功匯出至：\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self.view, "匯出失敗", f"匯出資料集時發生錯誤：\n{str(e)}")

    def import_dataset(self):
        """匯入資料集並處理衝突"""
        file_path, _ = QFileDialog.getOpenFileName(
            self.view, "匯入資料集", "", "JSON Files (*.json);;All Files (*)"
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                QMessageBox.warning(self.view, "匯入失敗", "無效的資料格式。")
                return

            # 相容單純匯出的卡片格式或帶有 meta 的格式
            cards_data = data.get("cards", data) if "cards" in data else data
            imported_meta = data.get("categories_meta", {})

            # 收集所有匯入的卡片名稱
            imported_cards = []
            def _collect(cat_data):
                for card in cat_data:
                    imported_cards.append(card)
                    _collect(card.get("children", []))
            
            for cat, cards in cards_data.items():
                if isinstance(cards, list):
                    _collect(cards)

            # 檢查衝突 (現有卡片)
            existing_cards_dict = {}
            for cat, cards in self.mc.project_cards.items():
                def _collect_existing(node_list):
                    for node in node_list:
                        existing_cards_dict[node.title] = node
                        _collect_existing(node.children)
                _collect_existing(cards)

            conflicts = [c for c in imported_cards if c.get("title") in existing_cards_dict]

            strategy = "new"
            if conflicts:
                msgBox = QMessageBox(self.view)
                msgBox.setWindowTitle("匯入衝突")
                msgBox.setText(f"發現 {len(conflicts)} 張同名的卡片。請選擇處理方式：")
                btn_new = msgBox.addButton("建立為新卡片", QMessageBox.ButtonRole.ActionRole)
                btn_overwrite = msgBox.addButton("覆蓋現有卡片", QMessageBox.ButtonRole.ActionRole)
                btn_cancel = msgBox.addButton("取消匯入", QMessageBox.ButtonRole.RejectRole)
                msgBox.exec()

                if msgBox.clickedButton() == btn_cancel:
                    return
                elif msgBox.clickedButton() == btn_overwrite:
                    strategy = "overwrite"
                else:
                    strategy = "new"

            # 執行匯入
            for cat, cards_list in cards_data.items():
                if not isinstance(cards_list, list):
                    continue

                # 確保分類存在
                if cat not in self.mc.project_cards:
                    self.mc.project_cards[cat] = []
                    if hasattr(self.mc, '_project_category_order'):
                        self.mc._project_category_order.append(cat)
                    if cat in imported_meta:
                        if not hasattr(self.mc.project_info, 'categories_meta'):
                            self.mc.project_info.categories_meta = {}
                        self.mc.project_info.categories_meta[cat] = imported_meta[cat]

                # 遞迴處理卡片
                self._import_card_list(cards_list, self.mc.project_cards[cat], strategy, existing_cards_dict)

            self.mc.card.rebuild_card_tree()
            self.mc.project.save_temp_doc()
            QMessageBox.information(self.view, "匯入成功", "資料集匯入完成。")

        except Exception as e:
            QMessageBox.critical(self.view, "匯入失敗", f"匯入資料集時發生錯誤：\n{str(e)}")

    def _import_card_list(self, import_list: list, target_list: list, strategy: str, existing_cards_dict: dict):
        for card_data in import_list:
            title = card_data.get("title", "")
            if title in existing_cards_dict and strategy == "overwrite":
                # 覆蓋現有卡片內容
                existing_node = existing_cards_dict[title]
                existing_node.content = card_data.get("content", "")
                existing_node.color = card_data.get("color", "#3C3F41")
                # 遞迴處理子卡片
                self._import_card_list(card_data.get("children", []), existing_node.children, strategy, existing_cards_dict)
            else:
                # 建立為新卡片
                new_title = title
                if title in existing_cards_dict and strategy == "new":
                    new_title = f"{title} (匯入)"
                
                new_node = CardNode(
                    title=new_title,
                    id=str(uuid.uuid4()),  # 賦予新 ID 避免衝突
                    content=card_data.get("content", ""),
                    color=card_data.get("color", "#3C3F41"),
                    is_collapsed=card_data.get("is_collapsed", False)
                )
                target_list.append(new_node)
                # 子卡片也視為新卡片處理
                self._import_card_list(card_data.get("children", []), new_node.children, "new", existing_cards_dict)
