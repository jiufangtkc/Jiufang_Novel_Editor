import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.writing_log_service import WritingLogService


class TestWritingLogService(unittest.TestCase):
    """驗證 WritingLogService 純邏輯計算與資料格式化。"""

    def test_calculate_dashboard_metrics_empty(self):
        metrics = WritingLogService.calculate_dashboard_metrics([])
        self.assertEqual(metrics["total_words"], 0)
        self.assertEqual(metrics["total_duration"], 0)
        self.assertEqual(metrics["total_manual_words"], 0)
        self.assertEqual(metrics["active_days"], 0)
        self.assertIn("100% 純手創", metrics["ai_main"])
        self.assertIn("零 AI 介入", metrics["ai_sub"])

    def test_calculate_dashboard_metrics_mixed(self):
        logs = [
            {
                "date": "2026-09-01",
                "duration": 3660,
                "word_count": 2000,
                "ai_continuation_chars": 500,
                "ai_chat_count": 3,
                "ai_details": {
                    "character": 1,
                    "world": 1,
                    "timeline": 0,
                    "proofread": 2,
                    "impression": 0,
                    "chat": 3
                }
            },
            {
                "date": "2026-09-02",
                "duration": 1800,
                "word_count": 1000,
                "ai_continuation_chars": 0,
                "ai_chat_count": 0,
                "ai_details": {}
            }
        ]

        metrics = WritingLogService.calculate_dashboard_metrics(logs)
        self.assertEqual(metrics["total_words"], 3000)
        self.assertEqual(metrics["total_ai_chars"], 500)
        self.assertEqual(metrics["total_manual_words"], 2500)
        self.assertEqual(metrics["active_days"], 2)
        self.assertEqual(metrics["avg_words"], 1500)
        self.assertEqual(metrics["total_hours"], 1)
        self.assertEqual(metrics["total_mins"], 31)
        self.assertIn("83% 手創", metrics["ai_main"])
        self.assertIn("含正文擴寫", metrics["ai_sub"])

    def test_prepare_chart_data(self):
        logs = [
            {"date": "2026-09-01", "word_count": 100},
            {"date": "2026-09-02", "word_count": 200},
            {"date": "2026-09-03", "word_count": 300},
        ]
        dates, vals, ai_chars, ai_chats, ai_details, full_map = WritingLogService.prepare_chart_data(logs)
        self.assertEqual(dates, ["2026-09-01", "2026-09-02", "2026-09-03"])
        self.assertEqual(vals, [100, 200, 300])
        self.assertEqual(full_map["2026-09-02"], 200)

    def test_format_table_rows(self):
        logs = [
            {
                "date": "2026-09-01",
                "duration": 90,
                "word_count": 500,
                "ai_continuation_chars": 50,
                "ai_chat_count": 1,
                "ai_details": {"chat": 1}
            }
        ]
        rows = WritingLogService.format_table_rows(logs)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["date_str"], "2026-09-01")
        self.assertEqual(rows[0]["duration_str"], "1 分 30 秒")
        self.assertEqual(rows[0]["manual_words"], 450)
        self.assertEqual(rows[0]["ai_chars"], 50)
        self.assertIn("[💬靈感 1]", rows[0]["chat_display"])


if __name__ == "__main__":
    unittest.main()
