import unittest
import sys
from PyQt6.QtWidgets import QApplication, QTreeWidgetItem
from PyQt6.QtCore import Qt

from views.main_window import MainWindow
from controllers.main_controller import MainController

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

class TestFocusAndOutline(unittest.TestCase):
    """測試沉浸模式 (Focus Mode) 與大綱模式 (Outline View) 功能。"""

    def setUp(self):
        self.view = MainWindow()
        self.mc = MainController(self.view)

    def tearDown(self):
        if hasattr(self.mc, 'writing_timer') and self.mc.writing_timer.isActive():
            self.mc.writing_timer.stop()
        if hasattr(self.mc, 'auto_save_timer') and self.mc.auto_save_timer.isActive():
            self.mc.auto_save_timer.stop()
        self.view.close()

    def test_outline_view_population_and_stats(self):
        """測試大綱模式從章節樹擷取資料、計算字數與摘要。"""
        # 清空章節樹並建立測試章節
        self.view.tree_widget.clear()
        
        folder_item = self.mc.tree.create_item("第一卷 風起", is_folder=True)
        self.view.tree_widget.addTopLevelItem(folder_item)
        
        chapter1 = self.mc.tree.create_item("第一章 少年入世", is_folder=False, content="這是第一章的內文，天朗氣清，惠風和暢。")
        self.mc.tree.set_item_mark(chapter1, "#008000", "Final")
        folder_item.addChild(chapter1)

        chapter2 = self.mc.tree.create_item("第二章 拔劍相助", is_folder=False, content="這是第二章的內文，少年拔劍而起，行俠仗義。")
        folder_item.addChild(chapter2)

        # 切換至大綱模式並同步
        self.mc.tree.show_outline_page()
        self.assertEqual(self.view.center_stack.currentIndex(), 3)

        outline_tree = self.view.outline_view.tree_widget
        self.assertEqual(outline_tree.topLevelItemCount(), 1)
        
        out_folder = outline_tree.topLevelItem(0)
        self.assertEqual(out_folder.text(0), "第一卷 風起")
        self.assertEqual(out_folder.childCount(), 2)

        out_ch1 = out_folder.child(0)
        self.assertEqual(out_ch1.text(0), "第一章 少年入世")
        self.assertEqual(out_ch1.text(1), "完稿")
        self.assertIn("天朗氣清", out_ch1.text(3))

        out_ch2 = out_folder.child(1)
        self.assertEqual(out_ch2.text(0), "第二章 拔劍相助")
        self.assertEqual(out_ch2.text(1), "草稿")
        self.assertIn("拔劍而起", out_ch2.text(3))

    def test_outline_filter(self):
        """測試大綱模式即時搜尋過濾。"""
        self.view.tree_widget.clear()
        folder = self.mc.tree.create_item("卷一", is_folder=True)
        self.view.tree_widget.addTopLevelItem(folder)

        ch1 = self.mc.tree.create_item("林沖夜奔", is_folder=False, content="大雪紛飛，直奔梁山。")
        ch2 = self.mc.tree.create_item("武松打虎", is_folder=False, content="景陽岡上，三碗不過岡。")
        folder.addChild(ch1)
        folder.addChild(ch2)

        self.mc.tree.show_outline_page()
        outline_tree = self.view.outline_view.tree_widget
        
        # 搜尋 "武松"
        self.view.outline_view.filter_items("武松")
        out_folder = outline_tree.topLevelItem(0)
        self.assertFalse(out_folder.child(0).isHidden() == False and out_folder.child(0).text(0) == "林沖夜奔" and not out_folder.child(0).isHidden())
        self.assertFalse(out_folder.child(1).isHidden())

        # 清除過濾
        self.view.outline_view.filter_items("")
        self.assertFalse(out_folder.child(0).isHidden())
        self.assertFalse(out_folder.child(1).isHidden())

    def test_outline_open_chapter_and_mark_change(self):
        """測試在大綱中選取跳轉及修改章節標記。"""
        self.view.tree_widget.clear()
        chapter = self.mc.tree.create_item("孤舟蓑笠翁", is_folder=False, content="獨釣寒江雪。")
        self.view.tree_widget.addTopLevelItem(chapter)
        ch_id = self.mc.tree.get_item_id(chapter)

        # 透過 id 開啟章節
        self.mc.tree.show_outline_page()
        self.assertEqual(self.view.center_stack.currentIndex(), 3)
        
        self.mc.tree.open_chapter_by_id(ch_id)
        self.assertEqual(self.view.center_stack.currentIndex(), 0)
        self.assertEqual(self.mc.current_file_item, chapter)
        self.assertIn("獨釣寒江雪", self.view.editor.toPlainText())

        # 透過 id 變更標記
        self.mc.tree.set_chapter_mark_by_id(ch_id, "1st Edit")
        data = chapter.data(0, Qt.ItemDataRole.UserRole)
        self.assertEqual(data.get("mark"), "1st Edit")

    def test_focus_mode_lifecycle(self):
        """測試沉浸模式進入與離開狀態。"""
        self.assertFalse(self.view.is_focus_mode)
        self.assertFalse(self.view.left_widget.isHidden())
        self.assertFalse(self.view.right_widget.isHidden())

        # 進入沉浸模式
        self.view.enter_focus_mode()
        self.assertTrue(self.view.is_focus_mode)
        self.assertTrue(self.view.left_widget.isHidden())
        self.assertTrue(self.view.right_widget.isHidden())
        self.assertTrue(self.view.top_bar.isHidden())
        self.assertTrue(self.view.format_toolbar.isHidden())
        self.assertTrue(self.view.status_bar.isHidden())
        self.assertFalse(self.view.lbl_focus_banner.isHidden())
        self.assertEqual(self.view.center_stack.currentIndex(), 0)

        # 離開沉浸模式
        self.view.exit_focus_mode()
        self.assertFalse(self.view.is_focus_mode)
        self.assertFalse(self.view.left_widget.isHidden())
        self.assertFalse(self.view.right_widget.isHidden())
        self.assertFalse(self.view.top_bar.isHidden())
        self.assertFalse(self.view.format_toolbar.isHidden())
        self.assertFalse(self.view.status_bar.isHidden())
        self.assertTrue(self.view.lbl_focus_banner.isHidden())

        # 切換測試
        self.view.toggle_focus_mode()
        self.assertTrue(self.view.is_focus_mode)
        self.view.toggle_focus_mode()
        self.assertFalse(self.view.is_focus_mode)

if __name__ == '__main__':
    unittest.main()
