import os
import sys
import unittest
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication, QTreeWidgetItem
from PyQt6.QtCore import Qt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.models import CardNode, MARK_COLOR_MAP
from views.main_window import MainWindow
from controllers.main_controller import MainController


class TestContextMenus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication([])

    def setUp(self):
        self.view = MainWindow()
        self.mc = MainController(self.view)
        self.view.tree_widget.clear()
        self.mc.file_word_stats.clear()

    def tearDown(self):
        self.mc.writing_timer.stop()
        self.mc.auto_save_timer.stop()
        self.view.close()

    # ── 左側作品面板測試 ───────────────────────────────────────────

    def test_tree_rename_node(self):
        """測試樹狀節點重新命名。"""
        item = self.mc.tree.create_item("第一章", is_folder=False)
        self.view.tree_widget.addTopLevelItem(item)

        with patch("PyQt6.QtWidgets.QInputDialog.getText", return_value=("第壹章 序幕", True)):
            self.mc.tree.rename_tree_node(item)

        self.assertEqual(item.text(0), "第壹章 序幕")

    def test_tree_duplicate_file_node(self):
        """測試單個章節建立副本。"""
        item = self.mc.tree.create_item("第一章", is_folder=False, content="這是內文。")
        self.view.tree_widget.addTopLevelItem(item)
        orig_id = self.mc.tree.get_item_id(item)

        self.mc.tree.duplicate_tree_node(item)

        self.assertEqual(self.view.tree_widget.topLevelItemCount(), 2)
        dup_item = self.view.tree_widget.topLevelItem(1)
        self.assertEqual(dup_item.text(0), "第一章 (副本)")

        dup_id = self.mc.tree.get_item_id(dup_item)
        self.assertNotEqual(orig_id, dup_id)

        dup_data = dup_item.data(0, Qt.ItemDataRole.UserRole)
        self.assertEqual(dup_data.get("content"), "這是內文。")
        self.assertIn(dup_id, self.mc.file_word_stats)

    def test_tree_duplicate_folder_with_children(self):
        """測試整卷資料夾（含子節點）建立副本。"""
        folder = self.mc.tree.create_item("第一卷", is_folder=True)
        child1 = self.mc.tree.create_item("第一章", is_folder=False, content="章節內容")
        child2 = self.mc.tree.create_item("第一幕", is_scene=True, content="幕內容")
        folder.addChild(child1)
        folder.addChild(child2)
        self.view.tree_widget.addTopLevelItem(folder)

        self.mc.tree.duplicate_tree_node(folder)

        self.assertEqual(self.view.tree_widget.topLevelItemCount(), 2)
        dup_folder = self.view.tree_widget.topLevelItem(1)
        self.assertEqual(dup_folder.text(0), "第一卷 (副本)")
        self.assertEqual(dup_folder.childCount(), 2)
        self.assertEqual(dup_folder.child(0).text(0), "第一章")
        self.assertEqual(dup_folder.child(1).text(0), "第一幕")

        # 驗證 ID 不重複
        f_id = self.mc.tree.get_item_id(folder)
        df_id = self.mc.tree.get_item_id(dup_folder)
        self.assertNotEqual(f_id, df_id)

    def test_tree_move_up_and_down(self):
        """測試樹狀節點同層上移與下移。"""
        item1 = self.mc.tree.create_item("第 1 章", is_folder=False)
        item2 = self.mc.tree.create_item("第 2 章", is_folder=False)
        item3 = self.mc.tree.create_item("第 3 章", is_folder=False)
        self.view.tree_widget.addTopLevelItem(item1)
        self.view.tree_widget.addTopLevelItem(item2)
        self.view.tree_widget.addTopLevelItem(item3)

        # item2 上移
        self.mc.tree.move_item_up(item2)
        self.assertEqual(self.view.tree_widget.topLevelItem(0).text(0), "第 2 章")
        self.assertEqual(self.view.tree_widget.topLevelItem(1).text(0), "第 1 章")

        # item2 下移
        self.mc.tree.move_item_down(item2)
        self.assertEqual(self.view.tree_widget.topLevelItem(0).text(0), "第 1 章")
        self.assertEqual(self.view.tree_widget.topLevelItem(1).text(0), "第 2 章")

    def test_tree_clear_mark(self):
        """測試清除節點進度標記。"""
        item = self.mc.tree.create_item("第一章", is_folder=False)
        self.mc.tree.set_item_mark(item, MARK_COLOR_MAP["Draft"], "Draft")
        self.assertEqual(item.data(0, Qt.ItemDataRole.UserRole).get("mark"), "Draft")

        self.mc.tree.clear_item_mark(item)
        self.assertEqual(item.data(0, Qt.ItemDataRole.UserRole).get("mark"), "None")

    def test_tree_context_menu_convert_options(self):
        """測試作品面板右鍵選單中的「轉換…」母選單與子選項。"""
        from PyQt6.QtWidgets import QMenu
        item_file = self.mc.tree.create_item("測試章節", is_folder=False)
        self.view.tree_widget.addTopLevelItem(item_file)

        captured_menus = []
        def fake_exec(menu_self, *args, **kwargs):
            captured_menus.append(menu_self)
            return None

        with patch.object(QMenu, "exec", fake_exec):
            self.mc.tree.show_tree_context_menu(self.view.tree_widget.visualItemRect(item_file).center())
            self.assertEqual(len(captured_menus), 1)
            menu = captured_menus[0]

            conv_menu = None
            for action in menu.actions():
                if action.menu() and "轉換…" in action.menu().title():
                    conv_menu = action.menu()
                    break

            self.assertIsNotNone(conv_menu, "右鍵選單中應包含「轉換…」母選項")
            sub_actions = {a.text(): a for a in conv_menu.actions()}
            self.assertIn("📁 轉換為卷", sub_actions)
            self.assertIn("📄 轉換為章", sub_actions)
            self.assertIn("🎬 轉換為幕", sub_actions)

            # 章節節點：「轉換為章」應禁用，「轉換為卷」與「轉換為幕」應啟用
            self.assertTrue(sub_actions["📁 轉換為卷"].isEnabled())
            self.assertFalse(sub_actions["📄 轉換為章"].isEnabled())
            self.assertTrue(sub_actions["🎬 轉換為幕"].isEnabled())

    def test_tree_convert_file_to_folder(self):
        """測試章節節點轉換為卷節點。"""
        item = self.mc.tree.create_item("第一章", is_folder=False, content="章節正文內容")
        self.view.tree_widget.addTopLevelItem(item)
        item_id = self.mc.tree.get_item_id(item)
        self.mc.file_word_stats[item_id] = {"valid": 6, "spaces": 0, "alpha": 0, "sym": 0}

        self.view.tree_widget.setCurrentItem(item)
        self.mc.tree.on_tree_item_clicked(item, 0)
        self.assertEqual(self.mc.current_file_item, item)

        # 轉換為卷
        self.mc.tree.convert_tree_node(item, "folder")

        data = item.data(0, Qt.ItemDataRole.UserRole)
        self.assertEqual(data.get("type"), "folder")
        # 原正文應保留在資料字典中防止誤操作遺失
        self.assertEqual(data.get("content"), "章節正文內容")
        # 編輯器應卸載且字數統計應移除卷
        self.assertIsNone(self.mc.current_file_item)
        self.assertNotIn(item_id, self.mc.file_word_stats)

    def test_tree_convert_folder_to_file(self):
        """測試卷節點轉換為章節節點。"""
        item = self.mc.tree.create_item("第一卷", is_folder=True)
        self.view.tree_widget.addTopLevelItem(item)
        item_id = self.mc.tree.get_item_id(item)

        # 轉換為章
        self.mc.tree.convert_tree_node(item, "file")

        data = item.data(0, Qt.ItemDataRole.UserRole)
        self.assertEqual(data.get("type"), "file")
        self.assertIn("content", data)
        self.assertIn("cards", data)
        self.assertIn(item_id, self.mc.file_word_stats)

    def test_tree_convert_file_to_scene_and_back(self):
        """測試章節節點與幕節點互相轉換。"""
        item = self.mc.tree.create_item("第一章", is_folder=False, content="這是測試文字")
        self.view.tree_widget.addTopLevelItem(item)
        self.mc.tree.set_item_mark(item, MARK_COLOR_MAP["Draft"], "Draft")

        # 轉換為幕
        self.mc.tree.convert_tree_node(item, "scene")
        data = item.data(0, Qt.ItemDataRole.UserRole)
        self.assertEqual(data.get("type"), "scene")
        self.assertEqual(data.get("mark"), "Draft")
        self.assertIn("scene_pov", data)
        self.assertIn("scene_location", data)
        self.assertIn("scene_summary", data)

        # 轉回章
        self.mc.tree.convert_tree_node(item, "file")
        data = item.data(0, Qt.ItemDataRole.UserRole)
        self.assertEqual(data.get("type"), "file")
        self.assertEqual(data.get("mark"), "Draft")


    # ── 右側資料集面板測試 ─────────────────────────────────────────

    def test_card_rename(self):
        """測試卡片重新命名。"""
        self.mc.project_cards["character"] = [CardNode(title="主角", content="主角設定")]
        card_id = self.mc.project_cards["character"][0].id

        with patch("PyQt6.QtWidgets.QInputDialog.getText", return_value=("男主角", True)):
            self.mc.card.rename_card(card_id, "character")

        self.assertEqual(self.mc.project_cards["character"][0].title, "男主角")

    def test_card_duplicate(self):
        """測試卡片建立副本（含子卡片）。"""
        parent_card = CardNode(
            title="主要反派",
            content="反派組織領袖",
            children=[CardNode(title="得力手下", content="刺客")]
        )
        self.mc.project_cards["character"] = [parent_card]
        orig_id = parent_card.id

        self.mc.card.duplicate_card(orig_id, "character")

        cards = self.mc.project_cards["character"]
        self.assertEqual(len(cards), 2)
        dup = cards[1]
        self.assertEqual(dup.title, "主要反派 (副本)")
        self.assertEqual(dup.content, "反派組織領袖")
        self.assertNotEqual(dup.id, orig_id)
        self.assertEqual(len(dup.children), 1)
        self.assertEqual(dup.children[0].title, "得力手下")
        self.assertNotEqual(dup.children[0].id, parent_card.children[0].id)

    def test_card_copy_content(self):
        """測試複製卡片內文到剪貼簿。"""
        card = CardNode(title="魔法設定", content="火球術：耗費 10 點魔力。")
        self.mc.project_cards["world"] = [card]

        with patch.object(QApplication.clipboard(), "setText") as mock_set:
            self.mc.card.copy_card_content(card.id, "world")
            mock_set.assert_called_once_with("火球術：耗費 10 點魔力。")

    def test_card_move_up_and_down(self):
        """測試卡片同層排序上移與下移。"""
        c1 = CardNode(title="卡片 A")
        c2 = CardNode(title="卡片 B")
        c3 = CardNode(title="卡片 C")
        self.mc.project_cards["summary"] = [c1, c2, c3]

        # c2 上移
        self.mc.card.move_card_up(c2.id, "summary")
        self.assertEqual([c.title for c in self.mc.project_cards["summary"]], ["卡片 B", "卡片 A", "卡片 C"])

        # c2 下移
        self.mc.card.move_card_down(c2.id, "summary")
        self.assertEqual([c.title for c in self.mc.project_cards["summary"]], ["卡片 A", "卡片 B", "卡片 C"])


if __name__ == "__main__":
    unittest.main()
