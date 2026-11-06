# 九方小說編輯器 — 交接文件

> 最後更新：2026-11-06，完成 Phase 30「純本機 AI 語意校稿引擎與架構減法重構」全數階段（拔除除校稿外所有 AI 功能）及取消 Local LLM 小模型開發規則。

## 0. 專案交接守則 (CRITICAL RULES)

1. **嚴格的範圍控制**：每次修改聚焦於指派任務檔案，不要發散，不要隨意大範圍破壞架構。
2. **每次結束必寫交接記錄**：當完成任務，**必須**修改本 HANDOVER.md 的「第 3 節 (目前執行狀態)」，清楚寫下變更內容與下一個 Agent 的指引。
3. **MVC 架構原則**：`views/` 保持純 UI、`controllers/` 處理業務邏輯、`services/` 專司資料存取。
4. **遇錯即停**：如果測試未通過，請立即排查修復後再進入下一步。
5. **打包檔案收納禁令**：所有建置與打包相關腳本（`build.bat`、`Jiufang_Novel_Editor.spec`、`setup.iss`）**一律存放在 .agents/build/**，**嚴禁複製或放置於專案根目錄**。

---

## 1. 接手概覽 (Overview)

這是一個基於 Python + PyQt6 的桌面端小說寫作軟體。專案採用嚴格 MVC 架構，並具備 238 項單元與整合測試（36 個測試模組）。
目前已完成核心寫作、資料集面板、儲存(SQLite)、多格式匯出、純本機 AI 語意校稿、數據儀表板、文風檢查等完整功能。
詳細架構請務必閱讀 `.agents/docs/ARCHITECTURE.md`。歷史修改紀錄請參閱 `.agents/docs/CHANGELOG.md`。

---

## 2. 陷阱清單 (Traps)

### 陷阱 1：寫作打卡熱力圖（Heatmap）網格與星期對齊
- 熱力圖的網格繪製為 24 欄（週）× 7 列（星期一至日）。計算起始日時，必須以「本週一」為基準向前推 23 週（共 24 週）：`curr_monday = today - datetime.timedelta(days=today.weekday())`，`start_date = curr_monday - datetime.timedelta(weeks=23)`。切勿額外加上 `days=6`，否則會多扣除 6 天使最後一格停留在上週，導致當週歷史打卡全部落在網格之外。
- 熱力圖的 `date_map` 必須包含專案全部歷史寫作日誌（`full_date_map`），切勿僅傳遞給近期折線圖的 14 天切片數據。

### 陷阱 2：大量文字刪除/貼上行為監控已全面移除

### 陷阱 3：AI 相關設定路徑與對話視窗非模態

### 陷阱 4：章節樹「幕 (Scene)」節點與「檔案 (File)」節點的內容屬性等價性

### 陷阱 5：ai_worker.py 與 ai_service.py 之解耦與循環引用防護

### 陷阱 6：AI 任務取消與 Socket 連線主動關閉（嚴禁使用 QThread.terminate()）

### 陷阱 7：LM Studio 無 /v1/tokenize REST 端點與 UI 執行緒 Blocking I/O 防護

### 陷阱 8：儲存架構已完全廢棄 JSON 格式
- 專案存檔、另存新檔、Temp_doc/ 自動暫存檔全面採用 SQLite (.db)。
- JSON 舊檔相容讀取功能已完全移除，如果需要開啟極早期的 JSON 專案檔，將無法直接開啟，且 `services/storage.py` 已被刪除。

### 陷阱 9：AI 請求必須在非同步執行緒
- 絕對不要在 Qt 主執行緒同步呼叫 API，避免介面卡頓。在單元測試中若測試 UI 流程，應 mock worker.start。

### 陷阱 10：設定檔與專案檔案隔離
- ai_settings.json 與 lint_settings.json 為本機全域設定，不會寫入 SQLite 專案資料庫中。

### 陷阱 11：子控制器之間不得互相 import
- 所有子控制器在 __init__ 接收 main_controller 實例（self.mc），跨控制器操作一律透過 self.mc.xxx 存取，嚴禁子控制器互相 import，防止 Circular Import。

### 陷阱 12：JneProject 資料模型層級
- 專案字型、書名、大綱設定皆統一放置於 project.project_info (ProjectInfo dataclass) 中，請勿在 JneProject 頂層新增冗餘 getter/setter 或屬性。

### 陷阱 13：QSS Template 字串格式化大括號轉義
- theme_manager.py 的 BASE_THEME_TEMPLATE 會使用 format(**colors)，CSS 選擇器內的普通大括號必須寫為雙大括號 {{ 與 }}，僅有要被代換的變數（如 {status_bar_bg}）保留單大括號。

### 陷阱 14：章節標記色碼統一常數
- 章節與幕的進度標記色碼（Draft, 1st Edit, 2nd Edit, Final, Discarded）一律統一引用 models.models.MARK_COLOR_MAP，禁止在 Controller 或 View 中自行硬編碼字典。

### 陷阱 15：開啟新專案不可重設 UI 縮放比例
- 開啟新專案（_reset_project_state）僅重設當前專案資料與樹狀結構，不得修改全域介面縮放 scale_factor。

### 陷阱 16：存檔與暫存路徑請統一透過 MainController 取得
- 請統一呼叫 `self.mc.get_story_dir()` 與 `self.mc.get_temp_dir()` 取得路徑，不可硬編碼 `os.path.join(self.mc.app_dir, "story")`，以確保使用者自訂雲端同步路徑時能正確運作。

### 陷阱 17：小說文字儲存與匯出轉換
- 編輯器底層以純文字 Markdown 儲存，匯出時必須透過 `MarkdownConverter` 進行轉檔，確保輸出之 Word 文件（.docx）帶有真實樣式 Run、電子書（.epub）具有語意化 HTML 標籤、純文字（.txt）已清洗語法符號。

### 陷阱 18：不要在 apply_theme 中直接呼叫 QApplication.setStyleSheet()
- 在 PyQt6 / Windows 上，若對全域 `QApplication.instance()` 呼叫 `setStyleSheet`，會導致部分已手動指定字型的 widget（如 `QComboBox`）觸發全域字型 reset（變回 9pt）。
- 正確做法為在各對話框初始化時使用 `ThemeManager.apply_theme_to_dialog(self, parent)`，既保證完整繼承主題色彩與縮放，又不會污染或重設主視窗的字型。

### 陷阱 19：Windows 剪貼簿單元測試請 Mock，避免 OLE 重試與衝突
- 在單元測試中若需測試複製到剪貼簿功能（如 `copy_card_content`），應使用 `unittest.mock.patch.object(QApplication.clipboard(), "setText")` 驗證傳入參數，嚴禁直接依賴系統全域剪貼簿。在 Windows 平台無頭或背景測試環境中，`OpenClipboard` 易與其他程式（或 COM 歷程記錄）衝突觸發 `0x800401d0`，導致 Qt 不斷 retry 造成數秒卡頓並拋出 `AssertionError`。

### 陷阱 20：外部與本機網路端點測試必須 Mock
- 在測試 `AIService.detect_local_models` 時，不得直接發送真實 HTTP request 到未開放的本機端點（如 `99999` port），否則在 Windows 系統連線 socket 超時會導致測試每次延遲 2 秒以上，應使用 `unittest.mock.patch` 模擬異常以保持測試純淨與毫秒級快速執行。

### 陷阱 21：Antigravity Agent 執行測試與背景工作機制
- 專案全套測試完整執行需耗時約 30 秒。在 Antigravity 環境中，若使用 `run_command`，一旦執行時間超過 `WaitMsBeforeAsync` 上限（10 秒），指令會自動轉入背景執行緒 (`Background Task`)。此時 Agent 必須等待背景任務完成通知並讀取結果，切勿誤判為測試死鎖或在背景未完成時提前結束回覆。

### 陷阱 22：SQLite Migration v10 -> v11 與 writing_logs.ai_details 序列化
- 在擴充 `writing_logs` 紀錄 AI 細部功能次數時，採用 JSON 格式儲存於 `ai_details` 欄位，以維持彈性擴充與向下相容。
- 反序列化時需嚴格防禦：`details_raw` 若為 `None` 或無效字串，應安全回退為空字典 `{}`。
- 當新增資料庫版本時，既有遷移測試（如 `test_daily_progress_sync.py`）中的 `SELECT MAX(version)` 檢查應斷言等於 `DatabaseService.CURRENT_SCHEMA_VERSION`，避免因版本遞增而造成斷言失敗。

---

## 3. 目前執行狀態與下一步指引 (CURRENT STATUS & NEXT STEPS)

- **當前任務狀態**：
  1. **2026-11-06：完成規則清理（移除 Local LLM 小模型開發規則）**：
     - 刪除 `.agents/rules/long-document-analysis.md` 與誤建之 `.agents/rules/.agents`。
     - 自 `.agents/rules/workspace_rules.md`、`.agents/docs/ARCHITECTURE.md`、`.agents/docs/LOCAL_AI_PROOFREAD_MIGRATION_PLAN.md` 移除「10B 等級中小模型防卡死守則」。
  2. **2026-11-06：完成 Phase 30 階段三與階段四（拔除除了校稿以外的所有 AI 功能，維持僅支援本機）**：
     - **Controller 層瘦身 (`controllers/ai_controller.py`)**：移除對話、續寫、擴寫、角色抽取與卡片生成等過渡方法，專職處理本機 AI 設定與本機 AI 校稿。
     - **Service 層清理 (`services/ai_worker.py`, `services/ai_service.py`, `services/ai_settings_service.py`)**：
       - 移除 `AIWorker`、`AIChatWorker`、`AIContinuationWorker`、`AIStreamWorker`，僅保留 `BaseAIWorker` 與 `AIProofreadWorker`。
       - 移除雲端特化協定分支（Anthropic / OpenAI 等雲端預設）與角色抽取解析邏輯，統一保留本機 `Ollama` 與 `LM Studio` 端點支援。
       - 刪除已廢棄的 `services/token_estimator.py`、`services/hardware_detector.py` 與 `resources/prompts/` 下 6 個舊功能提示詞檔案。
     - **View 層廢棄視窗清理**：刪除 `ai_chat_dialog.py`、`ai_expansion_dialog.py`、`ai_scope_dialog.py`、`ai_preview_dialog.py`、`ai_character_review_dialog.py`、`ai_floating_hud.py`、`ai_task_overlay.py`。
     - **測試套件重整與文件同步**：刪除對應廢棄功能的 6 個測試模組，更新 `test_ai_cancellation.py`、`test_ai_service.py`、`test_ai_settings_and_worker.py`。全套 36 個測試模組、238 項測試 100% 綠燈通過，並同步更新 `TEST_SUITE.md`、`ROADMAP.md`、`ARCHITECTURE.md`。

- **下一個 Agent 的任務指引**：
  1. **Phase 30 全數完成**：目前專案已轉型為純本機 AI 語意校稿引擎，架構與測試均處於乾淨穩定狀態。
  2. 後續若有新功能需求或版本打包發布，請遵循 `.agents/rules/workspace_rules.md` 之 MVC 分層規範與 Release SOP 執行。
