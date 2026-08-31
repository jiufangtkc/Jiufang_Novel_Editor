import os
import tempfile
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
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

        # 驗證資料集樹狀圖預設對齊設定（靠左）
        self.assertEqual(view.right_panel.card_tree.layoutDirection(), Qt.LayoutDirection.LeftToRight)

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

    def test_first_launch_initial_scale_dialog(self):
        """測試乾淨首次啟動時彈出 InitialScaleDialog 並正確儲存偏好縮放比例"""
        from unittest.mock import patch, MagicMock
        from PyQt6.QtWidgets import QDialog
        from views.dialogs.initial_scale_dialog import InitialScaleDialog

        target_app_dir = os.path.join(self.temp_dir.name, "Jiufang_Novel_Editor")

        # 確認初始狀態為首次啟動
        self.assertTrue(AppSettingsService.is_first_launch(target_app_dir))

        mock_dlg = MagicMock()
        mock_dlg.exec.return_value = QDialog.DialogCode.Accepted
        mock_dlg.selected_scale = 1.25

        view = MainWindow()
        with patch.dict(os.environ, {"LOCALAPPDATA": self.temp_dir.name}), \
             patch("controllers.main_controller.InitialScaleDialog", return_value=mock_dlg) as mock_init_dlg, \
             patch("controllers.main_controller.StartupDialog") as mock_startup:
            mock_startup_inst = MagicMock()
            mock_startup_inst.exec.return_value = QDialog.DialogCode.Accepted
            mock_startup_inst.selected_action = "new"
            mock_startup.return_value = mock_startup_inst

            mc = MainController(view, interactive_startup=True)
            mock_init_dlg.assert_called_once()
            self.assertEqual(view.scale_factor, 1.25)
            self.assertEqual(mc.app_settings["scale_factor"], 1.25)
            self.assertTrue(mc.app_settings["has_completed_initial_setup"])

            # 驗證本機設定檔已寫入
            saved = AppSettingsService.load_settings(target_app_dir)
            self.assertEqual(saved["scale_factor"], 1.25)
            self.assertTrue(saved["has_completed_initial_setup"])
            self.assertFalse(AppSettingsService.is_first_launch(target_app_dir))
            view.close()

    def test_subsequent_launch_preserves_scale_without_dialog(self):
        """測試非首次啟動時直接套用已存的 scale_factor 且不彈出 InitialScaleDialog"""
        from unittest.mock import patch, MagicMock
        from PyQt6.QtWidgets import QDialog

        target_app_dir = os.path.join(self.temp_dir.name, "Jiufang_Novel_Editor")

        # 先預先寫入已設定的設定檔
        AppSettingsService.save_settings({
            "scale_factor": 1.5,
            "has_completed_initial_setup": True,
            "last_exit_normal": True,
            "session_active": False,
        }, target_app_dir)
        self.assertFalse(AppSettingsService.is_first_launch(target_app_dir))

        view = MainWindow()
        with patch.dict(os.environ, {"LOCALAPPDATA": self.temp_dir.name}), \
             patch("controllers.main_controller.InitialScaleDialog") as mock_init_dlg, \
             patch("controllers.main_controller.StartupDialog") as mock_startup:
            mock_startup_inst = MagicMock()
            mock_startup_inst.exec.return_value = QDialog.DialogCode.Accepted
            mock_startup_inst.selected_action = "new"
            mock_startup.return_value = mock_startup_inst

            mc = MainController(view, interactive_startup=True)
            # 確保不會再彈出初次縮放詢問視窗
            mock_init_dlg.assert_not_called()
            self.assertEqual(view.scale_factor, 1.5)
            self.assertEqual(mc.app_settings["scale_factor"], 1.5)
            view.close()

    def test_reset_project_state_preserves_scale(self):
        """測試開啟新專案（_reset_project_state）時不會將縮放比例重設為 1.0"""
        view = MainWindow()
        mc = MainController(view)
        mc.app_dir = self.temp_dir.name

        # 使用者手動設定縮放至 1.8x
        mc.theme.set_ui_scale(1.8)
        self.assertEqual(view.scale_factor, 1.8)
        self.assertEqual(mc.app_settings["scale_factor"], 1.8)

        # 觸發開啟新專案（init_default_project）
        mc.project.init_default_project()

        # 驗證縮放比例依然維持 1.8x，不會被重設為 1.0
        self.assertEqual(view.scale_factor, 1.8)
        self.assertEqual(mc.app_settings["scale_factor"], 1.8)

        saved = AppSettingsService.load_settings(self.temp_dir.name)
        self.assertEqual(saved["scale_factor"], 1.8)
        view.close()

    def test_theme_set_ui_scale_persists_settings(self):
        """測試 ThemeController.set_ui_scale 會即時將縮放比例持久化至 app_settings.json"""
        view = MainWindow()
        mc = MainController(view)
        mc.app_dir = self.temp_dir.name

        mc.theme.set_ui_scale(1.25)
        saved = AppSettingsService.load_settings(self.temp_dir.name)
        self.assertEqual(saved["scale_factor"], 1.25)

        mc.theme.set_ui_scale(2.0)
        saved = AppSettingsService.load_settings(self.temp_dir.name)
        self.assertEqual(saved["scale_factor"], 2.0)
        view.close()


if __name__ == "__main__":
    unittest.main()

