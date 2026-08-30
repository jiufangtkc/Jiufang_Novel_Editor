import os
import json
import zipfile
import datetime
import shutil
from typing import Optional, Dict, Any


class BackupService:
    """負責專案之 ZIP 打包備份與安全還原服務。"""

    BACKUP_VERSION = "1.0"

    @staticmethod
    def create_backup(
        project_db_path: str,
        backup_zip_path: str,
        project_title: str = "",
        include_global_settings: bool = False
    ) -> str:
        """將 SQLite 專案資料庫與相關資料打包為 .zip 備份檔案。
        
        Args:
            project_db_path: 專案 SQLite .db 檔案絕對路徑
            backup_zip_path: 目標 .zip 或 .jnebackup 儲存路徑
            project_title: 專案作品標題
            include_global_settings: 是否一同備份全域 ai_settings.json
            
        Returns:
            生成的備份檔案路徑
        """
        if not os.path.isfile(project_db_path):
            raise FileNotFoundError(f"找不到專案資料庫檔案：{project_db_path}")

        os.makedirs(os.path.dirname(os.path.abspath(backup_zip_path)), exist_ok=True)
        db_basename = os.path.basename(project_db_path)

        manifest = {
            "version": BackupService.BACKUP_VERSION,
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "project_title": project_title or os.path.splitext(db_basename)[0],
            "original_db_filename": db_basename,
            "has_settings": include_global_settings
        }

        with zipfile.ZipFile(backup_zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            # 寫入資料庫
            zf.write(project_db_path, arcname=f"data/{db_basename}")
            # 寫入清單
            zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            # 選擇性寫入全域設定
            if include_global_settings and os.path.isfile("ai_settings.json"):
                zf.write("ai_settings.json", arcname="config/ai_settings.json")

        return backup_zip_path

    @staticmethod
    def inspect_backup(backup_zip_path: str) -> Dict[str, Any]:
        """檢查備份檔案的元資料。"""
        if not os.path.isfile(backup_zip_path):
            raise FileNotFoundError(f"找不到備份檔案：{backup_zip_path}")

        with zipfile.ZipFile(backup_zip_path, 'r') as zf:
            namelist = zf.namelist()
            if "manifest.json" in namelist:
                raw_manifest = zf.read("manifest.json").decode("utf-8")
                manifest = json.loads(raw_manifest)
            else:
                manifest = {
                    "version": "legacy",
                    "created_at": "未知",
                    "project_title": os.path.splitext(os.path.basename(backup_zip_path))[0],
                    "original_db_filename": "project.db",
                    "has_settings": False
                }

            # 尋找內部的 .db 檔案
            db_entries = [name for name in namelist if name.endswith(".db")]
            manifest["db_entries"] = db_entries
            return manifest

    @staticmethod
    def restore_backup(
        backup_zip_path: str,
        target_dir: str,
        custom_db_name: Optional[str] = None
    ) -> str:
        """從備份 ZIP 中還原專案 SQLite .db 檔案。
        
        Args:
            backup_zip_path: 備份 ZIP 檔案路徑
            target_dir: 還原儲存目錄（如 story/）
            custom_db_name: 自訂還原後的 db 檔名（可選）
            
        Returns:
            還原後的 SQLite .db 絕對路徑
        """
        if not os.path.isfile(backup_zip_path):
            raise FileNotFoundError(f"找不到備份檔案：{backup_zip_path}")

        os.makedirs(target_dir, exist_ok=True)
        manifest = BackupService.inspect_backup(backup_zip_path)

        with zipfile.ZipFile(backup_zip_path, 'r') as zf:
            db_entries = manifest.get("db_entries", [])
            if not db_entries:
                raise ValueError("備份檔案中未包含有效的 SQLite 資料庫 (.db)")

            src_db_arcname = db_entries[0]
            if custom_db_name:
                out_filename = custom_db_name if custom_db_name.endswith(".db") else f"{custom_db_name}.db"
            else:
                out_filename = manifest.get("original_db_filename") or os.path.basename(src_db_arcname)

            out_path = os.path.join(target_dir, out_filename)

            # 若檔案已存在且未指定自訂檔名，為避免意外覆蓋，加上還原時間戳記
            if os.path.exists(out_path) and not custom_db_name:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                base, ext = os.path.splitext(out_filename)
                out_filename = f"{base}_restored_{timestamp}{ext}"
                out_path = os.path.join(target_dir, out_filename)

            # 抽取 db 檔案
            with zf.open(src_db_arcname) as source, open(out_path, "wb") as target:
                shutil.copyfileobj(source, target)

        return os.path.abspath(out_path)
