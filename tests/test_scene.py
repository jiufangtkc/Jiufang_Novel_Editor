"""
test_scene.py — Phase 8.5 場景管理系統測試套件

涵蓋：
  1. ChapterNode 新欄位預設值
  2. DatabaseService 儲存/讀取 scene 節點（含 3 個 scene 欄位）
  3. 向後相容測試（舊 DB 無 scene 欄仍可讀取）
  4. scene 節點序列化/反序列化完整性
  5. SceneMetadataDialog 初始值填充與 get_metadata()
"""

import os
import tempfile
import sqlite3
import sys
import unittest
from PyQt6.QtWidgets import QApplication

# 確保 import 路徑正確
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.models import ChapterNode, JneProject, ProjectInfo
from services.database import DatabaseService

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)


# ─────────────────────────────────────────────
# 測試 1：ChapterNode 新欄位預設值
# ─────────────────────────────────────────────

class TestChapterNodeDefaults(unittest.TestCase):
    def test_scene_fields_default_empty(self):
        """scene 節點三個 metadata 欄位預設均為空字串。"""
        node = ChapterNode(name="測試場景", node_type="scene")
        self.assertEqual(node.scene_summary, "")
        self.assertEqual(node.scene_pov, "")
        self.assertEqual(node.scene_location, "")

    def test_file_node_scene_fields_default_empty(self):
        """file 節點的 scene 欄位預設也應為空字串（不強制填值）。"""
        node = ChapterNode(name="第一章", node_type="file")
        self.assertEqual(node.scene_summary, "")
        self.assertEqual(node.scene_pov, "")
        self.assertEqual(node.scene_location, "")

    def test_scene_node_literal_valid(self):
        """'scene' 為合法的 node_type 值。"""
        node = ChapterNode(name="場景一", node_type="scene",
                           scene_summary="主角遇見敵人",
                           scene_pov="主角小明（第一人稱）",
                           scene_location="城市廣場")
        self.assertEqual(node.node_type, "scene")
        self.assertEqual(node.scene_summary, "主角遇見敵人")
        self.assertEqual(node.scene_pov, "主角小明（第一人稱）")
        self.assertEqual(node.scene_location, "城市廣場")


# ─────────────────────────────────────────────
# 測試 2：DatabaseService 儲存/讀取 scene 節點
# ─────────────────────────────────────────────

def _make_project_with_scene() -> JneProject:
    """建立含 scene 節點的 JneProject 供測試用。"""
    project = JneProject()
    project.project_info = ProjectInfo(title="場景測試專案")

    root = ChapterNode(name="場景測試專案", node_type="folder")
    chapter = ChapterNode(name="第一章", node_type="file", content="章節內容", mark="Draft")
    scene = ChapterNode(
        name="場景一：相遇",
        node_type="scene",
        content="場景正文",
        mark="Draft",
        scene_summary="主角與配角在廣場偶遇",
        scene_pov="主角小明",
        scene_location="城市廣場"
    )
    chapter.children.append(scene)
    root.children.append(chapter)
    project.tree.append(root)
    return project


class TestDatabaseSceneSupport(unittest.TestCase):
    def test_save_and_load_scene_node(self):
        """儲存含 scene 節點的專案後，讀回資料應完整一致。"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            project = _make_project_with_scene()
            DatabaseService.save_project(project, db_path)

            loaded = DatabaseService.load_project(db_path)
            self.assertEqual(len(loaded.tree), 1)

            root_node = loaded.tree[0]
            self.assertEqual(root_node.node_type, "folder")
            self.assertEqual(len(root_node.children), 1)

            chapter_node = root_node.children[0]
            self.assertEqual(chapter_node.node_type, "file")
            self.assertEqual(len(chapter_node.children), 1)

            scene_node = chapter_node.children[0]
            self.assertEqual(scene_node.node_type, "scene")
            self.assertEqual(scene_node.name, "場景一：相遇")
            self.assertEqual(scene_node.content, "場景正文")
            self.assertEqual(scene_node.scene_summary, "主角與配角在廣場偶遇")
            self.assertEqual(scene_node.scene_pov, "主角小明")
            self.assertEqual(scene_node.scene_location, "城市廣場")
        finally:
            os.unlink(db_path)

    def test_scene_fields_persist_on_overwrite(self):
        """多次存檔（DELETE + INSERT）後，scene metadata 不遺失。"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            project = _make_project_with_scene()
            DatabaseService.save_project(project, db_path)
            # 更新 scene_pov 後再次存檔
            scene = project.tree[0].children[0].children[0]
            scene.scene_pov = "配角小花"
            DatabaseService.save_project(project, db_path)

            loaded = DatabaseService.load_project(db_path)
            scene_node = loaded.tree[0].children[0].children[0]
            self.assertEqual(scene_node.scene_pov, "配角小花")
        finally:
            os.unlink(db_path)


# ─────────────────────────────────────────────
# 測試 3：向後相容（舊 DB 無 scene 欄）
# ─────────────────────────────────────────────

class TestBackwardCompatibility(unittest.TestCase):
    def test_old_db_without_scene_columns(self):
        """不含 scene 欄的舊格式 DB 讀取時，scene 欄應 fallback 為空字串。"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            # 建立不含 scene 欄的舊版 DB
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS project_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT, logline TEXT, current_theme TEXT,
                    global_font_family TEXT, global_font_size INTEGER,
                    editor_font_family TEXT, editor_font_size INTEGER
                )
            ''')
            cursor.execute('''
                INSERT INTO project_info
                    (title, logline, current_theme, global_font_family,
                     global_font_size, editor_font_family, editor_font_size)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', ("舊版專案", "", "default", "Iansui", 12, "Iansui", 12))

            # 不含 scene 欄的舊版 chapters 表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chapters (
                    id TEXT PRIMARY KEY, parent_id TEXT, name TEXT,
                    node_type TEXT, content TEXT, mark TEXT, sort_order INTEGER,
                    FOREIGN KEY (parent_id) REFERENCES chapters(id)
                )
            ''')
            cursor.execute('''
                INSERT INTO chapters (id, parent_id, name, node_type, content, mark, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', ("test-id-1", None, "第一章", "file", "章節內容", "Draft", 0))
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cards (
                    id TEXT PRIMARY KEY, parent_id TEXT, category TEXT,
                    title TEXT, content TEXT, color TEXT, is_collapsed INTEGER, sort_order INTEGER
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS writing_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE, duration INTEGER, word_count INTEGER
                )
            ''')
            conn.commit()
            conn.close()

            # init_db migration 應自動補充 scene 欄
            DatabaseService.init_db(db_path)

            # 讀取應成功，且 scene 欄為空字串（fallback）
            loaded = DatabaseService.load_project(db_path)
            self.assertEqual(len(loaded.tree), 1)
            chapter = loaded.tree[0]
            self.assertEqual(chapter.name, "第一章")
            self.assertEqual(chapter.scene_summary, "")
            self.assertEqual(chapter.scene_pov, "")
            self.assertEqual(chapter.scene_location, "")
        finally:
            os.unlink(db_path)


# ─────────────────────────────────────────────
# 測試 4：SceneMetadataDialog 初始值與 get_metadata()
# ─────────────────────────────────────────────

class TestSceneMetadataDialog(unittest.TestCase):
    def test_dialog_initial_values(self):
        """Dialog 開啟時應正確填入初始值。"""
        from views.dialogs.scene_metadata_dialog import SceneMetadataDialog
        dlg = SceneMetadataDialog(
            parent=None,
            scene_name="場景一",
            scene_summary="摘要內容",
            scene_pov="主角",
            scene_location="廣場"
        )
        self.assertEqual(dlg.summary_edit.toPlainText(), "摘要內容")
        self.assertEqual(dlg.pov_edit.text(), "主角")
        self.assertEqual(dlg.location_edit.text(), "廣場")
        dlg.close()

    def test_get_metadata_returns_correct_values(self):
        """修改欄位後，get_metadata() 應傳回更新後的值。"""
        from views.dialogs.scene_metadata_dialog import SceneMetadataDialog
        dlg = SceneMetadataDialog(parent=None)
        dlg.summary_edit.setPlainText("新摘要")
        dlg.pov_edit.setText("配角")
        dlg.location_edit.setText("咖啡廳")
        meta = dlg.get_metadata()
        self.assertEqual(meta["scene_summary"], "新摘要")
        self.assertEqual(meta["scene_pov"], "配角")
        self.assertEqual(meta["scene_location"], "咖啡廳")
        dlg.close()

    def test_empty_initial_values(self):
        """無初始值時，欄位應為空。"""
        from views.dialogs.scene_metadata_dialog import SceneMetadataDialog
        dlg = SceneMetadataDialog(parent=None)
        self.assertEqual(dlg.summary_edit.toPlainText(), "")
        self.assertEqual(dlg.pov_edit.text(), "")
        self.assertEqual(dlg.location_edit.text(), "")
        dlg.close()


if __name__ == "__main__":
    unittest.main()
