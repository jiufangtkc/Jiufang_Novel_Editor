import sqlite3
import json
import os
import uuid
from typing import Dict, Any, List, Optional
from models.models import JneProject, ProjectInfo, ChapterNode, CardNode, WritingLogEntry, BUILTIN_CATEGORIES
from services.storage import StorageService
from services.database_migrations import DatabaseMigrations

class DatabaseService:
    CURRENT_SCHEMA_VERSION = DatabaseMigrations.CURRENT_SCHEMA_VERSION

    # 委派至 DatabaseMigrations 確保相容性與清晰職責分離
    _get_current_schema_version = DatabaseMigrations.get_current_schema_version
    _detect_legacy_version = DatabaseMigrations.detect_legacy_version
    _upgrade_v1_to_v2 = DatabaseMigrations.upgrade_v1_to_v2
    _upgrade_v2_to_v3 = DatabaseMigrations.upgrade_v2_to_v3
    _upgrade_v3_to_v4 = DatabaseMigrations.upgrade_v3_to_v4
    _upgrade_v4_to_v5 = DatabaseMigrations.upgrade_v4_to_v5
    _upgrade_v5_to_v6 = DatabaseMigrations.upgrade_v5_to_v6
    _upgrade_v6_to_v7 = DatabaseMigrations.upgrade_v6_to_v7
    _upgrade_v7_to_v8 = DatabaseMigrations.upgrade_v7_to_v8
    _upgrade_v8_to_v9 = DatabaseMigrations.upgrade_v8_to_v9
    _apply_migrations = DatabaseMigrations.apply_migrations

    @staticmethod
    def init_db(db_path: str):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 建立核心資料表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                logline TEXT,
                current_theme TEXT,
                global_font_family TEXT,
                global_font_size INTEGER,
                editor_font_family TEXT,
                editor_font_size INTEGER,
                target_word_count INTEGER DEFAULT 100000,
                daily_target_word_count INTEGER DEFAULT 1000,
                category_order TEXT DEFAULT NULL,
                expanded_categories TEXT DEFAULT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chapters (
                id TEXT PRIMARY KEY,
                parent_id TEXT,
                name TEXT,
                node_type TEXT,
                content TEXT,
                mark TEXT,
                sort_order INTEGER,
                scene_summary TEXT DEFAULT '',
                scene_pov TEXT DEFAULT '',
                scene_location TEXT DEFAULT '',
                is_expanded INTEGER DEFAULT 1,
                FOREIGN KEY (parent_id) REFERENCES chapters(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cards (
                id TEXT PRIMARY KEY,
                parent_id TEXT,
                category TEXT,
                title TEXT,
                content TEXT,
                color TEXT,
                is_collapsed INTEGER,
                sort_order INTEGER,
                FOREIGN KEY (parent_id) REFERENCES cards(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS writing_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE,
                duration INTEGER,
                word_count INTEGER,
                ai_continuation_count INTEGER DEFAULT 0,
                ai_continuation_chars INTEGER DEFAULT 0,
                ai_chat_count INTEGER DEFAULT 0,
                ai_details TEXT DEFAULT '{}',
                paste_large_count INTEGER DEFAULT 0,
                delete_large_count INTEGER DEFAULT 0
            )
        ''')

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

        # 2. 執行版本遷移 Pipeline
        DatabaseService._apply_migrations(cursor)
        
        conn.commit()
        conn.close()

    @staticmethod
    def save_project(project: JneProject, db_path: str):
        DatabaseService.init_db(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Save Project Info
        cursor.execute('DELETE FROM project_info')
        # 序列化 category_order 為 JSON 字串
        category_order_json = json.dumps(getattr(project, 'category_order', []), ensure_ascii=False)
        expanded_categories = getattr(project.project_info, 'expanded_categories', None)
        expanded_categories_json = json.dumps(expanded_categories, ensure_ascii=False) if expanded_categories is not None else None
        cursor.execute(
            '''INSERT INTO project_info (
                title, logline, current_theme,
                global_font_family, global_font_size,
                editor_font_family, editor_font_size,
                target_word_count, daily_target_word_count,
                category_order, expanded_categories
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                project.project_info.title,
                project.project_info.logline,
                project.current_theme,
                project.project_info.global_font_family,
                project.project_info.global_font_size,
                project.project_info.editor_font_family,
                project.project_info.editor_font_size,
                getattr(project.project_info, 'target_word_count', 100000),
                getattr(project.project_info, 'daily_target_word_count', 1000),
                category_order_json,
                expanded_categories_json
            )
        )
        
        # Save Chapters (Recursively)
        cursor.execute('DELETE FROM chapters')
        def save_chapter(node: ChapterNode, parent_id: Optional[str], sort_order: int):
            cursor.execute('''
                INSERT INTO chapters (id, parent_id, name, node_type, content, mark, sort_order,
                                     scene_summary, scene_pov, scene_location, is_expanded)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                node.id, parent_id, node.name, node.node_type, node.content, node.mark, sort_order,
                node.scene_summary, node.scene_pov, node.scene_location,
                1 if getattr(node, 'is_expanded', True) else 0
            ))
            for idx, child in enumerate(node.children):
                save_chapter(child, node.id, idx)
                
        for idx, root_node in enumerate(project.tree):
            save_chapter(root_node, None, idx)
            
        # Save Cards (Recursively)
        cursor.execute('DELETE FROM cards')
        def save_card(node: CardNode, category: str, parent_id: Optional[str], sort_order: int):
            cursor.execute('''
                INSERT INTO cards (id, parent_id, category, title, content, color, is_collapsed, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (node.id, parent_id, category, node.title, node.content, node.color, 1 if node.is_collapsed else 0, sort_order))
            for idx, child in enumerate(node.children):
                save_card(child, category, node.id, idx)
                
        for category, cards in project.project_cards.items():
            for idx, card in enumerate(cards):
                save_card(card, category, None, idx)
                
        # Save Writing Logs
        for log in project.writing_logs:
            details_json = json.dumps(getattr(log, "ai_details", {}) or {}, ensure_ascii=False)
            cursor.execute('''
                INSERT INTO writing_logs (date, duration, word_count, ai_continuation_count, ai_continuation_chars, ai_chat_count, ai_details, paste_large_count, delete_large_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                duration=excluded.duration,
                word_count=excluded.word_count,
                ai_continuation_count=excluded.ai_continuation_count,
                ai_continuation_chars=excluded.ai_continuation_chars,
                ai_chat_count=excluded.ai_chat_count,
                ai_details=excluded.ai_details,
                paste_large_count=excluded.paste_large_count,
                delete_large_count=excluded.delete_large_count
            ''', (
                log.date, log.duration, log.word_count,
                getattr(log, "ai_continuation_count", 0),
                getattr(log, "ai_continuation_chars", 0),
                getattr(log, "ai_chat_count", 0),
                details_json,
                getattr(log, "paste_large_count", 0),
                getattr(log, "delete_large_count", 0)
            ))
            
        conn.commit()
        conn.close()

    @staticmethod
    def load_project(db_path: str) -> JneProject:
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database file not found: {db_path}")
            
        DatabaseService.init_db(db_path)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        project = JneProject()
        
        # Load Project Info
        cursor.execute('SELECT * FROM project_info LIMIT 1')
        p_row = cursor.fetchone()
        if p_row:
            keys = p_row.keys()
            global_font_family = p_row['global_font_family'] if 'global_font_family' in keys and p_row['global_font_family'] else "Iansui"
            global_font_size = p_row['global_font_size'] if 'global_font_size' in keys and p_row['global_font_size'] else 12
            editor_font_family = p_row['editor_font_family'] if 'editor_font_family' in keys and p_row['editor_font_family'] else "Iansui"
            editor_font_size = p_row['editor_font_size'] if 'editor_font_size' in keys and p_row['editor_font_size'] else 12
            target_word_count = p_row['target_word_count'] if 'target_word_count' in keys and p_row['target_word_count'] is not None else 100000
            daily_target_word_count = p_row['daily_target_word_count'] if 'daily_target_word_count' in keys and p_row['daily_target_word_count'] is not None else 1000

            project.project_info = ProjectInfo(
                title=p_row['title'],
                logline=p_row['logline'],
                global_font_family=global_font_family,
                global_font_size=int(global_font_size),
                editor_font_family=editor_font_family,
                editor_font_size=int(editor_font_size),
                target_word_count=int(target_word_count),
                daily_target_word_count=int(daily_target_word_count)
            )
            project.current_theme = p_row['current_theme']
            # 讀取 category_order（v7 新增欄位）
            if 'category_order' in keys and p_row['category_order']:
                try:
                    loaded_order = json.loads(p_row['category_order'])
                    if isinstance(loaded_order, list):
                        # 確保所有內建分類都在清單中
                        merged = list(loaded_order)
                        for builtin in BUILTIN_CATEGORIES:
                            if builtin not in merged:
                                merged.insert(BUILTIN_CATEGORIES.index(builtin), builtin)
                        project.category_order = merged
                except (json.JSONDecodeError, ValueError):
                    pass
            # 讀取 expanded_categories（v9 新增欄位）
            if 'expanded_categories' in keys and p_row['expanded_categories'] is not None:
                try:
                    loaded_exp = json.loads(p_row['expanded_categories'])
                    if isinstance(loaded_exp, list):
                        project.project_info.expanded_categories = loaded_exp
                except (json.JSONDecodeError, ValueError):
                    pass
            
        # Load Chapters
        cursor.execute('SELECT * FROM chapters ORDER BY parent_id, sort_order')
        chapters_rows = cursor.fetchall()
        chapters_map = {}
        chapter_keys = set()
        if chapters_rows:
            chapter_keys = set(chapters_rows[0].keys())
        for row in chapters_rows:
            is_expanded = bool(row['is_expanded']) if 'is_expanded' in chapter_keys and row['is_expanded'] is not None else True
            node = ChapterNode(
                name=row['name'],
                node_type=row['node_type'],
                id=row['id'],
                content=row['content'],
                mark=row['mark'],
                scene_summary=row['scene_summary'] if 'scene_summary' in chapter_keys and row['scene_summary'] else "",
                scene_pov=row['scene_pov'] if 'scene_pov' in chapter_keys and row['scene_pov'] else "",
                scene_location=row['scene_location'] if 'scene_location' in chapter_keys and row['scene_location'] else "",
                is_expanded=is_expanded
            )
            chapters_map[node.id] = {"node": node, "parent_id": row['parent_id']}
            
        for node_id, data in chapters_map.items():
            parent_id = data["parent_id"]
            if parent_id is None:
                project.tree.append(data["node"])
            elif parent_id in chapters_map:
                chapters_map[parent_id]["node"].children.append(data["node"])
                
        # Load Cards
        cursor.execute('SELECT * FROM cards ORDER BY parent_id, sort_order')
        cards_rows = cursor.fetchall()
        cards_map = {}
        for row in cards_rows:
            node = CardNode(
                title=row['title'],
                id=row['id'],
                content=row['content'],
                color=row['color'],
                is_collapsed=bool(row['is_collapsed'])
            )
            cards_map[node.id] = {"node": node, "parent_id": row['parent_id'], "category": row['category']}
            
        for node_id, data in cards_map.items():
            parent_id = data["parent_id"]
            if parent_id is None:
                category = data["category"]
                # 動態建立不在預設清單中的自訂分類 key
                if category not in project.project_cards:
                    project.project_cards[category] = []
                project.project_cards[category].append(data["node"])
            elif parent_id in cards_map:
                cards_map[parent_id]["node"].children.append(data["node"])
                
        # Load Writing Logs
        cursor.execute('SELECT * FROM writing_logs')
        logs_rows = cursor.fetchall()
        log_keys = set()
        if logs_rows:
            log_keys = set(logs_rows[0].keys())
        for row in logs_rows:
            details_raw = row['ai_details'] if 'ai_details' in log_keys and row['ai_details'] else '{}'
            try:
                ai_details = json.loads(details_raw) if isinstance(details_raw, str) else {}
            except Exception:
                ai_details = {}
            project.writing_logs.append(WritingLogEntry(
                date=row['date'],
                duration=row['duration'],
                word_count=row['word_count'],
                ai_continuation_count=row['ai_continuation_count'] if 'ai_continuation_count' in log_keys and row['ai_continuation_count'] is not None else 0,
                ai_continuation_chars=row['ai_continuation_chars'] if 'ai_continuation_chars' in log_keys and row['ai_continuation_chars'] is not None else 0,
                ai_chat_count=row['ai_chat_count'] if 'ai_chat_count' in log_keys and row['ai_chat_count'] is not None else 0,
                ai_details=ai_details,
                paste_large_count=row['paste_large_count'] if 'paste_large_count' in log_keys and row['paste_large_count'] is not None else 0,
                delete_large_count=row['delete_large_count'] if 'delete_large_count' in log_keys and row['delete_large_count'] is not None else 0
            ))

            
        conn.close()
        return project

    @staticmethod
    def migrate_json_to_sqlite(json_path: str, db_path: str):
        project = StorageService.load_project_from_json(json_path)
        DatabaseService.save_project(project, db_path)
        return project

    # =========================================================================
    # Phase 10：版本快照系統 (Snapshot Management)
    # =========================================================================

    @staticmethod
    def _project_to_dict(project: JneProject) -> dict:
        """將 JneProject dataclass 轉換為可序列化為 JSON 的字典。"""
        def _chapter_to_dict(ch: ChapterNode) -> dict:
            return {
                "name": ch.name,
                "node_type": ch.node_type,
                "id": ch.id,
                "content": ch.content,
                "mark": ch.mark,
                "scene_summary": ch.scene_summary,
                "scene_pov": ch.scene_pov,
                "scene_location": ch.scene_location,
                "children": [_chapter_to_dict(c) for c in ch.children]
            }

        def _card_to_dict(c: CardNode) -> dict:
            return {
                "title": c.title,
                "id": c.id,
                "content": c.content,
                "color": c.color,
                "is_collapsed": c.is_collapsed,
                "children": [_card_to_dict(child) for child in c.children]
            }

        return {
            "project_info": {
                "title": project.project_info.title,
                "logline": project.project_info.logline,
                "global_font_family": project.project_info.global_font_family,
                "global_font_size": project.project_info.global_font_size,
                "editor_font_family": project.project_info.editor_font_family,
                "editor_font_size": project.project_info.editor_font_size,
                "target_word_count": getattr(project.project_info, "target_word_count", 100000),
                "daily_target_word_count": getattr(project.project_info, "daily_target_word_count", 1000)
            },
            "current_theme": project.current_theme,
            "tree": [_chapter_to_dict(n) for n in project.tree],
            "project_cards": {
                cat: [_card_to_dict(c) for c in cards]
                for cat, cards in project.project_cards.items()
            },
            "category_order": getattr(project, 'category_order', list(project.project_cards.keys())),
            "writing_logs": [
                {
                    "date": l.date,
                    "duration": l.duration,
                    "word_count": l.word_count,
                    "ai_continuation_count": getattr(l, "ai_continuation_count", 0),
                    "ai_continuation_chars": getattr(l, "ai_continuation_chars", 0),
                    "ai_chat_count": getattr(l, "ai_chat_count", 0),
                    "ai_details": getattr(l, "ai_details", {}),
                    "paste_large_count": getattr(l, "paste_large_count", 0),
                    "delete_large_count": getattr(l, "delete_large_count", 0)
                }
                for l in project.writing_logs
            ]
        }

    @staticmethod
    def _dict_to_project(d: dict) -> JneProject:
        """從字典反序列化為 JneProject dataclass。"""
        p_info_d = d.get("project_info", {})
        project = JneProject(
            project_info=ProjectInfo(
                title=p_info_d.get("title", "未命名作品"),
                logline=p_info_d.get("logline", ""),
                global_font_family=p_info_d.get("global_font_family", "Iansui"),
                global_font_size=p_info_d.get("global_font_size", 12),
                editor_font_family=p_info_d.get("editor_font_family", "Iansui"),
                editor_font_size=p_info_d.get("editor_font_size", 12),
                target_word_count=p_info_d.get("target_word_count", 100000),
                daily_target_word_count=p_info_d.get("daily_target_word_count", 1000)
            ),
            current_theme=d.get("current_theme", "default")
        )

        def _dict_to_chapter(cd: dict) -> ChapterNode:
            node = ChapterNode(
                name=cd.get("name", ""),
                node_type=cd.get("node_type", "file"),
                id=cd.get("id", str(uuid.uuid4())),
                content=cd.get("content", ""),
                mark=cd.get("mark", "None"),
                scene_summary=cd.get("scene_summary", ""),
                scene_pov=cd.get("scene_pov", ""),
                scene_location=cd.get("scene_location", "")
            )
            for child_d in cd.get("children", []):
                node.children.append(_dict_to_chapter(child_d))
            return node

        for tree_d in d.get("tree", []):
            project.tree.append(_dict_to_chapter(tree_d))

        def _dict_to_card(card_d: dict) -> CardNode:
            card = CardNode(
                title=card_d.get("title", ""),
                id=card_d.get("id", str(uuid.uuid4())),
                content=card_d.get("content", ""),
                color=card_d.get("color", "#3C3F41"),
                is_collapsed=card_d.get("is_collapsed", False)
            )
            for child_d in card_d.get("children", []):
                card.children.append(_dict_to_card(child_d))
            return card

        for cat, cards in d.get("project_cards", {}).items():
            # 動態建立不在預設清單中的自訂分類 key
            project.project_cards[cat] = [_dict_to_card(c) for c in cards]

        # 讀取 category_order
        if "category_order" in d and isinstance(d["category_order"], list):
            loaded_order = d["category_order"]
            merged = list(loaded_order)
            for builtin in BUILTIN_CATEGORIES:
                if builtin not in merged:
                    merged.insert(BUILTIN_CATEGORIES.index(builtin), builtin)
            project.category_order = merged

        for log_d in d.get("writing_logs", []):
            project.writing_logs.append(WritingLogEntry(
                date=log_d.get("date", ""),
                duration=log_d.get("duration", 0),
                word_count=log_d.get("word_count", 0),
                ai_continuation_count=log_d.get("ai_continuation_count", 0),
                ai_continuation_chars=log_d.get("ai_continuation_chars", 0),
                ai_chat_count=log_d.get("ai_chat_count", 0),
                ai_details=log_d.get("ai_details", {}),
                paste_large_count=log_d.get("paste_large_count", 0),
                delete_large_count=log_d.get("delete_large_count", 0)
            ))

        return project

    @staticmethod
    def save_snapshot(db_path: str, name: str, note: str, project: JneProject, word_count: int = 0) -> int:
        """將專案當前狀態儲存為快照。"""
        import datetime
        import re
        DatabaseService.init_db(db_path)

        if word_count <= 0:
            # 自動計算總字數
            def _calc_words(nodes):
                total = 0
                for n in nodes:
                    if n.node_type in ("file", "scene") and n.content:
                        clean = re.sub(r'<[^>]+>', '', n.content)
                        clean = re.sub(r'[\s\r\n\t]+', '', clean)
                        c_zh = len(re.findall(r'[\u4e00-\u9fa5]', clean))
                        c_en = len(re.findall(r'[a-zA-Z0-9]+', clean))
                        total += (c_zh + c_en)
                    total += _calc_words(n.children)
                return total
            word_count = _calc_words(project.tree)

        project_dict = DatabaseService._project_to_dict(project)
        project_json = json.dumps(project_dict, ensure_ascii=False)
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO snapshots (name, note, timestamp, word_count, project_data)
            VALUES (?, ?, ?, ?, ?)
        ''', (name or "手動快照", note or "", now_str, word_count, project_json))
        conn.commit()
        snapshot_id = cursor.lastrowid
        conn.close()
        return snapshot_id

    @staticmethod
    def list_snapshots(db_path: str) -> List[Dict[str, Any]]:
        """查詢資料庫中所有快照清單（不包含巨大的 project_data 欄位）。"""
        DatabaseService.init_db(db_path)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, name, note, timestamp, word_count
            FROM snapshots
            ORDER BY id DESC
        ''')
        rows = cursor.fetchall()
        result = [
            {
                "id": row["id"],
                "name": row["name"],
                "note": row["note"],
                "timestamp": row["timestamp"],
                "word_count": row["word_count"]
            }
            for row in rows
        ]
        conn.close()
        return result

    @staticmethod
    def load_snapshot(db_path: str, snapshot_id: int) -> Optional[JneProject]:
        """讀取指定快照並還原為 JneProject dataclass。"""
        DatabaseService.init_db(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT project_data FROM snapshots WHERE id = ?', (snapshot_id,))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0]:
            return None

        project_dict = json.loads(row[0])
        return DatabaseService._dict_to_project(project_dict)

    @staticmethod
    def delete_snapshot(db_path: str, snapshot_id: int) -> bool:
        """刪除指定快照。"""
        DatabaseService.init_db(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM snapshots WHERE id = ?', (snapshot_id,))
        conn.commit()
        affected = cursor.rowcount > 0
        conn.close()
        return affected

    # ==========================================
    # AI 校稿結果與忽略規則 CRUD
    # ==========================================
    @staticmethod
    def save_proofread_result(db_path: str, result_dict: dict):
        DatabaseService.init_db(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO proofread_results (
                id, category, node_id, chapter_name, char_offset, match_len,
                original_text, suggestion, reason, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            result_dict.get('id'),
            result_dict.get('category'),
            result_dict.get('node_id'),
            result_dict.get('chapter_name'),
            result_dict.get('char_offset'),
            result_dict.get('match_len'),
            result_dict.get('original_text'),
            result_dict.get('suggestion'),
            result_dict.get('reason'),
            result_dict.get('status', 'pending'),
            result_dict.get('created_at', '')
        ))
        conn.commit()
        conn.close()

    @staticmethod
    def load_proofread_results(db_path: str) -> List[dict]:
        DatabaseService.init_db(db_path)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM proofread_results')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def update_proofread_result_status(db_path: str, result_id: str, new_status: str):
        DatabaseService.init_db(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE proofread_results SET status = ? WHERE id = ?', (new_status, result_id))
        conn.commit()
        conn.close()
        
    @staticmethod
    def delete_proofread_result(db_path: str, result_id: str):
        DatabaseService.init_db(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM proofread_results WHERE id = ?', (result_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def add_ignored_rule(db_path: str, rule_type: str, target_word: str):
        import datetime
        DatabaseService.init_db(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        now_str = datetime.datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO proofread_ignored_rules (rule_type, target_word, created_at)
            VALUES (?, ?, ?)
        ''', (rule_type, target_word, now_str))
        conn.commit()
        conn.close()

    @staticmethod
    def load_ignored_rules(db_path: str) -> List[dict]:
        DatabaseService.init_db(db_path)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM proofread_ignored_rules')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
