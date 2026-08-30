import os
import tempfile
import unittest
from PyQt6.QtWidgets import QApplication
from views.main_window import MainWindow
from controllers.main_controller import MainController
from services.app_settings_service import AppSettingsService, DEFAULT_WINDOW_SETTINGS


class TestWindowSettings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_layout_ratios(self):
        """測試預設三欄 UI 比例為 1:2:2 (左欄 1/5, 編輯欄 2/5, 資料欄 2/5)"""
        view = MainWindow()
        view.resize(1200, 800)
        view.show()
        QApplication.processEvents()

        # 驗證 show 後 splitter sizes 比例為 1:2:2（五等分）
        sizes = view.splitter.sizes()
        self.assertEqual(len(sizes), 3)
        total = sum(sizes)
        self.assertAlmostEqual(sizes[0] / total, 1 / 5, delta=0.03)
        self.assertAlmostEqual(sizes[1] / total, 2 / 5, delta=0.03)
        self.assertAlmostEqual(sizes[2] / total, 2 / 5, delta=0.03)

        # 驗證預設收折寬度與備份尺寸
        self.assertEqual(view.last_left_width, 240)
        self.assertEqual(view.last_right_width, 480)
        self.assertEqual(view._saved_splitter_sizes, [240, 480, 480])
        view.close()

    def test_app_settings_service_load_save(self):
        """測試 AppSettingsService 偏好設定儲存與讀取"""
        custom_settings = {
            "window_width": 1400,
            "window_height": 900,
            "window_x": 120,
            "window_y": 80,
            "is_maximized": False,
            "splitter_sizes": [280, 560, 560],
            "last_left_width": 280,
            "last_right_width": 560,
            "scale_factor": 1.25,
        }

        save_ok = AppSettingsService.save_settings(custom_settings, self.temp_dir.name)
        self.assertTrue(save_ok)

        loaded = AppSettingsService.load_settings(self.temp_dir.name)
        self.assertEqual(loaded["window_width"], 1400)
        self.assertEqual(loaded["window_height"], 900)
        self.assertEqual(loaded["splitter_sizes"], [280, 560, 560])
        self.assertEqual(loaded["scale_factor"], 1.25)

    def test_apply_and_extract_settings(self):
        """測試 MainWindow 與 AppSettingsService 之間的套用與提取"""
        view = MainWindow()
        test_settings = {
            "window_width": 1000,
            "window_height": 700,
            "window_x": None,
            "window_y": None,
            "is_maximized": False,
            "splitter_sizes": [200, 400, 400],
            "last_left_width": 200,
            "last_right_width": 400,
            "scale_factor": 1.5,
        }

        AppSettingsService.apply_to_window(view, test_settings)
        view.show()
        QApplication.processEvents()
        view.scale_factor = 1.5

        extracted = AppSettingsService.extract_from_window(view)
        self.assertEqual(extracted["window_width"], 1000)
        self.assertEqual(extracted["window_height"], 700)
        self.assertEqual(extracted["last_left_width"], 200)
        self.assertEqual(extracted["last_right_width"], 400)
        self.assertEqual(extracted["scale_factor"], 1.5)
        
        # 驗證提取出來的 splitter sizes 比例仍為 1:2:2
        ext_sizes = extracted["splitter_sizes"]
        total = sum(ext_sizes)
        self.assertAlmostEqual(ext_sizes[0] / total, 1 / 5, delta=0.03)
        self.assertAlmostEqual(ext_sizes[1] / total, 2 / 5, delta=0.03)
        self.assertAlmostEqual(ext_sizes[2] / total, 2 / 5, delta=0.03)
        view.close()

    def test_close_event_persists_settings(self):
        """測試關閉視窗事件會將當前介面設定寫入設定檔"""
        view = MainWindow()
        mc = MainController(view)
        mc.app_dir = self.temp_dir.name

        # 調整尺寸
        view.resize(1300, 850)
        view.show()
        QApplication.processEvents()
        view.scale_factor = 1.25

        # 觸發 closeEvent
        class DummyEvent:
            def accept(self):
                pass

        mc.project.on_close_event(DummyEvent())

        # 讀取暫存目錄下的設定檔
        settings = AppSettingsService.load_settings(self.temp_dir.name)
        self.assertEqual(settings["window_width"], 1300)
        self.assertEqual(settings["window_height"], 850)
        self.assertEqual(settings["scale_factor"], 1.25)
        self.assertEqual(len(settings["splitter_sizes"]), 3)
        view.close()

    def test_ui_scale_font_scaling(self):
        """測試介面縮放時，工具列、狀態列與資料集樹狀節點字型皆能正確等比放大"""
        view = MainWindow()
        mc = MainController(view)
        mc.app_dir = self.temp_dir.name

        # 模擬右側樹狀節點已有類別與卡片
        cat_item = view.right_panel.make_category_item("characters", "角色")
        view.card_tree.addTopLevelItem(cat_item)
        card_item = view.right_panel.make_card_item("c1", "主角小明", "characters")
        cat_item.addChild(card_item)

        # 測試縮放至 1.5x (150%)
        mc.theme.set_ui_scale(1.5)

        # 驗證按鈕與狀態列標籤字型（9 * 1.5 = 13 或 13pt）
        self.assertEqual(view.btn_typewriter.font().pointSize(), int(9 * 1.5))
        self.assertEqual(view.lbl_progress.font().pointSize(), int(9 * 1.5))
        self.assertEqual(view.lbl_word_count.font().pointSize(), int(9 * 1.5))
        self.assertEqual(view.lbl_project_progress.font().pointSize(), int(9 * 1.5))
        self.assertEqual(view.right_panel.combo_add_category.font().pointSize(), int(9 * 1.5))
        
        # 驗證樹狀節點字型
        self.assertEqual(cat_item.font(0).pointSize(), int(9 * 1.5))
        self.assertEqual(card_item.font(0).pointSize(), int(9 * 1.5))

        # 驗證在 1.5x 下建立新節點也是 1.5x 字型
        new_cat = view.right_panel.make_category_item("world", "世界觀")
        self.assertEqual(new_cat.font(0).pointSize(), int(9 * 1.5))

        view.close()


if __name__ == "__main__":
    unittest.main()
