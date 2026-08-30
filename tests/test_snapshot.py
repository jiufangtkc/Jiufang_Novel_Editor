import os
import sys
import tempfile
import unittest
from PyQt6.QtWidgets import QApplication

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.models import JneProject, ProjectInfo, ChapterNode, CardNode, WritingLogEntry
from services.database import DatabaseService
from views.dialogs.snapshot_dialog import SnapshotDialog

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)


class TestSnapshotService(unittest.TestCase):
    def _create_sample_project(self):
        project = JneProject(
            project_info=ProjectInfo(
                title="快照測試作品",
                logline="這是一部測試快照功能的作品",
                global_font_family="Iansui",
                global_font_size=13,
                editor_font_family="Iansui",
                editor_font_size=14,
                target_word_count=150000
            ),
            current_theme="celadon"
        )
        # 加入章節與幕
        vol = ChapterNode(name="第一卷", node_type="folder")
        ch1 = ChapterNode(name="第一章 起點", node_type="file", content="天地初開，萬物生長。這裡是第一章。")
        scene1 = ChapterNode(
            name="第一幕 森林對決",
            node_type="scene",
            content="樹影婆娑，劍光閃爍。",
            scene_summary="主角與刺客在黑夜密林中交鋒",
            scene_pov="主角",
            scene_location="黑木森林"
        )
        ch1.children.append(scene1)
        vol.children.append(ch1)
        project.tree.append(vol)

        # 加入卡片
        card1 = CardNode(title="主角", content="熱血少年", color="#2b78e4")
        project.project_cards["character"].append(card1)

        # 加入日誌
        project.writing_logs.append(WritingLogEntry(date="2026-08-21", duration=1800, word_count=500))
        return project

    def test_save_and_list_snapshots(self):
        sample_project = self._create_sample_project()
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_snapshot.db")
            DatabaseService.save_project(sample_project, db_path)

            # 建立第一個快照
            snap1_id = DatabaseService.save_snapshot(
                db_path=db_path,
                name="初稿快照",
                note="完成第一幕草稿",
                project=sample_project
            )
            self.assertGreater(snap1_id, 0)

            # 建立第二個快照
            sample_project.project_info.title = "快照測試作品（二修版）"
            snap2_id = DatabaseService.save_snapshot(
                db_path=db_path,
                name="二修快照",
                note="修改書名與內容",
                project=sample_project
            )
            self.assertGreater(snap2_id, snap1_id)

            # 查詢快照清單
            snapshots = DatabaseService.list_snapshots(db_path)
            self.assertEqual(len(snapshots), 2)
            # 依 ID DESC 排序，第二個在前面
            self.assertEqual(snapshots[0]["id"], snap2_id)
            self.assertEqual(snapshots[0]["name"], "二修快照")
            self.assertEqual(snapshots[0]["note"], "修改書名與內容")
            self.assertEqual(snapshots[1]["id"], snap1_id)
            self.assertEqual(snapshots[1]["name"], "初稿快照")
            self.assertGreater(snapshots[1]["word_count"], 0)

    def test_load_and_restore_snapshot_integrity(self):
        sample_project = self._create_sample_project()
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_snapshot.db")
            DatabaseService.save_project(sample_project, db_path)

            snap_id = DatabaseService.save_snapshot(
                db_path=db_path,
                name="完整性快照",
                note="包含樹、幕、卡片與日誌",
                project=sample_project
            )

            # 載入快照
            loaded_project = DatabaseService.load_snapshot(db_path, snap_id)
            self.assertIsNotNone(loaded_project)
            self.assertEqual(loaded_project.project_info.title, "快照測試作品")
            self.assertEqual(loaded_project.project_info.target_word_count, 150000)
            self.assertEqual(loaded_project.current_theme, "celadon")

            # 驗證章節與幕結構
            self.assertEqual(len(loaded_project.tree), 1)
            vol = loaded_project.tree[0]
            self.assertEqual(vol.name, "第一卷")
            self.assertEqual(vol.node_type, "folder")
            self.assertEqual(len(vol.children), 1)

            ch1 = vol.children[0]
            self.assertEqual(ch1.name, "第一章 起點")
            self.assertEqual(ch1.node_type, "file")
            self.assertEqual(len(ch1.children), 1)

            sc1 = ch1.children[0]
            self.assertEqual(sc1.name, "第一幕 森林對決")
            self.assertEqual(sc1.node_type, "scene")
            self.assertEqual(sc1.scene_summary, "主角與刺客在黑夜密林中交鋒")
            self.assertEqual(sc1.scene_pov, "主角")
            self.assertEqual(sc1.scene_location, "黑木森林")
            self.assertEqual(sc1.content, "樹影婆娑，劍光閃爍。")

            # 驗證卡片
            self.assertEqual(len(loaded_project.project_cards["character"]), 1)
            self.assertEqual(loaded_project.project_cards["character"][0].title, "主角")

            # 驗證日誌
            self.assertEqual(len(loaded_project.writing_logs), 1)
            self.assertEqual(loaded_project.writing_logs[0].word_count, 500)

    def test_delete_snapshot(self):
        sample_project = self._create_sample_project()
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_snapshot.db")
            DatabaseService.save_project(sample_project, db_path)

            snap1_id = DatabaseService.save_snapshot(db_path, "快照1", "備註1", sample_project)
            snap2_id = DatabaseService.save_snapshot(db_path, "快照2", "備註2", sample_project)

            self.assertEqual(len(DatabaseService.list_snapshots(db_path)), 2)

            # 刪除快照 1
            ok = DatabaseService.delete_snapshot(db_path, snap1_id)
            self.assertTrue(ok)

            snapshots = DatabaseService.list_snapshots(db_path)
            self.assertEqual(len(snapshots), 1)
            self.assertEqual(snapshots[0]["id"], snap2_id)

            # 重複刪除回傳 False
            ok_again = DatabaseService.delete_snapshot(db_path, snap1_id)
            self.assertFalse(ok_again)

    def test_snapshot_dialog_populate_and_selection(self):
        sample_project = self._create_sample_project()
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "dialog_test.db")
            DatabaseService.save_project(sample_project, db_path)
            DatabaseService.save_snapshot(db_path, "測試快照A", "測試備註A", sample_project)

            dlg = SnapshotDialog(db_path=db_path)
            self.assertEqual(dlg.table.rowCount(), 1)
            self.assertEqual(dlg.table.item(0, 1).text(), "測試快照A")
            self.assertEqual(dlg.table.item(0, 3).text(), "測試備註A")

            # 選取第 0 列
            dlg.table.selectRow(0)
            selected_id = dlg.get_selected_snapshot_id()
            self.assertIsNotNone(selected_id)
            dlg.close()


if __name__ == "__main__":
    unittest.main()
