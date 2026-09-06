# 九方小說編輯器 — 交接文件

> 最後更新：2026-09-06，完成 GitHub 發布文案檢討改寫（去 Emoji、回歸同儕創作者平實語調）、增訂工作區發布規則，並發布 v0.1.3-Beta（包含 Setup.exe 與 Zip），全套 222 項單元測試維持 100% 通過。

### 陷阱 17：寫作打卡熱力圖（Heatmap）網格與星期對齊
- 熱力圖的網格繪製為 24 欄（週）× 7 列（星期一至日）。計算起始日時，必須以「本週一」為基準向前推 23 週（共 24 週）：`curr_monday = today - datetime.timedelta(days=today.weekday())`，`start_date = curr_monday - datetime.timedelta(weeks=23)`。切勿額外加上 `days=6`，否則會多扣除 6 天使最後一格停留在上週，導致當週歷史打卡全部落在網格之外。
- 熱力圖的 `date_map` 必須包含專案全部歷史寫作日誌（`full_date_map`），切勿僅傳遞給近期折線圖的 14 天切片數據。

### 陷阱 20：大量文字刪除/貼上行為監控已全面移除
- **背景與原因**：
  由於鍵盤敲擊、輸入法組字（IME）、日常退格（Backspace / Delete）以及剪貼文字在不同輸入環境下極易產生誤判，且給使用者帶來不必要的心理負擔與系統開銷。
- **現行架構處理**：
  - 已將 `StatsController.on_document_contents_change` 內的大量刪除計數邏輯徹底移除，僅保留正常字數統計與 session 計時。
  - 已自 `MainController` 拔除 `signal_text_pasted` 之統計監聽；`on_text_pasted` 與 `record_text_modification` 保留為 safe no-op 以維持向後相容。
  - `WritingLogDashboard` 表格已移除「大量異動(貼/刪)」欄位，恢復為標準 5 欄設定（日期、當日總時長、手寫字數、AI 續寫字數、AI 輔助與面向）；CSV 匯出亦同步剔除相關次數欄位。
  - 既有資料庫欄位（`paste_large_count`、`delete_large_count`）維持模型向後相容性，不破壞舊有專案存檔讀取。

### 陷阱 21：AI 相關設定路徑與對話視窗非模態
- **AI 設定檔儲存路徑嚴禁使用相對路徑**：
  在桌面端應用程式中，若直接使用 `"ai_settings.json"`，會隨啟動方式（捷徑、不同工作目錄、關聯開啟）而造成路徑漂移、設定遺失。必須統一使用 `AIService.get_settings_file_path()` 儲存於使用者 AppData 本機目錄（`%LOCALAPPDATA%/Jiufang_Novel_Editor/`），並保留舊版檔案向後相容與自動遷移。
- **AI 對話視窗必須保持非模態 (Modeless)**：
  切勿在 `open_ai_chat_dialog` 呼叫阻塞式 `dlg.exec()`，否則作家在等待 AI 回覆或查閱對話時會被鎖定主編輯器而無法繼續碼字。應使用單一實例保持與 `dlg.show()`、`dlg.raise_()`。

### 陷阱 22：章節樹「幕 (Scene)」節點與「檔案 (File)」節點的內容屬性等價性
- **問題根源**：
  編輯器核心結構中，「幕 (Scene)」節點（`node_type == "scene"`）與普通文件節點（`node_type == "file"`）均承載正文內文（`content`）。九方小說編輯器在章節結構與預設專案中，正文主要存放在 `scene` 節點內。
- **關鍵規範**：
  遍歷章節內文時（如跨章節全文搜尋、大綱檢視操作等），判斷式**絕對不可**只寫 `node_type == "file"`，必須寫 `node_type in ("file", "scene")`，否則所有幕節點的內文將被全面略過。
- **跳轉高亮校準**：
  從搜尋結果跳轉時，Markdown 標籤在渲染成富文本後可能導致字元位移，`navigate_to_global_match` 應以 `match_text` 與 `document().find()` 進行智慧校準，確保游標精確選取目標關鍵字。

---

## 4. 目前執行狀態與下一步指引 (CURRENT STATUS & NEXT STEPS)

- **本次完成事項（GitHub 文案檢討改寫、增訂發布規則、程式碼推送與 v0.1.3-Beta 正式發布）**：
  1. **文案風格檢討與全面改寫**：
     - 全面檢視 `README.md`，保留作者親筆自述前言，將功能介紹徹底去除 Emoji 與行銷煽情詞，以同儕小說創作者視角平實說明功能設計初衷與已知限制。
     - 透過 GitHub API 更新遠端歷次發布（`v0.1.0-beta`、`v0.1.1-beta`、`v0.1.2-beta`）之 Release 內文，全面剔除 Emoji 與誇飾字眼。
  2. **工作區規則增訂 (`.agents/rules/workspace_rules.md`)**：
     - 正式新增「發布規則與文案風格規範」，明文規定溝通定位、文字風格禁令（嚴禁 Emoji 與過度矯情）與 Release SOP 六步驟標準作業流程。
  3. **專案變更推送與 v0.1.3-Beta 發布**：
     - 提交包含節點類型轉換（卷/章/幕）、全文搜尋修復、文字排版工具、打字機模式微調、移除日常刪貼監控等完整更新至 Git 並推送到遠端。
     - 建立 `v0.1.3-beta` 標籤並於 GitHub 建立 Pre-release，上傳 `Jiufang_Novel_Editor_0.1.3-Beta-Setup.exe` 與 `Jiufang_Novel_Editor_0.1.3-Beta-Setup.zip`。
  4. **全套測試維持 100% 綠燈**：
     - 222 項單元測試全數通過。

- **當前任務狀態**：
  1. v0.1.3-Beta 發布完成，所有公開文件風格已對齊創作者同儕平實語氣。
  2. 程式碼與標籤皆已同步至 GitHub 遠端儲存庫。

- **下一個 Agent 的任務指引**：
  1. 後續所有對外文件或 Release Notes 必須遵守 `.agents/rules/workspace_rules.md` 中的發布規範，嚴禁使用 Emoji 與煽情行銷詞彙。
  2. 系統 Python 3.14 統一安裝/對齊至 `C:\Python314`。
  3. 打包請一律使用 `.agents\build\build.bat`。產物必須置於 `pre-release/`，嚴禁放置於專案根目錄。
  4. 存檔與路徑相關功能一律使用 `mc.get_storage_path()`、`mc.get_story_dir()`、`mc.get_temp_dir()`、`mc.get_export_dir()`，嚴禁硬編碼。
  5. 執行 `pytest tests/` 時若被轉入背景任務請務必使用 `manage_task` 追蹤 status 直至 DONE。
  6. **有新增、修改或刪除測試時，請務必隨同更新 `.agents/docs/TEST_SUITE.md`**。

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
- **AI 整合與長文捲動壓縮（HRCI）**：
  - 支援多輪對話、智慧續寫（含防護開關）、本機模型偵測 (Ollama/LM Studio)。
  - **長文分析演算法（HRCI）**：為 9B 以下本地小模型設計「語義安全分塊 + 捲動狀態壓縮（雙軌索引） + 全局最終整合」機制，突破 Context Window 限制並防止細節丟失。
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
    ├── Phase 13：技術債與冗餘程式碼清理（✅ 全部完成）
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
    └── Phase 23：AI 輔助創作誠信指標細項打點與寫作儀表板升級（✅ 全部完成）
        ├── 23.1 誠信光譜資料模型：WritingLogEntry 擴充 ai_details 字典，區分「正文代筆 (continuation)」、「設定架構整理 (character/world/timeline)」、「文字審校 (proofread/impression)」、「靈感對話 (chat)」
        ├── 23.2 資料庫平滑升級：DatabaseMigrations 實現 v10 -> v11，writing_logs 新增 ai_details TEXT DEFAULT '{}' 欄位，維持舊檔 100% 相容
        ├── 23.3 全 AI 功能精準打點：對話、角色提取、世界觀提取、時間線梳理、文學評語、AI 校稿與智慧擴寫皆正確傳入 feature_key
        ├── 23.4 儀表板 UI 與圖表升級：頂部 KPI 突出「手寫原創率」與「主要角色定位」；日誌表格第 5 欄顯示膠囊標籤 [🔍校審][🧩整理][💬靈感] 與懸停明細 Tooltip；圖表呈現手創率環形圖與面向統計明細；CSV 匯出細部統計
        └── 23.5 測試套件擴充：新增 test_stats_ai_breakdown.py，186/186 項測試全數通過
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

### 陷阱 16：SQLite Migration v10 -> v11 與 writing_logs.ai_details 序列化
- 在擴充 `writing_logs` 紀錄 AI 細部功能次數時，採用 JSON 格式儲存於 `ai_details` 欄位（而不是為每個可能新增的 AI 功能增加 SQL 欄位），以維持彈性擴充。
- 反序列化時需嚴格防禦：`details_raw` 若為 `None` 或無效字串，應安全回退為空字典 `{}`。
- 當新增資料庫版本時，既有遷移測試（如 `test_daily_progress_sync.py`）中的 `SELECT MAX(version)` 檢查應斷言等於 `DatabaseService.CURRENT_SCHEMA_VERSION`，避免因版本遞增而造成斷言失敗。

---

## 4. 目前執行狀態與下一步指引 (CURRENT STATUS & NEXT STEPS)

- **本次完成事項 (Phase 25：AI 誠信光譜指標精準化與創作日誌全域 UI 縮放自適應，全套 193 項單元測試 100% 綠燈)**：
  1. **AI 誠信光譜指標精準化**：
     - 使用者指出「大量貼上文字」與「大量刪除文字」為一般文字剪貼與排版行為，不應列入 AI 介入度或誠信指標。
     - 在 `WritingChartView._paint_ai_ratio` 的「誠信指標與輔助明細」中，正式剔除「📋 大量貼上文字」與「✂️ 大量刪除文字」，專注呈現「親筆手創」、「AI 正文代筆」、「設定架構整理」、「責任編輯審校」、「靈感構思對話」等真正與 AI 相關之創作面向。
     - 在 `WritingLogDashboard.refresh_data` 中，移除 `card_ai_ratio`（創作誠信與 AI 輔助指標卡片）副標題上的貼上/刪除統計文字，保持指標卡片純淨反映原創與 AI 輔助；日誌表格中仍保留第 4 欄獨立的「大量異動(貼/刪)」以供作家隨時檢閱異常剪貼紀錄。
     - 表格中「AI 輔助與面向」欄位 ToolTip 同步清理，移除大量貼上與刪除次數，與第 4 欄專屬 ToolTip 各司其職。
  2. **創作日誌與寫作儀表板全域 UI 縮放反應**：
     - `WritingLogDashboard` 外層引入 `QScrollArea`，確保在高解析度大縮放比例（如 150%、175%、200%）或較小視窗尺寸下，整個儀表板（標題、卡片、圖表、日誌表格）均能自適應等比縮放且垂直滾動流暢，絕無元件重疊、擠壓變形或文字截斷問題。
     - `MetricCard`、儀表板標題、分享/匯出/關閉按鈕、視圖切換按鈕、表格表頭與每列高度（`defaultSectionSize`）均完整套用 `scale_factor` 縮放。
     - `WritingChartView` 四大圖表視圖（字數趨勢圖、打卡熱力圖、各章字數圖、AI 介入度環形圖）底層所有文字字級、線寬、方塊尺寸、間距與邊距全面響應 `self.scale_factor`。
     - 在 `StatsController.show_writing_log_dashboard` 中，開啟日誌視圖時自動強制同步主視窗最新的 `scale_factor`，保證一開啟即是完美比例。
  3. **測試套件擴充與全量驗證**：
     - 在 `tests/test_writing_log_enhancements.py` 新增 `test_ai_ratio_chart_excludes_paste_and_delete` 與 `test_writing_log_dashboard_ui_scale_response`。
     - 全專案 31 個測試模組、193 項測試 100% 通過（`pytest tests/` 193 passed in 44.24s）。
     - 同步更新 `.agents/docs/TEST_SUITE.md` 與本交接文件。

- **當前任務狀態**：
  1. AI 介入度與誠信分析圖已不再包含非 AI 的文字剪貼與刪除行為，指標定義更嚴謹、客觀。
  2. 創作日誌與寫作儀表板完整跟隨設定中的介面縮放百分比（100%、125%、150%、175%、200% 等）縮放與適配。
  3. 全套 193 項測試維持 100% 通過。
- **下一個 Agent 的任務指引**：
  1. 系統 Python 3.14 統一安裝/對齊至 `C:\Python314`。
  2. 打包請一律使用 `.agents\build\build.bat`。注意在 Windows 上執行 PyInstaller 時應透過 `python -m PyInstaller` 避免二進位 stub 寫死路徑之錯誤。
  3. 存檔與路徑相關功能一律使用 `mc.get_storage_path()`、`mc.get_story_dir()`、`mc.get_temp_dir()`、`mc.get_export_dir()`，嚴禁硬編碼。
  4. 執行 `pytest tests/` 時若被轉入背景任務請務必使用 `manage_task` 追蹤 status 直至 DONE。
  5. **有新增、修改或刪除測試時，請務必隨同更新 `.agents/docs/TEST_SUITE.md`**。

