# 九方小說編輯器 — 交接文件

> 最後更新：2026-09-28，完成專案狀態記憶功能 (Schema v14) 與巡檢維護。

## 0. ⚠️ 專案交接守則 (CRITICAL RULES)

1. **嚴格的範圍控制**：每次修改聚焦於指派任務檔案，不要發散，不要隨意大範圍破壞架構。
2. **每次結束必寫交接記錄**：當完成任務，**必須**修改本 HANDOVER.md 的「第 3 節 (目前執行狀態)」，清楚寫下變更內容與下一個 Agent 的指引。
3. **MVC 架構原則**：`views/` 保持純 UI、`controllers/` 處理業務邏輯、`services/` 專司資料存取。
4. **遇錯即停**：如果測試未通過，請立即排查修復後再進入下一步。
5. **打包檔案收納禁令**：所有建置與打包相關腳本（`build.bat`、`Jiufang_Novel_Editor.spec`、`setup.iss`）**一律存放在 .agents/build/**，**嚴禁複製或放置於專案根目錄**。

---

## 1. 接手概覽 (Overview)

這是一個基於 Python + PyQt6 的桌面端小說寫作軟體。專案採用嚴格 MVC 架構，並具備 262 項以上的單元與整合測試。
目前已經完成核心寫作、資料集面板、儲存(SQLite)、多格式匯出、AI 助手與長文分析、數據儀表板、文風檢查等完整功能。
詳細架構請務必閱讀 `.agents/docs/ARCHITECTURE.md`。歷史修改紀錄請參閱 `CHANGELOG.md`。

---

## 2. 陷阱清單 (Traps)

### 陷阱 1：寫作打卡熱力圖（Heatmap）網格與星期對齊
- 熱力圖的網格繪製為 24 欄（週）× 7 列（星期一至日）。計算起始日時，必須以「本週一」為基準向前推 23 週（共 24 週）：`curr_monday = today - datetime.timedelta(days=today.weekday())`，`start_date = curr_monday - datetime.timedelta(weeks=23)`。切勿額外加上 `days=6`，否則會多扣除 6 天使最後一格停留在上週，導致當週歷史打卡全部落在網格之外。
- 熱力圖的 `date_map` 必須包含專案全部歷史寫作日誌（`full_date_map`），切勿僅傳遞給近期折線圖的 14 天切片數據。

### 陷阱 2：大量文字刪除/貼上行為監控已全面移除


### 陷阱 3：AI 相關設定路徑與對話視窗非模態


### 陷阱 4：章節樹「幕 (Scene)」節點與「檔案 (File)」節點的內容屬性等價性


### 陷阱 5：ai_worker.py 與 ai_service.py 之解耦與循環引用防護


### 陷阱 6：8GB 顯卡環境下 Local LLM 長文本分析之 Context 預算與實體檢索


### 陷阱 7：AI 任務取消與 Socket 連線主動關閉（嚴禁使用 QThread.terminate()）


### 陷阱 8：LM Studio 無 /v1/tokenize REST 端點與 UI 執行緒 Blocking I/O 防護


### 陷阱 9：儲存架構已完全廢棄 JSON 格式
- 專案存檔、另存新檔、Temp_doc/ 自動暫存檔全面採用 SQLite (.db)。
- JSON 舊檔相容讀取功能已完全移除，如果需要開啟極早期的 JSON 專案檔，將無法直接開啟，且 `services/storage.py` 已被刪除。

### 陷阱 10：AI 請求必須在非同步執行緒
- 絕對不要在 Qt 主執行緒同步呼叫 API，避免介面卡頓。在單元測試中若測試 UI 流程，應 mock worker.start。

### 陷阱 11：API Key 與專案檔案隔離
- ai_settings.json 與 lint_settings.json 為本機全域設定，不會寫入 SQLite 專案資料庫中。

### 陷阱 12：子控制器之間不得互相 import
- 所有子控制器在 __init__ 接收 main_controller 實例（self.mc），跨控制器操作一律透過 self.mc.xxx 存取，嚴禁子控制器互相 import，防止 Circular Import。

### 陷阱 13：JneProject 資料模型層級
- 專案字型、書名、大綱設定皆統一放置於 project.project_info (ProjectInfo dataclass) 中，請勿在 JneProject 頂層新增冗餘 getter/setter 或屬性。

### 陷阱 14：QSS Template 字串格式化大括號轉義
- theme_manager.py 的 BASE_THEME_TEMPLATE 會使用 format(**colors)，CSS 選擇器內的普通大括號必須寫為雙大括號 {{ 與 }}，僅有要被代換的變數（如 {status_bar_bg}）保留單大括號。

### 陷阱 15：章節標記色碼統一常數
- 章節與幕的進度標記色碼（Draft, 1st Edit, 2nd Edit, Final, Discarded）一律統一引用 models.models.MARK_COLOR_MAP，禁止在 Controller 或 View 中自行硬編碼字典。

### 陷阱 16：開啟新專案不可重設 UI 縮放比例
- 開啟新專案（_reset_project_state）僅重設當前專案資料與樹狀結構，不得修改全域介面縮放 scale_factor。

### 陷阱 17：存檔與暫存路徑請統一透過 MainController 取得
- 請統一呼叫 `self.mc.get_story_dir()` 與 `self.mc.get_temp_dir()` 取得路徑，不可硬編碼 `os.path.join(self.mc.app_dir, "story")`，以確保使用者自訂雲端同步路徑時能正確運作。

### 陷阱 18：小說文字儲存與匯出轉換
- 編輯器底層以純文字 Markdown 儲存，匯出時必須透過 `MarkdownConverter` 進行轉檔，確保輸出之 Word 文件（.docx）帶有真實樣式 Run、電子書（.epub）具有語意化 HTML 標籤、純文字（.txt）已清洗語法符號。

### 陷阱 19：不要在 apply_theme 中直接呼叫 QApplication.setStyleSheet()
- 在 PyQt6 / Windows 上，若對全域 `QApplication.instance()` 呼叫 `setStyleSheet`，會導致部分已手動指定字型的 widget（如 `QComboBox`）觸發全域字型 reset（變回 9pt）。
- 正確做法為在各對話框初始化時使用 `ThemeManager.apply_theme_to_dialog(self, parent)`，既保證完整繼承主題色彩與縮放，又不會污染或重設主視窗的字型。

### 陷阱 20：Windows 剪貼簿單元測試請 Mock，避免 OLE 重試與衝突
- 在單元測試中若需測試複製到剪貼簿功能（如 `copy_card_content`），應使用 `unittest.mock.patch.object(QApplication.clipboard(), "setText")` 驗證傳入參數，嚴禁直接依賴系統全域剪貼簿。在 Windows 平台無頭或背景測試環境中，`OpenClipboard` 易與其他程式（或 COM 歷程記錄）衝突觸發 `0x800401d0`，導致 Qt 不斷 retry 造成數秒卡頓並拋出 `AssertionError`。

### 陷阱 21：外部與本機網路端點測試必須 Mock
- 在測試 `AIService.detect_local_models` 時，不得直接發送真實 HTTP request 到未開放的本機端點（如 `99999` port），否則在 Windows 系統連線 socket 超時會導致測試每次延遲 2 秒以上，應使用 `unittest.mock.patch("urllib.request.urlopen")` 模擬異常以保持測試純淨與毫秒級快速執行。

### 陷阱 22：Antigravity Agent 執行測試與背景工作機制
- 專案全套測試數量達 262 項，完整執行需耗時約 35 秒。在 Antigravity 環境中，若使用 `run_command`，一旦執行時間超過 `WaitMsBeforeAsync` 上限（10 秒），指令會自動轉入背景執行緒 (`Background Task`)。此時 Agent 必須使用 `manage_task` 追蹤狀態直至 `DONE` 並讀取日誌回報結果，切勿誤判為測試死鎖或在背景未完成時提前結束回覆。

### 陷阱 23：SQLite Migration v10 -> v11 與 writing_logs.ai_details 序列化
- 在擴充 `writing_logs` 紀錄 AI 細部功能次數時，採用 JSON 格式儲存於 `ai_details` 欄位（而不是為每個可能新增的 AI 功能增加 SQL 欄位），以維持彈性擴充。
- 反序列化時需嚴格防禦：`details_raw` 若為 `None` 或無效字串，應安全回退為空字典 `{}`。
- 當新增資料庫版本時，既有遷移測試（如 `test_daily_progress_sync.py`）中的 `SELECT MAX(version)` 檢查應斷言等於 `DatabaseService.CURRENT_SCHEMA_VERSION`，避免因版本遞增而造成斷言失敗。

### 陷阱 24：深層資料集卡片匯出排版與標題降級（Depth >= 4）


---

## 3. 目前執行狀態與下一步指引 (CURRENT STATUS & NEXT STEPS)

- **當前任務狀態**：
  1. 最佳化計畫 (Phase O-6) View 介面穩定化已完成。
  2. 最佳化計畫 (Phase O-7) 開發工具鏈導入已完成。
  3. 已在專案根目錄建立 `pyproject.toml` 與 `.pre-commit-config.yaml`，提供 ruff 設定檔。
  4. **Phase O-1 至 O-7 全數執行完畢！** 專案已大幅度瘦身並提高型別安全與效能。
  5. 2026-09-22: 建立 `v0.1.7-beta` 標籤並推送到 GitHub。已撰寫發布說明於 `pre-release/release_notes_v0.1.7-beta.txt`。
  6. 2026-09-28: 新增記憶專案上次開啟檔案與游標位置的功能 (Schema Version 14)，包含單元與整合測試，測試套件總數增至 262 項，全數綠燈通過。

- **下一個 Agent 的任務指引**：
  1. 協助使用者完成 GitHub Release 上傳 (因為本機無 gh CLI)。
  2. 嚴格遵守 `.agents/rules/workspace_rules.md`。
  3. 執行測試請使用 `py -m pytest tests/`，確保 100% 通過。
