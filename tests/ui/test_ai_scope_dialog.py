import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PyQt6.QtWidgets import QApplication, QTreeWidgetItem
from PyQt6.QtCore import Qt
from views.dialogs.ai_scope_dialog import AIScopeDialog
from views.main_window import MainWindow
from controllers.main_controller import MainController
from services.token_estimator import TokenEstimateResult


class TestAIScopeDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.main_win = MainWindow()
        self.mc = MainController(self.main_win)
        self.main_win.tree_widget.clear()

        # 建立測試用目錄結構
        self.vol_item = self.mc.tree.create_item("第一卷", is_folder=True)
        self.main_win.tree_widget.addTopLevelItem(self.vol_item)

        self.ch1 = self.mc.tree.create_item("第一章", is_folder=False, content="莫庸持劍凝視星空，體內靈力流轉不息。")
        self.ch2 = self.mc.tree.create_item("第二章", is_folder=False, content="越無憂自迷霧中走出，遞過一枚泛黃的玉簡。")
        self.vol_item.addChild(self.ch1)
        self.vol_item.addChild(self.ch2)

        # 預設模擬本機服務在線與 Context 回傳以利一般流程測試
        self.patcher_status = patch("services.ai_service.AIService.check_local_server_status", return_value=(True, "連線正常"))
        self.mock_status = self.patcher_status.start()
        self.patcher_limit = patch("services.ai_service.AIService.fetch_context_limit", return_value=131072)
        self.mock_limit = self.patcher_limit.start()

    def tearDown(self):
        self.patcher_limit.stop()
        self.patcher_status.stop()
        self.main_win.close()

    def test_scope_dialog_no_emoji(self):
        """驗證 AIScopeDialog 介面元件文案均不包含 Emoji 表情符號。"""
        dlg = AIScopeDialog(parent=self.main_win, current_item=self.ch1, task_type="character")
        
        # 檢查選項與按鈕文案
        texts_to_check = [
            dlg.radio_all.text(),
            dlg.radio_current.text(),
            dlg.radio_custom.text(),
            dlg.btn_select_all.text(),
            dlg.btn_deselect_all.text(),
            dlg.btn_start.text(),
            dlg.btn_cancel.text()
        ]
        if hasattr(dlg, "btn_check_connection"):
            texts_to_check.append(dlg.btn_check_connection.text())
        
        # 定義常見的 Emoji Unicode 範圍
        for text in texts_to_check:
            for char in text:
                # 排除純幾何形狀（如燈號圓點 ●）與一般中文/英文/數字/標點
                code = ord(char)
                # 常用 Emoji 區段: 0x1F300-0x1FAFF, 0x2600-0x27BF (排除全形標點等)
                is_emoji = (0x1F300 <= code <= 0x1FAFF) or (0x2600 <= code <= 0x27BF and char not in ("，", "。", "！", "？"))
                self.assertFalse(is_emoji, f"文字 '{text}' 含有 Emoji 字元: '{char}' (U+{code:04X})")
        
        dlg.close()

    def test_scope_dialog_green_status_enables_start_button(self):
        """模擬估算為 GREEN 狀態時，驗證顯示綠燈且開始按鈕處於啟用狀態。"""
        with patch("services.token_estimator.TokenEstimator.estimate_request") as mock_estimate:
            mock_estimate.return_value = TokenEstimateResult(
                input_tokens=500,
                system_tokens=200,
                reserved_output_tokens=4000,
                overhead_tokens=1000,
                total_estimated_tokens=5700,
                context_limit=131072,
                status="GREEN",
                status_message="可以嘗試送出"
            )
            dlg = AIScopeDialog(parent=self.main_win, current_item=self.ch1, task_type="character")
            dlg.update_statistics()

            self.assertTrue(dlg.btn_start.isEnabled())
            self.assertIn("#98c379", dlg.lbl_stats.text())
            self.assertIn("可以嘗試送出", dlg.lbl_stats.text())
            dlg.close()

    def test_scope_dialog_yellow_status_enables_start_button(self):
        """模擬估算為 YELLOW 狀態時，驗證顯示黃燈且開始按鈕仍允許點擊。"""
        with patch("services.token_estimator.TokenEstimator.estimate_request") as mock_estimate:
            mock_estimate.return_value = TokenEstimateResult(
                input_tokens=7000,
                system_tokens=500,
                reserved_output_tokens=4000,
                overhead_tokens=1000,
                total_estimated_tokens=12500,
                context_limit=14000,
                status="YELLOW",
                status_message="接近 Context 上限，可能導致分析較慢或失敗"
            )
            dlg = AIScopeDialog(parent=self.main_win, current_item=self.ch1, task_type="character")
            dlg.update_statistics()

            self.assertTrue(dlg.btn_start.isEnabled())
            self.assertIn("#e5c07b", dlg.lbl_stats.text())
            self.assertIn("接近 Context 上限", dlg.lbl_stats.text())
            dlg.close()

    def test_scope_dialog_red_status_disables_start_button(self):
        """模擬估算為 RED 狀態時，驗證顯示紅燈且開始按鈕被強制禁用。"""
        with patch("services.token_estimator.TokenEstimator.estimate_request") as mock_estimate:
            mock_estimate.return_value = TokenEstimateResult(
                input_tokens=15000,
                system_tokens=500,
                reserved_output_tokens=4000,
                overhead_tokens=1000,
                total_estimated_tokens=20500,
                context_limit=8192,
                status="RED",
                status_message="超過目前 Context 限制，請縮小分析範圍或調高限制"
            )
            dlg = AIScopeDialog(parent=self.main_win, current_item=self.ch1, task_type="character")
            dlg.update_statistics()

            self.assertFalse(dlg.btn_start.isEnabled())
            self.assertIn("#e06c75", dlg.lbl_stats.text())
            self.assertIn("超過目前 Context 限制", dlg.lbl_stats.text())
            dlg.close()

    def test_scope_dialog_local_server_offline_disables_start_button(self):
        """驗證當本機模型（LM Studio / Ollama）未啟動時，顯示 Local LLM 服務未上線並禁用開始按鈕，絕不誤報 Context 不足。"""
        self.patcher_status.stop()  # 停止 setup 預設的 online mock
        try:
            with patch("services.ai_service.AIService.check_local_server_status") as mock_status, \
                 patch("services.ai_service.AIService.load_settings") as mock_settings:
                mock_settings.return_value = {
                    "provider": "LM Studio",
                    "api_urls": {"LM Studio": "http://localhost:1234/v1/chat/completions"},
                    "api_keys": {"LM Studio": ""},
                    "models": {"LM Studio": "qwen2.5-7b"},
                    "context_limits": {"LM Studio": 131072},
                    "prompts": {}
                }
                mock_status.return_value = (False, "LM Studio 服務未啟動（連線遭拒或超時）")

                dlg = AIScopeDialog(parent=self.main_win, current_item=self.ch1, task_type="character")
                dlg.update_statistics()

                # 驗證開始按鈕被禁用
                self.assertFalse(dlg.btn_start.isEnabled())
                # 驗證燈號為紅色
                self.assertIn("#e06c75", dlg.lbl_stats.text())
                # 驗證明確提示 Local LLM 服務未上線
                self.assertIn("Local LLM 服務未上線", dlg.lbl_stats.text())
                self.assertIn("未連線（服務未啟動）", dlg.lbl_stats.text())
                # 驗證絕不誤報「超過目前 Context 限制」
                self.assertNotIn("超過目前 Context 限制", dlg.lbl_stats.text())
                self.assertNotIn("131,072", dlg.lbl_stats.text())

                # 驗證重新檢查服務按鈕存在
                self.assertTrue(hasattr(dlg, "btn_check_connection"))

                # 模擬使用者啟動 LM Studio 後點選重新檢查服務
                mock_status.return_value = (True, "連線正常")
                with patch("services.ai_service.AIService.fetch_context_limit", return_value=32768):
                    dlg.btn_check_connection.click()
                    self.assertTrue(dlg.local_server_online)
                    self.assertEqual(dlg.context_limit, 32768)

                dlg.close()
        finally:
            self.mock_status = self.patcher_status.start()

    def test_scope_dialog_tree_selection_updates_stats(self):
        """驗證在自訂勾選模式下，全選、全不選與單項勾選能即時更新統計與文字。"""
        dlg = AIScopeDialog(parent=self.main_win, current_item=self.ch1, task_type="character")
        dlg.radio_custom.setChecked(True)

        # 初始狀態全選
        scope_data = dlg.get_scope_content()
        self.assertEqual(scope_data["chapter_count"], 2)

        # 點選全不選
        dlg.deselect_all_items()
        scope_data_empty = dlg.get_scope_content()
        self.assertEqual(scope_data_empty["chapter_count"], 0)
        self.assertFalse(dlg.btn_start.isEnabled())
        self.assertIn("無有效文字可供分析", dlg.lbl_stats.text())

        # 點選全選
        dlg.select_all_items()
        scope_data_all = dlg.get_scope_content()
        self.assertEqual(scope_data_all["chapter_count"], 2)

        dlg.close()

    def test_scope_dialog_empty_content_prevention(self):
        """驗證當所選章節內文為空時，介面顯示警告提示並禁用開始按鈕。"""
        empty_ch = self.mc.tree.create_item("空白章節", is_folder=False, content="")
        self.vol_item.addChild(empty_ch)

        dlg = AIScopeDialog(parent=self.main_win, current_item=empty_ch, task_type="character")
        dlg.radio_current.setChecked(True)

        self.assertFalse(dlg.btn_start.isEnabled())
        self.assertIn("無有效文字可供分析", dlg.lbl_stats.text())
        dlg.close()


if __name__ == "__main__":
    unittest.main()

