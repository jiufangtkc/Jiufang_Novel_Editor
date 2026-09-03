from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import QMainWindow

class MenuBuilder:
    """負責建立與配置主視窗選單列 (MenuBar) 的構建器。"""

    @staticmethod
    def build_menus(window: QMainWindow):
        """為指定的主視窗建立所有選單、子選單與 QAction，並掛載回主視窗屬性。"""
        menubar = window.menuBar()

        # 1. 檔案選單
        window.file_menu = menubar.addMenu("檔案(&F)")
        window.action_new_book = QAction("開啟新書(&N)", window)
        window.action_new_book.setShortcut("Ctrl+N")
        window.action_save_project = QAction("儲存稿件(&S)", window)
        window.action_save_project.setShortcut("Ctrl+S")
        window.action_save_project_as = QAction("另存新檔(&A)...", window)
        window.action_save_project_as.setShortcut("Ctrl+Alt+S")
        window.action_export = QAction("匯出(&E)...", window)
        window.action_export.setShortcut("Ctrl+E")
        window.action_load_latest_project = QAction("讀取上次寫的專案(&L)", window)
        window.action_load_project = QAction("讀取稿件(&O)...", window)
        window.action_load_project.setShortcut("Ctrl+O")
        window.action_load_temp_project = QAction("讀取暫存檔(&T)...", window)
        window.action_snapshot_manager = QAction("版本快照管理(&M)...", window)
        window.action_snapshot_manager.setShortcut("Ctrl+Shift+S")
        window.action_export_backup = QAction("匯出專案備份 (ZIP)(&B)...", window)
        window.action_export_backup.setShortcut("Ctrl+Shift+B")
        window.action_restore_backup = QAction("從備份還原專案(&R)...", window)
        window.action_restore_backup.setShortcut("Ctrl+Shift+R")
        window.action_exit = QAction("退出九方編輯器(&X)", window)
        window.action_exit.setShortcut("Ctrl+Q")

        window.file_menu.addAction(window.action_new_book)
        window.file_menu.addAction(window.action_save_project)
        window.file_menu.addAction(window.action_save_project_as)
        window.file_menu.addAction(window.action_export)
        window.file_menu.addSeparator()
        window.file_menu.addAction(window.action_load_latest_project)
        window.file_menu.addAction(window.action_load_project)
        window.file_menu.addAction(window.action_load_temp_project)
        window.file_menu.addSeparator()
        window.file_menu.addAction(window.action_snapshot_manager)
        window.file_menu.addAction(window.action_export_backup)
        window.file_menu.addAction(window.action_restore_backup)
        window.file_menu.addSeparator()
        window.file_menu.addAction(window.action_exit)

        # 2. 編輯選單
        window.edit_menu = menubar.addMenu("編輯(&E)")
        window.action_find = QAction("尋找(&F)...", window)
        window.action_find.setShortcut("Ctrl+F")
        window.action_replace = QAction("取代(&R)...", window)
        window.action_replace.setShortcut("Ctrl+H")
        window.action_global_search = QAction("跨章節全文搜尋(&S)...", window)
        window.action_global_search.setShortcut("Ctrl+Shift+F")

        window.edit_menu.addAction(window.action_find)
        window.edit_menu.addAction(window.action_replace)
        window.edit_menu.addSeparator()
        window.edit_menu.addAction(window.action_global_search)

        # 3. 檢視選單
        window.view_menu = menubar.addMenu("檢視(&V)")
        window.action_show_write = QAction("寫作編輯模式(&W)", window)
        window.action_show_write.setShortcut("Ctrl+Shift+W")
        window.action_show_outline = QAction("大綱總覽模式(&O)", window)
        window.action_show_outline.setShortcut("Ctrl+Shift+O")
        window.action_toggle_focus = QAction("沉浸專注模式(&F)", window)
        window.action_toggle_focus.setShortcut("F11")

        window.view_menu.addAction(window.action_show_write)
        window.view_menu.addAction(window.action_show_outline)
        window.view_menu.addSeparator()
        window.view_menu.addAction(window.action_toggle_focus)

        # 4. 全文格式選單
        window.format_menu = menubar.addMenu("全文格式(&O)")
        window.action_adjust_global_font = QAction("調整全文字型(&F)...", window)
        window.action_adjust_global_font.setShortcut("Ctrl+Shift+T")
        window.action_adjust_global_size = QAction("調整全文字級(&S)...", window)
        window.action_adjust_global_size.setShortcut("Ctrl+Shift+P")
        window.format_menu.addAction(window.action_adjust_global_font)
        window.format_menu.addAction(window.action_adjust_global_size)

        # 創作日誌（獨立 Action 直接掛在 menubar 上）
        window.action_show_writing_log = QAction("創作日誌(&D)", window)
        window.action_show_writing_log.setShortcut("Ctrl+Shift+D")
        menubar.addAction(window.action_show_writing_log)

        # 5. 工具選單
        window.tools_menu = menubar.addMenu("工具(&T)")
        window.action_lint = QAction("文風與贅詞檢查(&L)...", window)
        window.action_lint.setShortcut("Ctrl+Shift+L")
        window.tools_menu.addAction(window.action_lint)

        # 6. AI 助手選單
        window.ai_menu = menubar.addMenu("✨ AI 助手(&A)")
        window.action_ai_chat = QAction("💬 AI 對話助手(&C)", window)
        window.action_ai_chat.setShortcut(QKeySequence("Ctrl+Shift+A"))
        window.action_ai_continuation = QAction("✍️ AI 智慧擴寫(&K)", window)
        window.action_ai_continuation.setShortcut("Ctrl+K")
        
        window.action_ai_impression = QAction("📝 文學評語與寫作建議(&R)...", window)
        window.action_ai_character = QAction("👤 登場角色提取(&P)...", window)
        window.action_ai_world = QAction("🌍 世界觀設定提取(&W)...", window)
        window.action_ai_timeline = QAction("⏱️ 時間線與事件梳理(&T)...", window)
        window.action_ai_proofread = QAction("🔎 AI 校稿(&P)...", window)
        window.action_ai_settings = QAction("⚙️ AI 助手設定(&S)...", window)

        window.ai_menu.addAction(window.action_ai_chat)
        window.ai_menu.addAction(window.action_ai_continuation)
        window.ai_menu.addSeparator()
        window.ai_menu.addAction(window.action_ai_impression)
        window.ai_menu.addAction(window.action_ai_character)
        window.ai_menu.addAction(window.action_ai_world)
        window.ai_menu.addAction(window.action_ai_timeline)
        window.ai_menu.addAction(window.action_ai_proofread)
        window.ai_menu.addSeparator()
        window.ai_menu.addAction(window.action_ai_settings)

        # 7. 設定選單
        window.settings_menu = menubar.addMenu("設定(&S)")
        window.action_autosave_settings = QAction("暫存與自動存檔設定(&A)...", window)
        window.action_storage_path_settings = QAction("存檔路徑設定(&P)...", window)
        window.action_word_count_settings = QAction("字數統計設定(&W)...", window)
        window.settings_menu.addAction(window.action_autosave_settings)
        window.settings_menu.addAction(window.action_storage_path_settings)
        window.settings_menu.addAction(window.action_word_count_settings)
        window.settings_menu.addSeparator()
        
        window.theme_menu = window.settings_menu.addMenu("主題切換(&T)")
        window.action_theme_default = QAction("預設深色(&1)", window)
        window.action_theme_green = QAction("綠影風格(&2)", window)
        window.action_theme_celadon = QAction("青瓷風格(&3)", window)
        window.action_theme_sepia = QAction("暮茶風格(&4)", window)
        window.action_theme_polar = QAction("極地夜空(&5)", window)
        window.action_theme_forest = QAction("暗影森林(&6)", window)
        for act in [window.action_theme_default, window.action_theme_green, window.action_theme_celadon,
                   window.action_theme_sepia, window.action_theme_polar, window.action_theme_forest]:
            window.theme_menu.addAction(act)

        window.scale_menu = window.settings_menu.addMenu("介面大小調整(&Z)")
        window.scale_actions = {}
        scales = [
            ("&1 100% (預設)", 1.0), ("&2 125%", 1.25), ("&3 150%", 1.5),
            ("&4 180%", 1.8), ("&5 200%", 2.0)
        ]
        for label, val in scales:
            act = QAction(label, window)
            window.scale_menu.addAction(act)
            window.scale_actions[val] = act
