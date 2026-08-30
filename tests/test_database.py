import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.models import JneProject, ProjectInfo, ChapterNode, CardNode, WritingLogEntry
from services.database import DatabaseService


class TestDatabaseService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_project.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_and_load_project(self):
        project = JneProject()
        project.project_info = ProjectInfo(
            title="測試小說作品",
            logline="這是一部單元測試用的小說故事大綱。",
            global_font_family="Iansui",
            global_font_size=14,
            editor_font_family="Iansui",
            editor_font_size=13
        )
        project.current_theme = "celadon"

        # 建立章節樹（第一卷 -> 第一章 -> 第一節）
        vol = ChapterNode(name="第一卷：起承轉合", node_type="folder")
        chap1 = ChapterNode(name="第一章：風起雲湧", node_type="folder")
        sec1 = ChapterNode(name="第一節：序幕拉開", node_type="file", content="# 序幕\n這是內文段落。", mark="Draft")
        chap1.children.append(sec1)
        vol.children.append(chap1)
        project.tree.append(vol)

        # 建立四類卡片
        card_summary = CardNode(title="主線核心", content="主角踏上冒險旅途", color="#3C3F41")
        project.project_cards["summary"].append(card_summary)

        card_char = CardNode(title="主角設定", content="性格堅韌不拔", color="#4CAF50")
        card_char_sub = CardNode(title="專屬武器", content="青芒古劍", color="#2196F3")
        card_char.children.append(card_char_sub)
        project.project_cards["character"].append(card_char)

        # 建立寫作日誌
        project.writing_logs.append(WritingLogEntry(date="2026-08-20", duration=3600, word_count=2500))

        # 儲存至 SQLite
        DatabaseService.save_project(project, self.db_path)
        self.assertTrue(os.path.exists(self.db_path))

        # 讀取並驗證
        loaded = DatabaseService.load_project(self.db_path)
        self.assertEqual(loaded.project_info.title, "測試小說作品")
        self.assertEqual(loaded.project_info.logline, "這是一部單元測試用的小說故事大綱。")
        self.assertEqual(loaded.current_theme, "celadon")
        self.assertEqual(loaded.project_info.global_font_family, "Iansui")
        self.assertEqual(loaded.project_info.global_font_size, 14)
        self.assertEqual(loaded.project_info.editor_font_size, 13)

        # 驗證章節樹階層
        self.assertEqual(len(loaded.tree), 1)
        self.assertEqual(loaded.tree[0].name, "第一卷：起承轉合")
        self.assertEqual(len(loaded.tree[0].children), 1)
        self.assertEqual(loaded.tree[0].children[0].name, "第一章：風起雲湧")
        self.assertEqual(len(loaded.tree[0].children[0].children), 1)
        self.assertEqual(loaded.tree[0].children[0].children[0].name, "第一節：序幕拉開")
        self.assertEqual(loaded.tree[0].children[0].children[0].content, "# 序幕\n這是內文段落。")
        self.assertEqual(loaded.tree[0].children[0].children[0].mark, "Draft")

        # 驗證卡片
        self.assertEqual(len(loaded.project_cards["summary"]), 1)
        self.assertEqual(loaded.project_cards["summary"][0].title, "主線核心")
        self.assertEqual(len(loaded.project_cards["character"]), 1)
        self.assertEqual(loaded.project_cards["character"][0].title, "主角設定")
        self.assertEqual(len(loaded.project_cards["character"][0].children), 1)
        self.assertEqual(loaded.project_cards["character"][0].children[0].title, "專屬武器")

        # 驗證寫作日誌
        self.assertEqual(len(loaded.writing_logs), 1)
        self.assertEqual(loaded.writing_logs[0].date, "2026-08-20")
        self.assertEqual(loaded.writing_logs[0].duration, 3600)
        self.assertEqual(loaded.writing_logs[0].word_count, 2500)


if __name__ == "__main__":
    unittest.main()
