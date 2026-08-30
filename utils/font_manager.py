import os
import sys
import urllib.request
import zipfile
import io
from PyQt6.QtGui import QFontDatabase, QFont
from PyQt6.QtWidgets import QApplication

FONT_URL = "https://github.com/ButTaiwan/iansui/releases/download/v1.020/iansui.zip"
FONT_DIR_NAME = "resources/fonts"
FONT_FILE_NAME = "Iansui-Regular.ttf"

class FontManager:
    _default_font_family = "Iansui"
    _is_initialized = False

    @classmethod
    def get_font_dir(cls) -> str:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        font_dir = os.path.join(base_dir, "resources", "fonts")
        os.makedirs(font_dir, exist_ok=True)
        return font_dir

    @classmethod
    def get_font_path(cls) -> str:
        return os.path.join(cls.get_font_dir(), FONT_FILE_NAME)

    @classmethod
    def ensure_font_downloaded(cls) -> bool:
        font_path = cls.get_font_path()
        if os.path.exists(font_path) and os.path.getsize(font_path) > 10000:
            return True
        try:
            req = urllib.request.Request(FONT_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                zip_data = resp.read()
            with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
                for name in z.namelist():
                    if name.endswith(".ttf") or name.endswith(".otf"):
                        with open(font_path, "wb") as f_out:
                            f_out.write(z.read(name))
                        break
            return os.path.exists(font_path)
        except Exception:
            return False

    @classmethod
    def init_fonts(cls):
        if cls._is_initialized:
            return cls._default_font_family

        # 確保字型存在
        cls.ensure_font_downloaded()
        font_path = cls.get_font_path()

        if os.path.exists(font_path):
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id != -1:
                families = QFontDatabase.applicationFontFamilies(font_id)
                if families:
                    cls._default_font_family = families[0]
            else:
                cls._default_font_family = "Microsoft JhengHei"
        else:
            cls._default_font_family = "Microsoft JhengHei"

        cls._is_initialized = True
        return cls._default_font_family

    @classmethod
    def get_default_font_family(cls) -> str:
        if not cls._is_initialized:
            cls.init_fonts()
        return cls._default_font_family

    @classmethod
    def get_font(cls, family=None, size=10, weight=QFont.Weight.Normal, italic=False, strike_out=False) -> QFont:
        if not family:
            family = cls.get_default_font_family()
        try:
            val_size = int(size)
            if val_size <= 0:
                val_size = 10
        except (ValueError, TypeError):
            val_size = 10
        font = QFont(family, val_size, weight)
        if italic:
            font.setItalic(True)
        if strike_out:
            font.setStrikeOut(True)
        return font

    @classmethod
    def setup_application_font(cls, app: QApplication):
        family = cls.init_fonts()
        app_font = QFont(family, 10)
        app.setFont(app_font)
