# =============================================================================
# ⚠️ 警告 (WARNING):
# StorageService 僅供讀取極早期舊版 JSON 專案格式並自動遷移至 SQLite 專案庫使用。
# 專案已全面切換至 SQLite (.db)，嚴禁在此新增寫入邏輯或作為新功能儲存層！
# =============================================================================

import json
import os
import uuid
import warnings
from typing import Dict, Any, List, Tuple
from models.models import JneProject, ProjectInfo, ChapterNode, CardNode, WritingLogEntry

class StorageService:
    @staticmethod
    def _dict_to_card_node(data: Dict[str, Any]) -> CardNode:
        node = CardNode(
            title=data.get("title", ""),
            id=data.get("id", str(uuid.uuid4())),
            content=data.get("content", ""),
            color=data.get("color", "#3C3F41"),
            is_collapsed=data.get("is_collapsed", False)
        )
        for child_data in data.get("children", []):
            node.children.append(StorageService._dict_to_card_node(child_data))
        return node

    @staticmethod
    def _dict_to_chapter_node(data: Dict[str, Any]) -> Tuple[ChapterNode, Dict[str, List[CardNode]]]:
        node = ChapterNode(
            name=data.get("name", ""),
            node_type=data.get("type", "file"),
            id=data.get("id", str(uuid.uuid4())),
            content=data.get("content", ""),
            mark=data.get("mark", "Draft")
        )
        
        extracted_cards = {"summary": [], "character": [], "world": [], "timeline": []}
        
        # Load legacy cards if present
        cards_data = data.get("cards", {})
        for cat in ["summary", "character", "world", "timeline"]:
            if cat in cards_data:
                extracted_cards[cat].extend([StorageService._dict_to_card_node(c) for c in cards_data[cat]])
                
        for child_data in data.get("children", []):
            child_node, child_cards = StorageService._dict_to_chapter_node(child_data)
            node.children.append(child_node)
            # Merge child cards
            for cat in extracted_cards:
                extracted_cards[cat].extend(child_cards[cat])
            
        return node, extracted_cards

    @staticmethod
    def load_project_from_json(file_path: str) -> JneProject:
        """從舊版 JSON 檔案載入專案資料（向後相容專用）。"""
        warnings.warn(
            "StorageService 僅供舊版相容，勿用於新功能",
            category=DeprecationWarning,
            stacklevel=2
        )

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Project file not found: {file_path}")
            
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        project = JneProject()
        
        # Load Project Info
        p_info = data.get("project", {})
        global_font_family = data.get("global_font_family") or p_info.get("global_font_family", "Iansui")
        global_font_size = data.get("global_font_size") or p_info.get("global_font_size", 12)
        editor_font_family = data.get("editor_font_family") or p_info.get("editor_font_family", "Iansui")
        editor_font_size = data.get("editor_font_size") or p_info.get("editor_font_size", 12)

        project.project_info = ProjectInfo(
            title=p_info.get("title", "未命名專案"),
            logline=p_info.get("logline", ""),
            global_font_family=global_font_family,
            global_font_size=int(global_font_size),
            editor_font_family=editor_font_family,
            editor_font_size=int(editor_font_size)
        )
        
        # Check if project-level cards exist (new format)
        if "cards" in p_info:
            for cat in project.project_cards:
                if cat in p_info["cards"]:
                    project.project_cards[cat] = [StorageService._dict_to_card_node(c) for c in p_info["cards"][cat]]
        
        # Load Tree
        for node_data in data.get("tree", []):
            node, legacy_cards = StorageService._dict_to_chapter_node(node_data)
            project.tree.append(node)
            # Merge legacy cards if any
            for cat in project.project_cards:
                project.project_cards[cat].extend(legacy_cards[cat])
            
        # Load Theme
        project.current_theme = data.get("current_theme", "dark")
        
        # Load Logs
        for log_data in data.get("writing_logs", []):
            project.writing_logs.append(WritingLogEntry(
                date=log_data.get("date", ""),
                duration=log_data.get("duration", 0),
                word_count=log_data.get("word_count", 0),
                ai_continuation_count=log_data.get("ai_continuation_count", 0),
                ai_continuation_chars=log_data.get("ai_continuation_chars", 0),
                ai_chat_count=log_data.get("ai_chat_count", 0),
                ai_details=log_data.get("ai_details", {}),
                paste_large_count=log_data.get("paste_large_count", 0),
                delete_large_count=log_data.get("delete_large_count", 0)
            ))
            
        return project
