import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from utils.font_manager import FontManager
from views.main_window import MainWindow
from controllers.main_controller import MainController
import ctypes

import os

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def main():
    # 確保 Windows 工作列正確顯示 Icon
    myappid = 'jiufang.novel.editor.1.0' # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    
    app = QApplication(sys.argv)
    
    # 使用絕對路徑載入 Icon
    icon_path = resource_path("resources/icons/app_icon.ico")
    app.setWindowIcon(QIcon(icon_path))
    
    # 全局字型初始化為芫荽字體 (Iansui)
    FontManager.setup_application_font(app)
    
    # 建立 View
    view = MainWindow()
    
    # 建立 Controller，並將 View 傳入（啟用使用者啟動選擇流程）
    controller = MainController(view, interactive_startup=True)
    
    # 若使用者在啟動對話框中取消或關閉，直接乾淨結束
    if getattr(controller, "should_exit", False):
        sys.exit(0)

    # 顯示主視窗
    view.show()
    
    # 執行程式
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

