import os
import sys
import tempfile
import unittest
from PyQt6.QtWidgets import QApplication

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.models import JneProject, ProjectInfo, ChapterNode, CardNode, WritingLogEntry
from services.database import DatabaseService
from views.main_window import MainWindow
from controllers.main_controller import MainController


class TestTreeExpansionPersistence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "expansion_test.db")
        self.view = MainWindow()
        self.mc = MainController(self.view)

    def tearDown(self):
        self.mc.writing_timer.stop()
        self.mc.auto_save_timer.stop()
        self.view.close()
        self.temp_dir.cleanup()

    def test_database_expansion_persistence(self):
        """測試 DatabaseService 對章節樹與卡片/分類樹展開狀態的持久化能力。"""
        project = JneProject()
        project.project_info = ProjectInfo(
            title="展開狀態測試作品",
            expanded_categories=["character", "world"]  # 僅展開 character 與 world，其餘收合
        )

        # 左側目錄樹：
        # 卷 1 (展開: True) -> 章 1 (展開: False) -> 節 1 (展開: True)
        # 卷 2 (展開: False) -> 章 2 (展開: True)
        vol1 = ChapterNode(name="第一卷", node_type="folder", is_expanded=True)
        chap1 = ChapterNode(name="第一章", node_type="folder", is_expanded=False)
        sec1 = ChapterNode(name="第一節", node_type="file", is_expanded=True, content="章節內文")
        chap1.children.append(sec1)
        vol1.children.append(chap1)

        vol2 = ChapterNode(name="第二卷", node_type="folder", is_expanded=False)
        chap2 = ChapterNode(name="第二章", node_type="file", is_expanded=True)
        vol2.children.append(chap2)

        project.tree = [vol1, vol2]

        # 右側資料集卡片：
        # 角色分類：卡片 A (is_collapsed: False / 展開) -> 子卡片 A1 (is_collapsed: True / 收折)
        # 世界觀分類：卡片 B (is_collapsed: True / 收折)
        card_a = CardNode(title="主角卡片", is_collapsed=False)
        card_a_sub = CardNode(title="武器卡片", is_collapsed=True)
        card_a.children.append(card_a_sub)
        project.project_cards["character"].append(card_a)

        card_b = CardNode(title="世界觀卡片", is_collapsed=True)
        project.project_cards["world"].append(card_b)

        # 儲存
        DatabaseService.save_project(project, self.db_path)

        # 載入
        loaded = DatabaseService.load_project(self.db_path)

        # 驗證 project_info.expanded_categories
        self.assertEqual(loaded.project_info.expanded_categories, ["character", "world"])

        # 驗證左側章節樹
        self.assertEqual(len(loaded.tree), 2)
        self.assertTrue(loaded.tree[0].is_expanded)
        self.assertFalse(loaded.tree[0].children[0].is_expanded)
        self.assertTrue(loaded.tree[0].children[0].children[0].is_expanded)
        self.assertFalse(loaded.tree[1].is_expanded)
        self.assertTrue(loaded.tree[1].children[0].is_expanded)

        # 驗證右側卡片
        loaded_chars = loaded.project_cards["character"]
        self.assertEqual(len(loaded_chars), 1)
        self.assertFalse(loaded_chars[0].is_collapsed)
        self.assertTrue(loaded_chars[0].children[0].is_collapsed)

        loaded_world = loaded.project_cards["world"]
        self.assertEqual(len(loaded_world), 1)
        self.assertTrue(loaded_world[0].is_collapsed)

    def test_ui_tree_expansion_workflow(self):
        """測試完整 UI 操作流程：在介面上展開/收合左側與右側樹狀節點，存檔後載入，驗證 UI 還原。"""
        # 清除既有預設樹項目
        self.view.tree_widget.clear()

        # 1. 建立左側樹項目：
        # 卷 1 (展開) -> 章 1 (展開) -> 幕 1 (內文)
        # 卷 2 (收合) -> 章 2 (收合) -> 幕 2 (內文)
        vol1 = self.mc.tree.create_item("第一卷", is_folder=True)
        chap1 = self.mc.tree.create_item("第一章", is_folder=True)
        sec1 = self.mc.tree.create_item("第一幕", is_scene=True, content="幕 1 內文")
        chap1.addChild(sec1)
        vol1.addChild(chap1)
        self.view.tree_widget.addTopLevelItem(vol1)

        vol2 = self.mc.tree.create_item("第二卷", is_folder=True)
        chap2 = self.mc.tree.create_item("第二章", is_folder=True)
        sec2 = self.mc.tree.create_item("第二幕", is_scene=True, content="幕 2 內文")
        chap2.addChild(sec2)
        vol2.addChild(chap2)
        self.view.tree_widget.addTopLevelItem(vol2)

        # 設定展開狀態：卷 1 展開、章 1 展開；卷 2 收合、章 2 收合
        vol1.setExpanded(True)
        chap1.setExpanded(True)
        vol2.setExpanded(False)
        chap2.setExpanded(False)

        # 2. 建立右側卡片與自訂展開狀態
        card_main = CardNode(title="主角", is_collapsed=False)
        card_sub = CardNode(title="武器", is_collapsed=True)
        card_main.children.append(card_sub)
        self.mc.project_cards["character"] = [card_main]

        card_world = CardNode(title="王國", is_collapsed=False)
        self.mc.project_cards["world"] = [card_world]

        # 渲染卡片樹
        self.mc.card.rebuild_card_tree()

        # 在 UI 上手動收合「世界觀」分類，展開「角色」分類
        root = self.view.card_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if "角色" in item.text(0):
                item.setExpanded(True)
                # 主角卡片展開、武器收合
                if item.childCount() > 0:
                    item.child(0).setExpanded(True)
            elif "世界觀" in item.text(0):
                item.setExpanded(False)

        # 3. 執行儲存
        project = self.mc.project._build_jne_project()
        DatabaseService.save_project(project, self.db_path)

        # 4. 重新載入專案至全新的控制器狀態
        loaded_project = DatabaseService.load_project(self.db_path)
        self.mc.project.load_project_data(loaded_project)

        # 5. 驗證左側樹 UI 狀態
        self.assertEqual(self.view.tree_widget.topLevelItemCount(), 2)

        reloaded_vol1 = self.view.tree_widget.topLevelItem(0)
        self.assertEqual(reloaded_vol1.text(0), "第一卷")
        self.assertTrue(reloaded_vol1.isExpanded())

        reloaded_chap1 = reloaded_vol1.child(0)
        self.assertEqual(reloaded_chap1.text(0), "第一章")
        self.assertTrue(reloaded_chap1.isExpanded())

        reloaded_vol2 = self.view.tree_widget.topLevelItem(1)
        self.assertEqual(reloaded_vol2.text(0), "第二卷")
        self.assertFalse(reloaded_vol2.isExpanded())

        reloaded_chap2 = reloaded_vol2.child(0)
        self.assertEqual(reloaded_chap2.text(0), "第二章")
        self.assertFalse(reloaded_chap2.isExpanded())

        # 6. 驗證右側卡片與分類樹 UI 狀態
        card_root = self.view.card_tree.invisibleRootItem()
        found_character = False
        found_world = False
        for i in range(card_root.childCount()):
            cat_item = card_root.child(i)
            if "角色" in cat_item.text(0):
                found_character = True
                self.assertTrue(cat_item.isExpanded())
                if cat_item.childCount() > 0:
                    char_card_item = cat_item.child(0)
                    self.assertTrue(char_card_item.isExpanded())
            elif "世界觀" in cat_item.text(0):
                found_world = True
                self.assertFalse(cat_item.isExpanded())

        self.assertTrue(found_character)
        self.assertTrue(found_world)


if __name__ == '__main__':
    unittest.main()
