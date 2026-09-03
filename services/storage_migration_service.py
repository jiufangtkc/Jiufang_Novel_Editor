import os
import shutil
import tempfile
from typing import Dict, Any, List, Tuple
from services.app_settings_service import AppSettingsService


class StorageMigrationService:
    """負責管理專案存檔路徑的目錄初始化、權限校驗與歷史稿件/暫存檔遷移。"""

    @classmethod
    def ensure_storage_directories(cls, storage_path: str) -> Tuple[str, str, str]:
        """在指定儲存路徑下建立 Story、Temp_doc 與 Export 資料夾。
        
        回傳 (story_dir, temp_dir, export_dir) 路徑元組。
        """
        if not os.path.exists(storage_path):
            os.makedirs(storage_path, exist_ok=True)

        story_dir = os.path.join(storage_path, "Story")
        temp_dir = os.path.join(storage_path, "Temp_doc")
        export_dir = os.path.join(storage_path, "Export")

        os.makedirs(story_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)
        os.makedirs(export_dir, exist_ok=True)

        return story_dir, temp_dir, export_dir

    @classmethod
    def is_valid_writable_dir(cls, dir_path: str) -> bool:
        """檢查目錄是否有效且具備寫入權限。"""
        if not dir_path or not isinstance(dir_path, str):
            return False
        try:
            os.makedirs(dir_path, exist_ok=True)
            # 建立臨時檔案測試寫入與刪除
            test_file = os.path.join(dir_path, ".jne_write_test.tmp")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("write_test")
            if os.path.exists(test_file):
                os.remove(test_file)
            return True
        except Exception:
            return False

    @classmethod
    def migrate_storage_data(cls, old_storage_path: str, new_storage_path: str) -> Dict[str, Any]:
        """將舊存檔路徑下的 Story、Temp_doc 與 Export 檔案安全遷移（複製）至新存檔路徑。
        
        回傳包含遷移統計與錯誤清單的 dict。
        """
        result = {
            "story_files_copied": 0,
            "temp_files_copied": 0,
            "export_files_copied": 0,
            "errors": []
        }

        if not old_storage_path or not new_storage_path:
            return result

        old_abs = os.path.abspath(old_storage_path)
        new_abs = os.path.abspath(new_storage_path)

        if old_abs.lower() == new_abs.lower():
            # 相同路徑無須遷移
            return result

        # 確保新目錄存在
        new_story_dir, new_temp_dir, new_export_dir = cls.ensure_storage_directories(new_abs)

        # 1. 遷移 Story 目錄（檢查 Story 與小寫 story）
        old_story_candidates = [
            os.path.join(old_abs, "Story"),
            os.path.join(old_abs, "story")
        ]
        for old_story in old_story_candidates:
            if os.path.exists(old_story) and os.path.isdir(old_story):
                count, errs = cls._copy_directory_tree(old_story, new_story_dir)
                result["story_files_copied"] += count
                result["errors"].extend(errs)

        # 2. 遷移 Temp_doc 目錄
        old_temp = os.path.join(old_abs, "Temp_doc")
        if os.path.exists(old_temp) and os.path.isdir(old_temp):
            count, errs = cls._copy_directory_tree(old_temp, new_temp_dir)
            result["temp_files_copied"] += count
            result["errors"].extend(errs)

        # 3. 遷移 Export 目錄（檢查 Export 與小寫 export）
        old_export_candidates = [
            os.path.join(old_abs, "Export"),
            os.path.join(old_abs, "export")
        ]
        export_found = False
        for old_export in old_export_candidates:
            if os.path.exists(old_export) and os.path.isdir(old_export):
                export_found = True
                count, errs = cls._copy_directory_tree(old_export, new_export_dir)
                result["export_files_copied"] += count
                result["errors"].extend(errs)

        # 容錯機制：若舊路徑下無 Export 目錄，檢查系統預設 AppData 目錄是否存在 Export
        if not export_found:
            default_storage = AppSettingsService.get_default_storage_path()
            if os.path.abspath(default_storage).lower() != new_abs.lower():
                default_export = os.path.join(default_storage, "Export")
                if os.path.exists(default_export) and os.path.isdir(default_export):
                    count, errs = cls._copy_directory_tree(default_export, new_export_dir)
                    result["export_files_copied"] += count
                    result["errors"].extend(errs)

        return result

    @classmethod
    def _copy_directory_tree(cls, src_root: str, dest_root: str) -> Tuple[int, List[str]]:
        """遞迴複製目錄樹中的所有檔案，若目標已存在則比對更新。"""
        copied_count = 0
        errors = []

        for root, dirs, files in os.walk(src_root):
            rel_path = os.path.relpath(root, src_root)
            target_dir = dest_root if rel_path == "." else os.path.join(dest_root, rel_path)
            try:
                os.makedirs(target_dir, exist_ok=True)
            except Exception as e:
                errors.append(f"建立目錄失敗 {target_dir}: {e}")
                continue

            for file_name in files:
                src_file = os.path.join(root, file_name)
                dest_file = os.path.join(target_dir, file_name)
                try:
                    should_copy = True
                    if os.path.exists(dest_file):
                        # 若目標已存在，比較修改時間
                        src_mtime = os.path.getmtime(src_file)
                        dest_mtime = os.path.getmtime(dest_file)
                        if src_mtime <= dest_mtime and os.path.getsize(src_file) == os.path.getsize(dest_file):
                            should_copy = False

                    if should_copy:
                        shutil.copy2(src_file, dest_file)
                        copied_count += 1
                except Exception as e:
                    errors.append(f"複製檔案失敗 {src_file} -> {dest_file}: {e}")

        return copied_count, errors
