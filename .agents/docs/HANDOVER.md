# 九方小說編輯器 — 交接文件

> 最後更新：2026-09-03，完成 Phase 27「Markdown 所見即所得空行雙倍行高根除（精確單行高度還原）」，全部 144 項單元測試全數通過。

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

---

## 4. 目前執行狀態與下一步指引 (CURRENT STATUS & NEXT STEPS)

- **本次完成事項 (Phase 29：修復測試套件剪貼簿 OLE 重試卡頓與網路 Socket 阻塞問題，恢復全套 154 項自動化測試 100% 綠燈)**：
  1. **排查測試卡頓與未回報的根本原因**：
     - **背景工作盲點**：`python -m pytest tests/` 跑全套 154 項測試需要約 17 秒，超過 tool 的 10 秒上限後會自動切入 Background Task，上個 Agent 未使用 `manage_task` 監控完成狀態就中斷，導致使用者端看似卡死。
     - **Socket Timeout 阻塞**：`tests/test_ai_service.py` 中的 `test_detect_local_models_empty_or_offline` 直接向 99999 port 發送真實網路連線，造成每次執行固定卡住 2 秒多。
     - **Windows OLE 剪貼簿衝突**：`tests/test_context_menus.py` 中的 `test_card_copy_content` 直接呼叫 Windows 剪貼簿，觸發 COM error `0x800401d0: OpenClipboard 失敗`，Qt 連續重試 6 次造成嚴重延遲並導致測試失敗。
  2. **測試套件全面優化與修復**：
     - `tests/test_context_menus.py`：使用 `patch.object(QApplication.clipboard(), "setText")` 精準驗證卡片內文拷貝，徹底杜絕 Windows 剪貼簿 OLE 衝突與重試延遲。
     - `tests/test_ai_service.py`：使用 `patch("urllib.request.urlopen")` 模擬離線/連線異常，消除真實 socket 連線超時，該測試耗時由 2.03s 降至 0.09s，同時補齊空 URL 邊界案例。
  3. **測試與文件同步**：
     - 全套 **154 項單元測試 100% 通過**（`pytest tests/` 154 passed in 17s）。
     - 同步更新 `.agents/docs/TEST_SUITE.md` 與 `.agents/docs/HANDOVER.md`。
- **當前任務狀態**：
  1. 自動化測試套件完全無阻礙、無衝突，全套 154 項單元測試均可在 17 秒內乾淨且穩定通過。
- **下一個 Agent 的任務指引**：
  1. 執行 `pytest tests/` 時請注意其耗時約 17 秒，若被轉入背景任務請務必使用 `manage_task` 追蹤 status 直至 DONE。
  2. 編寫涉及系統級服務（剪貼簿、網路請求）的單元測試時，請嚴格遵守 Mock 原則。
  3. **有新增、修改或刪除測試時，請務必隨同更新 `.agents/docs/TEST_SUITE.md`**。
