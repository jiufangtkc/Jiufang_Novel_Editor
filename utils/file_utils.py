import os
import re
import datetime
from typing import Tuple


def get_temp_db_sort_key(file_path: str) -> Tuple[float, float]:
    """
    依據檔名中的時間戳 (YYYYMMDD_HHMMSS) 或檔案修改時間產生排序 key。
    回傳 (timestamp, mtime) 以利進行時間序排序。
    """
    fname = os.path.basename(file_path)
    m = re.search(r'(\d{8}_\d{6})', fname)
    if m:
        try:
            ts = datetime.datetime.strptime(m.group(1), "%Y%m%d_%H%M%S").timestamp()
            mtime = os.path.getmtime(file_path) if os.path.exists(file_path) else ts
            return (ts, mtime)
        except Exception:
            pass
    mtime = os.path.getmtime(file_path) if os.path.exists(file_path) else 0.0
    return (mtime, mtime)
