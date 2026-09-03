# 九方小說編輯器 — 交接文件

> 最後更新：2026-09-03，實作「快速存檔安靜存檔」與「依書名單一存檔覆寫規則」（Ctrl+S 不彈窗，檔名不再帶時間戳，除非另存新檔否則維持原檔名覆寫），全套 171 項單元測試維持 100% 通過。

## 0. ⚠️ 專案交接守則 (CRITICAL RULES)

1. **嚴格的範圍控制**：每次修改聚焦於指派任務檔案，不要發散，不要隨意大範圍破壞架構。
2. **每次結束必寫交接記錄**：當完成任務，**必須**修改本 HANDOVER.md 的「第 4 節 (目前執行狀態)」，清楚寫下變更內容與下一個 Agent 的指引。
3. **MVC 架構原則**：`views/` 保持純 UI、`controllers/` 處理業務邏輯、`services/` 專司資料存取。
4. **遇錯即停**：如果測試未通過，請立即排查修復後再進入下一步。
5. **打包檔案收納禁令**：所有建置與打包相關腳本（`build.bat`、`Jiufang_Novel_Editor.spec`、`setup.iss`）**一律存放在 .agents/build/**，**嚴禁複製或放置於專案根目錄**。

---

## 1. 你接手的是什麼

這是一個基於 Python + PyQt6 的桌面端小說寫作軟體，目前 Phase 1 到 Phase 20 已經全部開發完畢且完成全方位最佳化與防護：
- **核心寫作與結構**：樹狀目錄、巢狀卡片系統、純文字無格式編輯、沉浸模式、大綱總覽模式、場景/幕管理。
- **右側資料集面板**：上下兩欄垂直分欄顯示（上方為卡片分類與導航樹，下方為卡片內容即時檢視與編輯區，以及幕資訊屬性面板）。
- **右鍵選單增強**：作品面板與資料集面板支援重新命名、建立副本（深拷貝所有子項）、複製內文到剪貼簿、同層排序上移/下移、展開/收合狀態記憶與還原。
- **儲存與備份**：純 SQLite 儲存（含 `database_migrations.py` 版本化 Migration Pipeline）、自動暫存排程與崩潰還原 (`AutosaveController`)、版本快照管理 (`SnapshotController`)、ZIP 備份/還原 (`BackupController`)、垃圾桶管理。
- **雲端同步與存檔路徑自訂**：支援自訂存檔路徑（如 Dropbox、OneDrive 或自訂目錄）、自動建立 `Story` 與 `Temp_doc` 資料夾、變更路徑時自動安全遷移歷史稿件與暫存檔。
- **寫作輔助與檢查**：尋找與取代、全文檢索、多格式匯出 (docx/txt/md/epub)。
- **AI 整合與長文滾動壓縮（HRCI）**：
  - 支援多輪對話、智慧續寫（含防護開關）、本機模型偵測 (Ollama/LM Studio)。
  - **長文分析演算法（HRCI）**：為 9B 以下本地小模型設計「語義安全分塊 + 滾動狀態壓縮（雙軌索引） + 全局最終整合」機制，突破 Context Window 限制並防止細節丟失。
  - **AI 角色提取**：支援從小說文本自動提取角色特徵、關係網，並匯入卡片系統。
- **數據追蹤**：寫作儀表板（趨勢折線圖、熱力圖、各章長條圖、AI 介入度環形圖）、AI 介入度記錄 (手寫 vs AI)。
- **文風檢查**：繁中贅詞偵測（公文冗贅、被動弱句、高頻虛詞、相鄰重複詞）、白名單與自訂詞庫。
- **UI 偏好與縮放管理**：初次乾淨啟動介面縮放詢問引導 (InitialScaleDialog)、全域偏好持久化 (AppSettingsService)、自訂介面欄位佈局儲存。

---

## 2. 重構與開發歷史

```
原始狀態 --- main.py 3000+ 行的 God Object
    |
    ├── Phase 1 ~ 12：基礎架構與核心功能 (AI、匯出、儲存、儀表板等)
    |
    ▼── 功能開發完畢，進入最佳化階段 ──
    |
    ├── Phase 13：技術債與冗餘代碼清理（✅ 全部完成）
    ├── Phase 14：專案深度檢視與架構防護最佳化（✅ 全部完成）
    ├── Phase 15：Agent 友善化與 Controller 拆分（✅ 全部完成）
    ├── Phase 16：全面審計與系統擴充（✅ 全部完成）
    |   ├── 16.1 ~ 16.5 修復 Bug 與 Plan 02 審計
    |   ├── 16.6 UI 縮放記憶與引導
    |   └── 16.8 AI 助手長文分析演算法（HRCI）實作與整合
    ├── Phase 17：近期功能強化與 UI 更新（✅ 全部完成）
    |   ├── 17.1 AI 角色提取功能 (AIScopeDialog, AICharacterReviewDialog)
    |   ├── 17.2 自訂介面欄位佈局與儲存
    |   ├── 17.3 樹狀面板展開狀態存檔同步
    |   └── 17.4 軟體圖示全域更新與測試修正 (114/114 通過)
    ├── Phase 18：存檔路徑自訂與雲端同步遷移機制（✅ 全部完成）
    |   ├── 18.1 AppSettingsService 擴充 storage_path 支援
    |   ├── 18.2 StorageMigrationService 目錄初始化與檔案安全遷移
    |   ├── 18.3 StoragePathDialog 存檔路徑設定視窗與選單整合
    |   └── 18.4 稿件存檔/暫存/讀檔/備份路徑全面相容 (120/120 通過)
    ├── Phase 19：右側資料集面板上下分欄重構（✅ 全部完成）
    |   ├── 19.1 移除底部多餘之「新增卡片/分類下拉選單」控制列
    |   ├── 19.2 右側面板改為 QSplitter 上下兩欄佈局（上：樹狀導航；下：卡片內容/幕資訊區）
    |   ├── 19.3 點擊卡片節點直接於下方欄位即時檢視與編輯標題與內文
    |   └── 19.4 完善空白處右鍵新增卡片子選單與測試套件 (新增 test_right_panel_split.py)
    └── Phase 20：系統重構、模組化與狀態防護加固（✅ 全部完成）
        ├── 20.1 DatabaseService 瘦身：建立 services/database_migrations.py 獨立管理 Schema 升級
        ├── 20.2 ProjectController 模組化：抽離 controllers/autosave_controller.py 獨立管理暫存、計時器與崩潰還原
        ├── 20.3 UI 狀態防護加固：卡片改名時即時連動同步下方編輯欄位標題，防範資料覆寫
        └── 20.4 測試套件擴充：新增連動同步測試，127/127 項測試全數通過
    └── Phase 21：資料集卡片 Markdown 富文本渲染與格式化工具支援（✅ 全部完成）
        ├── 21.1 編輯器升級：RightPanelCardEditor 整合 MarkdownHighlighter 即時語法高亮
        ├── 21.2 快捷格式化工具列：提供粗體 (B/Ctrl+B)、斜體 (I/Ctrl+I)、標題 (H)、清單 (•)、刪除線 (~S~)、省略號 (……)、破折號 (──) 等快速按鈕
        ├── 21.3 Markdown 富文本渲染預覽：新增「📖 預覽 / 📝 編輯」模式切換與 HTML 渲染 (markdown_to_html)
        └── 21.4 測試套件擴充：新增高亮、預覽切換與格式化工具列單元測試，129/129 項測試全數通過
    └── Phase 22：小說編輯器 Markdown 底層轉換中介與極簡所見即所得支援（✅ 全部完成）
        ├── 22.1 Markdown 轉換中介核心：建立 utils/markdown_converter.py，支援結構化 Token 解析、純文字小說排版清洗 (全形縮排)、Docx Runs 生成、ePub 語意化 HTML 轉換
        ├── 22.2 編輯區極簡所見即所得體驗：JNE_TextEdit 支援 Ctrl+B (粗體)、Ctrl+I (斜體)、Ctrl+Shift+S (刪除線)、Ctrl+Shift+H (場景分隔線) 快捷操作與右鍵格式選單
        ├── 22.3 視覺減噪渲染：MarkdownHighlighter 導入 fmt_muted 淡化語法標記符號，顯著加強粗體、斜體等正文樣式
        ├── 22.4 多格式匯出升級：ExportController 全面整合 MarkdownConverter，匯出 Word/ePub/TXT 自動轉為出版級排版與乾淨純文字
        └── 22.5 單元測試擴充：新增 test_markdown_converter.py 並更新 test_export.py，134/134 項測試全數通過
    └── Phase 26：當日目標與進度多設備（Dropbox 同步）持久化與日誌連動（✅ 全部完成）
        ├── 26.1 模型擴充：ProjectInfo 新增 daily_target_word_count 欄位（預設 1000 字）
        ├── 26.2 SQLite 遷移升級：DatabaseMigrations 實現 v9 -> v10 升級，為 project_info 表補齊目標欄位
        ├── 26.3 跨設備開檔狀態還原：load_project_data 自動還原目標字數，並依今日日期 (YYYY-MM-DD) 從 writing_logs 還原已寫字數
        ├── 26.4 雙向即時同步與清除：set_daily_target、flush_active_writing_session、clear_daily_progress 與專案日誌及暫存即時連動
        └── 26.5 測試套件擴充：新增 test_daily_progress_sync.py（7 項測試），全套 143/143 項單元測試 100% 通過
```

---

## 3. 需要特別注意的陷阱與設計規則

### 陷阱 1：儲存架構已完全廢棄 JSON 格式
- 專案存檔、另存新檔、Temp_doc/ 自動暫存檔全面採用 SQLite (.db)。
- services/storage.py 僅供向後相容舊檔遷移使用，寫入方法已徹底封死。

### 陷阱 2：AI 請求必須在非同步執行緒
- 絕對不要在 Qt 主執行緒同步呼叫 API，避免介面卡頓。在單元測試中若測試 UI 流程，應 mock worker.start。

### 陷阱 3：API Key 與專案檔案隔離
- ai_settings.json 與 lint_settings.json 為本機全域設定，不會寫入 SQLite 專案資料庫中。

### 陷阱 4：子控制器之間不得互相 import
- 所有子控制器在 __init__ 接收 main_controller 實例（self.mc），跨控制器操作一律透過 self.mc.xxx 存取，嚴禁子控制器互相 import，防止 Circular Import。

### 陷阱 5：JneProject 資料模型層級
- 專案字型、書名、大綱設定皆統一放置於 project.project_info (ProjectInfo dataclass) 中，請勿在 JneProject 頂層新增冗餘 getter/setter 或屬性。

### 陷阱 6：QSS Template 字串格式化大括號轉義
- theme_manager.py 的 BASE_THEME_TEMPLATE 會使用 format(**colors)，CSS 選擇器內的普通大括號必須寫為雙大括號 {{ 與 }}，僅有要被代換的變數（如 {status_bar_bg}）保留單大括號。

### 陷阱 7：章節標記色碼統一常數
- 章節與幕的進度標記色碼（Draft, 1st Edit, 2nd Edit, Final, Discarded）一律統一引用 models.models.MARK_COLOR_MAP，禁止在 Controller 或 View 中自行硬編碼字典。

### 陷阱 8：開啟新專案不可重設 UI 縮放比例
- 開啟新專案（_reset_project_state）僅重設當前專案資料與樹狀結構，不得修改全域介面縮放 scale_factor。

### 陷阱 9：存檔與暫存路徑請統一透過 MainController 取得
- 請統一呼叫 `self.mc.get_story_dir()` 與 `self.mc.get_temp_dir()` 取得路徑，不可硬編碼 `os.path.join(self.mc.app_dir, "story")`，以確保使用者自訂雲端同步路徑時能正確運作。

### 陷阱 10：小說文字儲存與匯出轉換
- 編輯器底層以純文字 Markdown 儲存，匯出時必須透過 `MarkdownConverter` 進行轉檔，確保輸出之 Word 文件（.docx）帶有真實樣式 Run、電子書（.epub）具有語意化 HTML 標籤、純文字（.txt）已清洗語法符號。

### 陷阱 11：不要在 apply_theme 中直接呼叫 QApplication.setStyleSheet()
- 在 PyQt6 / Windows 上，若對全域 `QApplication.instance()` 呼叫 `setStyleSheet`，會導致部分已手動指定字型的 widget（如 `QComboBox`）觸發全域字型 reset（變回 9pt）。
- 正確做法為在各對話框初始化時使用 `ThemeManager.apply_theme_to_dialog(self, parent)`，既保證完整繼承主題色彩與縮放，又不會污染或重設主視窗的字型。

### 陷阱 12：Windows 剪貼簿單元測試請 Mock，避免 OLE 重試與衝突
- 在單元測試中若需測試複製到剪貼簿功能（如 `copy_card_content`），應使用 `unittest.mock.patch.object(QApplication.clipboard(), "setText")` 驗證傳入參數，嚴禁直接依賴系統全域剪貼簿。在 Windows 平台無頭或背景測試環境中，`OpenClipboard` 易與其他程式（或 COM 歷程記錄）衝突觸發 `0x800401d0`，導致 Qt 不斷 retry 造成數秒卡頓並拋出 `AssertionError`。

### 陷阱 13：外部與本機網路端點測試必須 Mock
- 在測試 `AIService.detect_local_models` 時，不得直接發送真實 HTTP request 到未開放的本機端點（如 `99999` port），否則在 Windows 系統連線 socket 超時會導致測試每次延遲 2 秒以上，應使用 `unittest.mock.patch("urllib.request.urlopen")` 模擬異常以保持測試純淨與毫秒級快速執行。

### 陷阱 14：Antigravity Agent 執行測試與背景工作機制
- 專案全套測試數量達 154 項，完整執行需耗時約 17 秒。在 Antigravity 環境中，若使用 `run_command`，一旦執行時間超過 `WaitMsBeforeAsync` 上限（10 秒），指令會自動轉入背景執行緒 (`Background Task`)。此時 Agent 必須使用 `manage_task` 追蹤狀態直至 `DONE` 並讀取日誌回報結果，切勿誤判為測試死鎖或在背景未完成時提前結束回覆。

### 陷阱 15：Windows 虛擬環境搬移與 PyInstaller Launcher 陷阱
- 在 Windows 上，若專案或 `.venv` 資料夾從其他磁碟機（例如 C 槽搬移至 D 槽）或使用者目錄搬家，`.venv\Scripts\*.exe`（如 `pyinstaller.exe`）為二進位 wrapper，內部寫死了原建立時的絕對路徑，直接執行會拋出 `Fatal error in launcher: Unable to create process using ...`。
- **解法**：呼叫工具時請一律使用 `.venv\Scripts\python.exe -m PyInstaller`（以 Python 直譯器直接掛載模組），並確認 `.venv\pyvenv.cfg` 中的 `home` 與 `executable` 指向系統實際存在的 Python 安裝目錄。此外，打包後若在專案根目錄產生臨時的 `Jiufang_Novel_Editor.spec`，應立即清除以維持根目錄整潔規範。

---


## 4. 目前執行狀態與下一步指引 (CURRENT STATUS & NEXT STEPS)

- **本次完成事項 (實作快速存檔安靜存檔與依書名單一存檔覆寫規則，全套 171 項單元測試 100% 綠燈)**：
  1. **快速存檔安靜存檔 (Quiet / Silent Save)**：
     - `controllers/project_controller.py`：`save_project(self, silent: bool = True)` 預設改為安靜存檔，不彈出 `QMessageBox.information` 對話框打斷寫作。
     - 狀態列反饋：儲存成功時於狀態列顯示 `稿件已儲存至 {檔名}` 3 秒，既溫和安靜又具備明確安全感；若儲存失敗依然保留 `QMessageBox.critical` 錯誤通知。
     - `controllers/main_controller.py`：選單與快捷鍵 Ctrl+S 動作綁定 `action_save_project.triggered.connect(lambda: self.project.save_project(silent=True))`，解決 Qt triggered 訊號傳入 checked=False 的潛在覆蓋問題。
  2. **存檔規則與檔名管理改進（單一存檔不膨脹）**：
     - 存檔不再加上日期與時間（移除 `now_str = datetime.datetime.now().strftime(...)` 產生新檔的行為）。
     - 若已有開啟或已存檔路徑（`self.current_project_path`），一般存檔時直接覆寫該路徑（本來的檔案名稱），不再重複產生大量歷史檔案。
     - 新專案首次存檔時依照書名命名（如 `Story/{書名}/{書名}.db`）；若後續在編輯器修改書名，除非使用者主動執行「另存新檔」，否則依然維持本來的檔案名稱進行覆寫。
     - 「另存新檔」（`save_project_as`）提供書名作為預設檔名建議，另存成功後更新 `current_project_path`，後續存檔便持續使用另存後的新檔名。
     - `_reset_project_state` 新增重設 `self.current_project_path = ""`，防範開新專案時誤用前一專案路徑。
  3. **測試套件擴充與文檔維護**：
     - 新增 `tests/test_save_rules.py`（6 項測試），完整覆蓋安靜存檔無對話框、狀態列提示、檔名不含時間戳、連續存檔覆寫原檔、改書名仍沿用原檔名、另存新檔後更新路徑與 Ctrl+S 觸發等行為。
     - 全套 171 項測試 100% 通過（`pytest tests/` 171 passed in 16.64s）。
     - 同步更新 `.agents/docs/TEST_SUITE.md` 與本交接文件。

- **前次完成事項 (發布 v0.1.1-beta 測試預發布版與稿件未存檔關閉防護機制，全套 165 項單元測試 100% 綠燈)**：
  1. **未儲存狀態機制與標題星號連動**：
     - `controllers/main_controller.py`：新增 `self.is_dirty` 狀態屬性與 `mark_dirty(dirty: bool)` 方法。
     - `controllers/project_controller.py`：`update_project_labels` 於未存檔時在視窗標題自動標註 `*`（例如 `*{書名} - 九方小說編輯器`），已存檔時移除星號。
  2. **全面變更事件與存檔清空覆蓋**：
     - `EditorController.on_editor_text_changed` 編輯器打字/修改內文時觸發 `mark_dirty(True)`。
     - `ProjectController.edit_project_title` / `edit_logline` 變更書名與大綱時觸發 `mark_dirty(True)`。
     - `ProjectController.save_temp_doc` 擴充 `from_timer: bool = False` 參數，非計時器之目錄樹、卡片等所有實質結構異動觸發暫存時自動標記 `mark_dirty(True)`，定時器暫存則不誤標記。
     - 正式存檔 `save_project`（支援 `silent` 參數）、`save_project_as`、專案載入 `load_project_data`、新開專案 `_reset_project_state` 完成時自動重設 `mark_dirty(False)`。
  3. **關閉事件攔截與確認對話框**：
     - `ProjectController.on_close_event`：若稿件未存檔且處於使用者互動模式，彈出「**稿件尚未存檔**」對話框。
     - 提供「儲存(&S)」、「不儲存(&D)」、「取消」三選項：
       - 【儲存】：執行 `save_project(silent=True)`，成功後關閉程式，失敗則阻止關閉。
       - 【不儲存】：放棄變更直接關閉，不覆寫暫存檔，正常儲存偏好設定。
       - 【取消】：呼叫 `event.ignore()` 中止關閉，留在編輯器。
  4. **版本發布與 Git 忽略規則強化**：
     - `.gitignore`：除 `pre-release/` 外，同步加入 `pre-realease/` 等拼寫相容忽略規則，徹底杜絕二進位發布檔推送到 GitHub 遠端儲存庫。
     - GitHub Pre-release：發布 `v0.1.1-beta`，並上傳 Windows 安裝程式（Setup.exe）與免安裝綠色包（.zip）雙版本資產。

- **當前任務狀態**：
  1. Python 3.14 已透過目錄聯結（Directory Junction）統一固定於 `C:\Python314`，並已將 `C:\Python314` 與 `C:\Python314\Scripts` 加入使用者環境變數 `Path`。
  2. 專案 `.venv\pyvenv.cfg` 之 `home` 與 `executable` 已固定指向 `C:\Python314`。
  3. 打包工具 `.agents\build\build.bat` 經雙重驗證打包順暢，成功產出 `dist\Jiufang_Novel_Editor\Jiufang_Novel_Editor.exe`，且打包後自動清理臨時 spec 檔以維護根目錄整潔。
  4. 全套 171 項測試維持 100% 通過。
- **下一個 Agent 的任務指引**：
  1. 系統 Python 3.14 統一安裝/對齊至 `C:\Python314`。
  2. 打包請一律使用 `.agents\build\build.bat`。注意在 Windows 上執行 PyInstaller 時應透過 `python -m PyInstaller` 避免二進位 stub 寫死路徑之錯誤。

  2. 存檔與路徑相關功能一律使用 `mc.get_storage_path()`、`mc.get_story_dir()`、`mc.get_temp_dir()`、`mc.get_export_dir()`，嚴禁硬編碼。
  3. 執行 `pytest tests/` 時若被轉入背景任務請務必使用 `manage_task` 追蹤 status 直至 DONE。
  4. **有新增、修改或刪除測試時，請務必隨同更新 `.agents/docs/TEST_SUITE.md`**。

