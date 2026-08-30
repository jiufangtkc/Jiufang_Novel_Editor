import json
import os
from typing import Dict, Any, List, Optional
from PyQt6.QtWidgets import QMainWindow, QApplication
from PyQt6.QtGui import QGuiApplication

DEFAULT_WINDOW_SETTINGS = {
    "window_width": 1200,
    "window_height": 800,
    "window_x": None,
    "window_y": None,
    "is_maximized": False,
    # 預設五等分：左 1/5 (240), 中 2/5 (480), 右 2/5 (480)
    "splitter_sizes": [240, 480, 480],
    "last_left_width": 240,
    "last_right_width": 480,
    "scale_factor": 1.0,
    # 暫存與自動存檔設定
    "autosave_interval_minutes": 10,
    "autosave_max_files": 100,
    # 專案路徑與 Session 狀態
    "last_exit_normal": True,
    "session_active": False,
    "last_project_path": "",
    # 字數統計規則設定
    "stat_count_half_alnum_and_sym": False,
    "stat_count_full_space": False,
}

SETTINGS_FILENAME = "app_settings.json"


class AppSettingsService:
    """負責管理全域視窗尺寸、介面佈局比例與 UI 縮放的持久化。"""

    @staticmethod
    def get_settings_file_path(app_dir: Optional[str] = None) -> str:
        if not app_dir:
            local_app_data = os.environ.get('LOCALAPPDATA')
            if not local_app_data:
                local_app_data = os.path.join(os.path.expanduser('~'), 'AppData', 'Local')
            app_dir = os.path.join(local_app_data, 'Jiufang_Novel_Editor')
            
        if not os.path.exists(app_dir):
            os.makedirs(app_dir)
            
        return os.path.join(app_dir, SETTINGS_FILENAME)

    @classmethod
    def load_settings(cls, app_dir: Optional[str] = None) -> Dict[str, Any]:
        """讀取本機偏好設定；若無或異常則回傳預設值。"""
        settings_path = cls.get_settings_file_path(app_dir)
        settings = dict(DEFAULT_WINDOW_SETTINGS)
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    if isinstance(saved, dict):
                        settings.update(saved)
            except Exception:
                pass
        return settings

    @classmethod
    def save_settings(cls, settings: Dict[str, Any], app_dir: Optional[str] = None) -> bool:
        """將偏好設定儲存至本機 json。"""
        settings_path = cls.get_settings_file_path(app_dir)
        try:
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    @classmethod
    def extract_from_window(cls, window: QMainWindow) -> Dict[str, Any]:
        """從 MainWindow 實例提取當前視窗大小、最大化狀態、splitter 與縮放設定。"""
        is_maximized = window.isMaximized()
        
        # 若當前是最大化狀態，geometry 會是全螢幕大小；若有 normalGeometry 可用則優先取之
        if is_maximized:
            norm_geo = window.normalGeometry()
            width = norm_geo.width() if norm_geo.isValid() and norm_geo.width() > 100 else 1200
            height = norm_geo.height() if norm_geo.isValid() and norm_geo.height() > 100 else 800
            x = norm_geo.x() if norm_geo.isValid() else None
            y = norm_geo.y() if norm_geo.isValid() else None
        else:
            geo = window.geometry()
            width = geo.width()
            height = geo.height()
            x = geo.x()
            y = geo.y()

        # Splitter 尺寸
        if getattr(window, "is_focus_mode", False):
            splitter_sizes = list(getattr(window, "_saved_splitter_sizes", [240, 480, 480]))
        else:
            splitter_sizes = window.splitter.sizes()
            # 若全部為 0 則回退預設
            if not splitter_sizes or sum(splitter_sizes) == 0:
                splitter_sizes = [240, 480, 480]

        last_left = getattr(window, "last_left_width", 240)
        last_right = getattr(window, "last_right_width", 480)
        scale_factor = getattr(window, "scale_factor", 1.0)

        return {
            "window_width": width,
            "window_height": height,
            "window_x": x,
            "window_y": y,
            "is_maximized": is_maximized,
            "splitter_sizes": splitter_sizes,
            "last_left_width": last_left,
            "last_right_width": last_right,
            "scale_factor": scale_factor,
        }

    @classmethod
    def apply_to_window(cls, window: QMainWindow, settings: Dict[str, Any]):
        """將設定套用回 MainWindow 實例。"""
        # 1. 視窗大小與位置
        w = settings.get("window_width", 1200)
        h = settings.get("window_height", 800)
        if isinstance(w, int) and isinstance(h, int) and w > 200 and h > 200:
            window.resize(w, h)

        x = settings.get("window_x")
        y = settings.get("window_y")
        if isinstance(x, int) and isinstance(y, int):
            # 檢查坐標是否落在合理螢幕範圍內
            screen = QGuiApplication.primaryScreen()
            if screen:
                screen_geo = screen.availableGeometry()
                if screen_geo.contains(x, y):
                    window.move(x, y)
            else:
                window.move(x, y)

        # 2. Splitter 尺寸與收折記憶
        splitter_sizes = settings.get("splitter_sizes")
        if isinstance(splitter_sizes, list) and len(splitter_sizes) == 3 and sum(splitter_sizes) > 0:
            window.splitter.setSizes(splitter_sizes)
            window._saved_splitter_sizes = list(splitter_sizes)
        else:
            # 預設 1 : 2 : 2
            total_w = window.width() or 1200
            unit = total_w // 5
            default_sizes = [unit, unit * 2, total_w - unit * 3]
            window.splitter.setSizes(default_sizes)
            window._saved_splitter_sizes = list(default_sizes)

        if "last_left_width" in settings and isinstance(settings["last_left_width"], int):
            window.last_left_width = settings["last_left_width"]
        if "last_right_width" in settings and isinstance(settings["last_right_width"], int):
            window.last_right_width = settings["last_right_width"]

        # 3. 最大化狀態
        if settings.get("is_maximized", False):
            window.showMaximized()
