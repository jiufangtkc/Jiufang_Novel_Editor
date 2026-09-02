import sqlite3
import datetime

class DatabaseMigrations:
    """管理 SQLite 資料庫 schema_version 與歷代版本升級 (Migrations)。"""
    CURRENT_SCHEMA_VERSION = 10

    @staticmethod
    def get_current_schema_version(cursor: sqlite3.Cursor) -> int:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'")
        if not cursor.fetchone():
            return 0
        cursor.execute("SELECT MAX(version) FROM schema_version")
        row = cursor.fetchone()
        return row[0] if row and row[0] is not None else 0

    @staticmethod
    def detect_legacy_version(cursor: sqlite3.Cursor) -> int:
        """偵測未建立 schema_version 資料表的舊版 DB 版本。"""
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        if "project_info" not in tables and "chapters" not in tables:
            return 0  # 全新空資料庫
        
        # 檢查 project_info 欄位
        cursor.execute("PRAGMA table_info(project_info)")
        p_cols = {row[1] for row in cursor.fetchall()}
        if "global_font_family" not in p_cols:
            return 1
            
        # 檢查 chapters 欄位
        cursor.execute("PRAGMA table_info(chapters)")
        ch_cols = {row[1] for row in cursor.fetchall()}
        if "scene_summary" not in ch_cols:
            return 2
            
        if "snapshots" not in tables:
            return 3
            
        # 檢查 writing_logs 欄位
        cursor.execute("PRAGMA table_info(writing_logs)")
        w_cols = {row[1] for row in cursor.fetchall()}
        if "ai_continuation_count" not in w_cols:
            return 4
            
        if "target_word_count" not in p_cols:
            return 5

        if "category_order" not in p_cols:
            return 6
            
        if "proofread_results" not in tables:
            return 7

        if "is_expanded" not in ch_cols:
            return 8

        if "daily_target_word_count" not in p_cols:
            return 9

        return 10

    @staticmethod
    def upgrade_v1_to_v2(cursor: sqlite3.Cursor):
        """v1 -> v2：project_info 增加字型設定欄位"""
        cursor.execute("PRAGMA table_info(project_info)")
        cols = {row[1] for row in cursor.fetchall()}
        if "global_font_family" not in cols:
            cursor.execute("ALTER TABLE project_info ADD COLUMN global_font_family TEXT")
        if "global_font_size" not in cols:
            cursor.execute("ALTER TABLE project_info ADD COLUMN global_font_size INTEGER")
        if "editor_font_family" not in cols:
            cursor.execute("ALTER TABLE project_info ADD COLUMN editor_font_family TEXT")
        if "editor_font_size" not in cols:
            cursor.execute("ALTER TABLE project_info ADD COLUMN editor_font_size INTEGER")

    @staticmethod
    def upgrade_v2_to_v3(cursor: sqlite3.Cursor):
        """v2 -> v3：chapters 增加幕（Scene）屬性欄位"""
        cursor.execute("PRAGMA table_info(chapters)")
        cols = {row[1] for row in cursor.fetchall()}
        if "scene_summary" not in cols:
            cursor.execute("ALTER TABLE chapters ADD COLUMN scene_summary TEXT DEFAULT ''")
        if "scene_pov" not in cols:
            cursor.execute("ALTER TABLE chapters ADD COLUMN scene_pov TEXT DEFAULT ''")
        if "scene_location" not in cols:
            cursor.execute("ALTER TABLE chapters ADD COLUMN scene_location TEXT DEFAULT ''")

    @staticmethod
    def upgrade_v3_to_v4(cursor: sqlite3.Cursor):
        """v3 -> v4：新增版本快照表格 snapshots"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                note TEXT,
                timestamp TEXT,
                word_count INTEGER,
                project_data TEXT
            )
        ''')

    @staticmethod
    def upgrade_v4_to_v5(cursor: sqlite3.Cursor):
        """v4 -> v5：writing_logs 增加 AI 介入度追蹤欄位"""
        cursor.execute("PRAGMA table_info(writing_logs)")
        cols = {row[1] for row in cursor.fetchall()}
        if "ai_continuation_count" not in cols:
            cursor.execute("ALTER TABLE writing_logs ADD COLUMN ai_continuation_count INTEGER DEFAULT 0")
        if "ai_continuation_chars" not in cols:
            cursor.execute("ALTER TABLE writing_logs ADD COLUMN ai_continuation_chars INTEGER DEFAULT 0")
        if "ai_chat_count" not in cols:
            cursor.execute("ALTER TABLE writing_logs ADD COLUMN ai_chat_count INTEGER DEFAULT 0")

    @staticmethod
    def upgrade_v5_to_v6(cursor: sqlite3.Cursor):
        """v5 -> v6：project_info 增加 target_word_count 專案目標字數欄位"""
        cursor.execute("PRAGMA table_info(project_info)")
        cols = {row[1] for row in cursor.fetchall()}
        if "target_word_count" not in cols:
            cursor.execute("ALTER TABLE project_info ADD COLUMN target_word_count INTEGER DEFAULT 100000")

    @staticmethod
    def upgrade_v6_to_v7(cursor: sqlite3.Cursor):
        """v6 -> v7：project_info 增加 category_order 欄位，支援使用者自訂分類排列"""
        cursor.execute("PRAGMA table_info(project_info)")
        cols = {row[1] for row in cursor.fetchall()}
        if "category_order" not in cols:
            cursor.execute("ALTER TABLE project_info ADD COLUMN category_order TEXT DEFAULT NULL")

    @staticmethod
    def upgrade_v7_to_v8(cursor: sqlite3.Cursor):
        """v7 -> v8：新增 proofread_results 與 proofread_ignored_rules 表格"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS proofread_results (
                id TEXT PRIMARY KEY,
                category TEXT,
                node_id TEXT,
                chapter_name TEXT,
                char_offset INTEGER,
                match_len INTEGER,
                original_text TEXT,
                suggestion TEXT,
                reason TEXT,
                status TEXT,
                created_at TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS proofread_ignored_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_type TEXT,
                target_word TEXT,
                created_at TEXT
            )
        ''')

    @staticmethod
    def upgrade_v8_to_v9(cursor: sqlite3.Cursor):
        """v8 -> v9：chapters 增加 is_expanded 欄位；project_info 增加 expanded_categories 欄位"""
        cursor.execute("PRAGMA table_info(chapters)")
        ch_cols = {row[1] for row in cursor.fetchall()}
        if "is_expanded" not in ch_cols:
            cursor.execute("ALTER TABLE chapters ADD COLUMN is_expanded INTEGER DEFAULT 1")

        cursor.execute("PRAGMA table_info(project_info)")
        p_cols = {row[1] for row in cursor.fetchall()}
        if "expanded_categories" not in p_cols:
            cursor.execute("ALTER TABLE project_info ADD COLUMN expanded_categories TEXT DEFAULT NULL")

    @staticmethod
    def upgrade_v9_to_v10(cursor: sqlite3.Cursor):
        """v9 -> v10：project_info 增加 daily_target_word_count 欄位"""
        cursor.execute("PRAGMA table_info(project_info)")
        p_cols = {row[1] for row in cursor.fetchall()}
        if "daily_target_word_count" not in p_cols:
            cursor.execute("ALTER TABLE project_info ADD COLUMN daily_target_word_count INTEGER DEFAULT 1000")

    @classmethod
    def apply_migrations(cls, cursor: sqlite3.Cursor):
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT
            )
        ''')

        v = cls.get_current_schema_version(cursor)
        if v == 0:
            v = cls.detect_legacy_version(cursor)

        migrations = [
            (1, cls.upgrade_v1_to_v2),
            (2, cls.upgrade_v2_to_v3),
            (3, cls.upgrade_v3_to_v4),
            (4, cls.upgrade_v4_to_v5),
            (5, cls.upgrade_v5_to_v6),
            (6, cls.upgrade_v6_to_v7),
            (7, cls.upgrade_v7_to_v8),
            (8, cls.upgrade_v8_to_v9),
            (9, cls.upgrade_v9_to_v10),
        ]

        for from_v, step_fn in migrations:
            if v <= from_v:
                step_fn(cursor)
                target_v = from_v + 1
                cursor.execute(
                    "INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (?, ?)",
                    (target_v, now_str)
                )
                v = target_v

        cursor.execute(
            "INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (?, ?)",
            (cls.CURRENT_SCHEMA_VERSION, now_str)
        )
