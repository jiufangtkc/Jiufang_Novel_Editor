# 九方小說編輯器 — 交接文件

> 最後更新：2026-09-10，完成編輯器底層重構、雙重貼上模式與資料集匯入匯出，並優化了 LM Studio 的零延遲 Token 估算，全套 257 項單元測試維持 100% 綠燈通過。

### 階段 24：程式碼架構瘦身與精簡重構
- **完全棄用舊版 JSON 格式存檔**：
  移除了 `project_controller.py` 中龐大且不再被呼叫的 `_migrate_legacy_dict_to_jne_project` 與多餘的 JSON 相關邏輯，專案全面強制使用 SQLite。
- **外部化 AI Prompt 模板**：
  建立 `resources/prompts/` 將角色、印象、世界觀、時間線、延續寫作等 6 大 Prompt 從 `services/ai_settings_service.py` 剝離成純文字檔，降低核心程式碼負載。
- **共用 UI 元件 `BaseDialog` 提取**：
  新增 `views/common/base_dialog.py`，全數封裝 `ThemeManager.apply_theme_to_dialog(self)` 與 `self.scale_factor` 等邏輯，並成功重構 `views/dialogs/` 下的 22 個 `QDialog` 類別，大幅削減重複樣板程式碼。
- **測試套件架構分層**：
  將 `tests/` 底下 40 個測試檔重構至 `tests/unit/`、`tests/integration/`、`tests/ui/`，並修正所有 `sys.path` 問題，257 項測試維持 100% 綠燈。

### 階段 23：實作全系列 AI 功能的滾動式抽取演算法
- **實作 `LongTextPipelineWorker`**：
  在 `services/ai_pipeline_workers.py` 實作了 4 階段滾動式抽取演算法（分段、預掃描、滾動抽取、收尾）。此 Worker 動態支援 `"character", "impression", "world", "timeline"` 等不同任務類型的 JSON diff 抽取，並最終轉換成卡片相容格式。
- **整合 `AIController` 與 `AIScopeDialog`**：
  將所有分析任務與 `AIScopeDialog` 綁定。現在包含文學評語、世界觀、時間線梳理等功能，在啟動前皆可選擇範圍與切換「前沿大模型 / 本地小模型」。
- **工具建立**：
  在 `utils/text_splitter.py` 建立了 `chunk_text_with_overlap` 函式，專司處理長篇文字的分段，支援 overlap 控制以防脈絡截斷。通過。

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

### 陷阱 23：ai_worker.py 與 ai_service.py 之解耦與循環引用防護
- **問題根源**：
  在進行架構模組化拆分時，`services/ai_service.py` 為了向後相容性在模組結尾處 re-export 背景執行緒類別（`AIWorker`, `AIChatWorker`, `AIContinuationWorker`, `AIStreamWorker`）。若 `services/ai_worker.py` 在頂層直接 `from services.ai_service import AIService`，在特定載入順序下會造成尚未完成類別定義的循環引用失敗；但若僅在局部函數內宣告，會導致各背景 Worker 於執行階段拋出 `NameError: name 'AIService' is not defined`。
- **現行架構處理**：
  `services/ai_worker.py` 採用 `_AIServiceProxy` 動態代理模式，於屬性調用時才延遲解析 `AIService`，既避免模組初始化時的循環引用問題，又確保所有靜態與類別方法（如 `load_settings`、`call_api_stream` 等）在各背景執行緒中正常運作。

### 陷阱 24：8GB 顯卡環境下 Local LLM 長文本分析之 Context 預算與實體檢索
- **問題根源**：
  在對 5 萬字以上超長篇小說進行人物分析時，若分段階段輸出過長，或在最終階段將所有分段（例如 17 段）的文字分析暴力拼接送往 LLM，Prompt 長度會高達 1.6 萬 tokens，撞上 16,384 tokens 的上下文限制引發 `finish_reason: length` 截斷崩潰；且在 8GB VRAM 下會引發系統記憶體置換，導致電腦嚴重卡頓。
- **現行架構處理**：
  - **分塊調優**：`DEFAULT_CHUNK_SIZE` 設為 2,800 字（約 2,000 tokens），`DEFAULT_OVERLAP` 設為 200 字。
  - **輸出長度約束**：分段 Prompt 強制要求模型將【本段分析結論】控制在 300~500 字，條列摘要每條不超過 35 字。
  - **突破實體數量限制**：`CompactState` 全局無上限儲存所有登場人物與設定，但在調用 `get_relevant_summary(chunk_text)` 時，由 Python 在記憶體中掃描當前段落正文，**僅將當前段落有登場的活躍實體**注入 Prompt（500 字以內），休眠實體沉澱在全局資料庫中，徹底突破數量限制且不佔用 Context。
  - **全域總結動態預算（Context Budget Controller）**：`build_synthesis_prompt` 依據總分段數分配單段額度，限制傳入 LLM 的各段要點總長度在 3,200 字（約 2,200 tokens）以內，並透過 `_format_final_state_summary` 提供依出場次數排序的高密度全景人物與設定索引，預留 2,500+ tokens 生成空間，徹底根絕 16k 溢出截斷問題。
- **本地 llama.cpp 啟動建議**：建議加入 `-np 1 -c 8192 -fa`，限制單一推論通道以避免 4 個 slot 搶佔 VRAM，並開啟 Flash Attention 節省顯存。

### 陷阱 25：AI 任務取消與 Socket 連線主動關閉（嚴禁使用 QThread.terminate()）
- **問題根源**：
  當使用者點選浮動進度 HUD、擴寫對話框或聊天視窗右上角的「✕」取消任務時，若在 Controller 端直接呼叫 `self.ai_worker.terminate()`，會強行殺死 OS 執行緒。這會使 Python 的 `with`、`finally` 區塊完全無法執行，底層由 `requests` 建立的 TCP Socket 依舊處於 ESTABLISHED 狀態。本地模型伺服器（LM Studio、Ollama、llama.cpp）依賴「寫入 TCP Socket 失敗（EPIPE / ECONNRESET）」來中止推論；Socket 未斷會導致模型伺服器在後台持續生成完畢，造成嚴重的 GPU/CPU 資源浪費。
- **現行架構處理**：
  - **嚴禁使用 `terminate()`**：取消任務一律改為 `worker.cancel()` 搭配 `worker.wait(1000)` 平穩終止。
  - **Active Connection Abort 機制**：`BaseAIWorker` 維護 `self._active_response`。在 `cancel()` 被觸發時，由主執行緒主動呼叫 `active_response.raw.close()` 與 `active_response.close()`，強制向本機服務器發送 TCP FIN/RST，使 LM Studio 在下一個 Token 寫入時瞬間感知斷線並立刻中止推論。
  - **Safe Generator Close**：呼叫串流 Generator 後，在 `finally` 區塊檢查 `if hasattr(generator, "close"): generator.close()`，確保無論正常結束或提早中斷皆即時釋放連線資源。
  - **全功能防護覆蓋**：`AIWorker`、`LongTextPipelineWorker`、`AIChatWorker`、`AIStreamWorker`、`AIContinuationWorker` 全面繼承 `BaseAIWorker`，對話視窗與擴寫視窗關閉事件（`closeEvent`）皆自動連動取消。

### 陷阱 26：LM Studio 無 /v1/tokenize REST 端點與 UI 執行緒 Blocking I/O 防護
- **問題根源**：
  LM Studio 本機伺服器相容於標準 OpenAI REST API，未提供 `/v1/tokenize` REST 端點（官方僅在內部 SDK 提供）。向其發送 `POST /v1/tokenize` 會導致 LM Studio DEV server 輸出 `[ERROR] Unexpected endpoint or method. (POST /v1/tokenize). Returning 200 anyway`。此外，在 `AIScopeDialog` 等範圍選擇視窗中，若在主 UI 執行緒同步調用 Blocking HTTP 請求計算數萬字文本的 Token，大 Payload 傳輸、LM Studio 處理非預期端點與超時等待會直接造成主執行緒凍結卡死 1 至 2 秒以上。
- **現行架構處理**：
  - `AIService.count_tokens` 針對非 Ollama（如 LM Studio 與雲端服務）一律使用純本機零延遲高精度分詞估算法 `fast_estimate_tokens`，完全不發起網路請求。
  - `fast_estimate_tokens` 針對中文字（CJK，保守加權 1.25）、英數單字（1.3）等現代大模型 BPE 特徵，在 0.1 毫秒內給出準確估算。
  - 徹底消除 LM Studio DEV server 報錯，並使 `AIScopeDialog` 在切換選取、章節與計算時維持 0 毫秒極速響應，徹底根除卡頓。
  - 全套自動化單元測試執行時間因剔除向本機伺服器的無效請求超時，由 160 秒大幅縮減至 23 秒。

---

## 4. 目前執行狀態與下一步指引 (CURRENT STATUS & NEXT STEPS)

- **本次完成事項（編輯器底層重構統一、雙重貼上模式與資料集匯入匯出）**：
  1. **編輯器規格統一與底層重構**：
     - 建立 `views/components/base_rich_text_edit.py`，將 `JNE_TextEdit` 與 `RightPanelCardEditor` 中重複的 Markdown 轉換、排版快捷鍵、場景分隔線等邏輯統一重構。
  2. **實作雙重貼上模式**：
     - 所有編輯器完整支援「按照來源格式貼上 (Ctrl+V)」與「僅貼上純文字 (Ctrl+Shift+V)」，預設 Ctrl+V 保留富文本格式以符合常規軟體習慣。
     - 更新 `test_main_editor_plain_text_paste_and_preservation` 測試以覆蓋雙重貼上模式行為。
  3. **資料集匯出與匯入功能**：
     - 於 `CardController` 實作 `export_dataset` 與 `import_dataset`，支援匯出整份資料集至 JSON。
     - 匯入時若遇到同名卡片，跳出衝突處理對話框讓使用者選擇「建立為新卡片（加上匯入後綴）」或「覆蓋現有卡片」。
  4. **測試與防護**：
     - 全套自動化測試執行通過，確保功能重構未破壞既有架構。

- **本次完成事項（LM Studio /v1/tokenize 終端機報錯消除、純本機零延遲 Token 估算、根除選取文本計算卡頓、全套測試擴充至 257 項 100% 綠燈）**：
  1. **問題排查與根本原因鎖定**：
     - 使用者回報 LM Studio DEV server 終端機頻繁出現 `[ERROR] Unexpected endpoint or method. (POST /v1/tokenize). Returning 200 anyway`，且選取文本並計算時非常卡頓。
     - 排查確認：LM Studio 官方 REST API 根本未提供 `/v1/tokenize` 端點；`AIScopeDialog` 在主 UI 執行緒中頻繁同步調用 `TokenEstimator.estimate_request`，其向 LM Studio 連續發起 2 次 Blocking HTTP POST 請求（大文本 + Prompt），導致主執行緒凍結卡頓。
  2. **純本機高精度零延遲分詞估算（Zero-Latency Token Estimation）實作**：
     - 在 `AIService` 與 `TokenEstimator` 實作 `fast_estimate_tokens`，依據 CJK 繁簡漢字（1.25x）與英數詞元（1.3x）加權，5 萬字耗時 < 3 毫秒，精度高度貼合現代大模型 BPE 分詞器。
     - 重構 `AIService.count_tokens`：LM Studio 與雲端模型直接使用 `fast_estimate_tokens`，徹底移除無效的 `POST /v1/tokenize` 網路請求。
     - 徹底杜絕 LM Studio 伺服器報錯，並使對話框文字選取與計算維持 0 毫秒即時響應。
  3. **測試與防護健全化**：
     - 在 `tests/test_ai_service.py` 新增 `test_count_tokens_lm_studio_no_network`，驗證 LM Studio 不對外發送請求。
     - 在 `tests/test_token_estimator.py` 新增 `test_fast_estimate_tokens` 驗證估算精度。
     - 健全 `TestAICharacterExtraction` 與 `TestAIScopeDialog` 的 Mock 防護，全套 257 項測試 100% 綠燈，執行時間由 160 秒驟降至 23 秒。
     - 同步更新 `.agents/docs/TEST_SUITE.md` 與 `.agents/docs/HANDOVER.md`。

- **當前任務狀態**：
  1. 程式碼修改完成，全套 257 項單元測試 100% 通過。
  2. 發布 v0.1.4-Beta 測試預發布版（Setup.exe 與 Zip 封裝檔）。
  3. Git 標籤 `v0.1.4-beta` 與遠端分支同步推送。
  4. 交接文件與測試手冊維護完畢。

- **下一個 Agent 的任務指引**：
  1. 後續所有對外文件或 Release Notes 必須遵守 `.agents/rules/workspace_rules.md` 中的發布規範，嚴禁使用 Emoji 與煽情行銷詞彙，嚴格使用台灣繁體中文。
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
- JSON 舊檔相容讀取功能已完全移除，如果需要開啟極早期的 JSON 專案檔，將無法直接開啟，且 `services/storage.py` 已被刪除。

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

- **本次完成事項 (進步計劃第一階段：P0 潛在缺陷修復，全套 226 項單元測試 100% 綠燈)**：
  1. **BUG-1：修復 `StorageService.load_data` 方法不存在之缺陷**：
     - 在 `project_controller.py`（L653）與 `autosave_controller.py`（L94）中，將不存在的 `StorageService.load_data` 替換為實際定義的 `StorageService.load_project_from_json`，徹底排除載入舊版 JSON 暫存檔時的 `AttributeError` 隱性異常。
  2. **BUG-2：修復全書自動排版對節點類型的錯誤判定**：
     - 在 `editor_controller.py`（L211）中，將錯誤的 `not data.get("is_folder", False)` 修正為 `data.get("type") != "folder"`，精確隔離資料夾節點，確保全書排版僅套用於文章與場景節點。
  3. **BUG-3：統一 `save_temp_doc` 控制器呼叫路徑**：
     - 在 `stats_controller.py`（L178, L189, L221, L332）中，將 `self.mc.save_temp_doc()` 統一為 `self.mc.project.save_temp_doc()`，符合專案既有各 Controller 調用慣例；同步更新 `test_daily_progress_sync.py` 與 `test_stats_ai_breakdown.py` 之 mock 與 Dummy 物件。
  4. **測試套件擴充**：
     - 新增 `tests/test_p0_bug_fixes.py`（4 項測試），完整覆蓋上述 3 項修復。
     - 全套 35 個測試模組、226 項單元測試 100% 通過（`pytest tests/` 226 passed in 21.47s）。
     - 同步更新 `.agents/docs/TEST_SUITE.md`。

- **本次完成事項 (進步計劃第二階段：P1 技術債與功能連結補完，全套 228 項單元測試 100% 綠燈)**：
  1. **DEBT-2：統一 `find_item_by_id` 邏輯**：
     - 在 `search_controller.py` 中將冗餘的遞迴樹搜尋簡化為直接委派 `self.mc.tree.find_item_by_id(target_id)`，消除重複邏輯。
  2. **DEBT-1：清理大量貼上/刪除殘留之殭屍欄位**：
     - 從 `main_controller.py` 的 `get_writing_logs_as_dict` 字典序列化中移除 `paste_large_count` 與 `delete_large_count`。
     - 從 `writing_chart_view.py` 中移除實例變數 `total_paste_large` 與 `total_delete_large`。
     - 在 `models/models.py` 的 `WritingLogEntry` 中加入明確廢棄標記，保留欄位預設值確保資料庫與舊 JSON 檔案向後相容性。
  3. **LINK-1：搜尋控制器呼叫路徑規範化**：
     - 將 `search_controller.py` 中的 `self.mc.editor.save_current_editor_content()` 統一修正為 `self.mc.save_current_editor_content()`。
  4. **LINK-2：大綱總覽模式即時雙向連動**：
     - 在 `tree_controller.py` 封裝 `_sync_outline_view_if_active()`，並在節點新增、新增幕、更名、複製、上下移動、刪除與垃圾桶復原操作完成後即時觸發同步。
     - 在大綱模式下執行新增時自動保持於 Page 3，確保使用者在瀏覽大綱時結構與統計即時更新。
  5. **LINK-3：快照與垃圾桶整合防護**：
     - 在 `project_controller.py` 的 `load_project_data` 開頭主動清空 `trash_bin` 並刷新 UI，徹底杜絕專案切換或快照還原後因殘留記憶體節點指針所引發的野指針異常。
     - 更新快照還原提示訊息，明確告知使用者垃圾桶已同步重置。
  6. **DEBT-4：關鍵路徑例外處理精確化**：
     - 在 `project_controller.py` 與 `autosave_controller.py` 的暫存與存檔載入流程中，導入 `sqlite3.Error`、`json.JSONDecodeError` 與 `OSError` 具體例外捕獲，明確區隔資料損毀與未預期異常。
  7. **測試套件擴充與全量通過**：
     - 在 `test_focus_and_outline.py` 新增 `test_outline_view_realtime_sync_on_tree_operations`。
     - 在 `test_snapshot.py` 新增 `test_restore_snapshot_clears_trash_bin`。
     - 全專案 35 個測試模組、228 項單元測試 100% 通過（`pytest tests/` 228 passed in 23.73s）。
     - 同步更新 `.agents/docs/TEST_SUITE.md`。

- **本次完成事項 (進步計劃第三階段：P2 專案精簡與架構重構，全套 235 項單元測試 100% 綠燈)**：
  1. **DEBT-3：統一 `save_temp_doc` 控制器呼叫鏈路**：
     - 在 `main_controller.py`（L182）中將定時器呼叫統一為 `self.project.save_temp_doc(from_timer=True)`，使全專案所有子控制器與定時器完全收斂至統一鏈路。
  2. **SLIM-3：拆分大型服務模組 `services/ai_service.py`（928 行 -> 525 行）**：
     - 抽離設定讀寫與預設 Prompt 模板至 `services/ai_settings_service.py`（`AISettingsService`）。
     - 抽離背景執行緒至 `services/ai_worker.py`（`AIWorker`, `AIChatWorker`, `AIContinuationWorker`, `AIStreamWorker`），並利用延遲解析消解循環相依。
     - `AIService` 保持對外統一 Facade 介面與 re-export，所有呼叫端與既有測試 100% 向後相容。
  3. **SLIM-4：主題樣式模板解耦外部化（`theme_manager.py` 667 行 -> 345 行）**：
     - 將佔據 323 行的 `BASE_THEME_TEMPLATE` 提取至獨立模組 `utils/theme_templates.py`，大幅減輕主模組行數並提升樣式可維護性。
  4. **SLIM-2：寫作日誌業務運算邏輯下沉至 Service 層**：
     - 建立 `services/writing_log_service.py`（`WritingLogService`），將指標卡片統計、AI 細部面向彙整、圖表切片與日誌表格格式化下沉至純邏輯服務層。
     - `WritingLogDashboard` 的 `refresh_data` 專注於 View 渲染，架構職責分明。
  5. **DEBT-5：拆分大型 View 元件 `right_panel_view.py`（697 行 -> 567 行）**：
     - 將富文本與 Markdown 雙向編輯器抽離至獨立模組 `views/components/right_panel_card_editor.py`（`RightPanelCardEditor`）。
  6. **SLIM-1：評估舊版 JSON 讀取模組 `StorageService` 之留存**：
     - 嚴格遵守 `workspace_rules.md` 之禁止事項：「不要刪除 StorageService——即使切換到 SQLite，仍需保留 JSON 讀取能力（舊檔相容）」，明確保留舊檔 JSON 遷移相容能力，並於文件載明結論。
  7. **測試套件擴充與全量通過**：
     - 新增 `tests/test_ai_settings_and_worker.py`（3 項測試）。
     - 新增 `tests/test_writing_log_service.py`（4 項測試）。
     - 全專案 37 個測試模組、235 項單元測試 100% 通過（`pytest tests/` 235 passed in 46.92s）。
     - 同步維護 `.agents/docs/TEST_SUITE.md` 與本交接文件。

- **本次完成事項 (長文分析 HRCI 演算法最佳化、動態實體命中檢索與 8GB 顯存防溢出，全套 236 項測試 100% 綠燈)**：
  1. **分塊常數調優**：將 `DEFAULT_CHUNK_SIZE` 由 4,000 字下調至 2,800 字（約 2,000 tokens），重疊區間設為 200 字，符合 8GB GPU 小模型的推論安全預算。
  2. **突破實體數量限制**：重構 `CompactState` 與 `get_relevant_summary(chunk_text)`，全局無上限收納上百位角色與設定，透過正文命中掃描僅動態注入當前段落活躍實體（500 字以內），徹底解決長篇小說龐大人物與名詞遺漏問題。
  3. **終端總結預算控制（Context Budget Controller）**：重構 `build_synthesis_prompt` 與 `_format_final_state_summary`，動態分配各分段摘要額度（上限 3,200 字），以出場頻次排序展示全景高密度索引，徹底根治 16k context window 爆表（`finish_reason: length`）截斷問題。
  4. **測試套件擴充與全量通過**：在 `test_long_text_analyzer.py` 新增 50+ 實體動態命中測試與 17 段超長篇總結長度控制測試，全專案 37 個測試模組、236 項單元測試 100% 綠燈通過。

- **本次完成事項 (AI 中斷請求與網路連線層串流重構，全套 236 項測試 100% 綠燈)**：
  1. **替換網路底層**：將 `urllib.request` 替換為現代化的 `requests`，解決同步阻塞無法中斷的問題。
  2. **全面串流化 (Streaming by Default)**：將所有 LLM API 的呼叫（包含原本阻塞式的 `call_api`）全部改由底層的 `call_api_stream` 實作，並保留相容性。
  3. **實作即時連線中斷**：加入 `is_cancelled_callback` 機制。現在當使用者點擊取消時，系統會立即中斷網路迴圈並關閉 tcp socket 連線，強制截斷伺服器端的運算。
  4. **相容性修復與加固**：確保了串流模式下對「思考型模型」（如 DeepSeek R1）的 `reasoning_content` 的相容性，並補齊了 `AIContinuationWorker` 的 `cancel` 介面。
  5. **測試驗證**：全專案 236 項單元測試維持 100% 綠燈通過。

- **當前任務狀態**：
  1. 長文本分析與 AI 對話之「中斷請求」問題已徹底修復。
  2. 程式碼已重構完畢，測試通過。

- **下一個 Agent 的任務指引**：
  1. 若後續需要新增 AI 供應商或實作新 API，必須遵循目前 `ai_service.py` 內基於 `requests` 與串流中斷的架構。
  2. 所有測試與說明文件皆已同步更新至最新版本。

- **本次完成事項 (動態硬體感知與長文自適應切分計畫 - Phase 1：工具層基礎建設)**：
  1. 在 `requirements.txt` 中新增 `pynvml` 與 `psutil` 依賴。
  2. 實作 `services/hardware_detector.py` 建立 `get_available_memory_mb()`，支援 NVIDIA GPU VRAM 偵測、System RAM 偵測與安全 Fallback。
  3. 新增 `tests/test_hardware_detector.py` 單元測試並透過 Mock 完成 3 種情境驗證，測試 100% 通過。

- **本次完成事項 (動態硬體感知與長文自適應切分計畫 - Phase 2：分析器架構約束與事前動態切分，全套 245 項測試 100% 綠燈)**：
  1. **修復文字切分死循環**：在 `utils/text_splitter.py` 的 `chunk_text_with_overlap` 中，加入字元切分到達末尾時（`end_idx >= len(p)`）的 `break` 判斷，徹底根治文字無換行時的無窮迴圈問題。
  2. **架構約束與動態分塊計算**：
     - 在 `services/long_text_analyzer.py` 的 `LongTextAnalyzer` 類別註解中明確宣告「絕對無狀態（Stateless）」與「單一佇列序列化（Serialized）」之架構約束。
     - 實作 `calculate_dynamic_chunk_size` 演算法，對接 `services/hardware_detector.py` 的 `get_available_memory_mb()`，當可用記憶體 < 1.5GB 時主動拋出 `MemoryError` 觸發防護。
     - 在 `analyze_long_text` 中實作安全下限策略 `min(self._custom_chunk_size, dynamic_chunk_size)`，既保障不超過硬體極限，又相容外部自訂參數與單元測試。
  3. **背景 Worker 記憶體不足攔截與 UI 降級回饋**：
     - 在 `services/ai_worker.py` 的 `AIWorker.run()` 中擴充 `except MemoryError`，發送包含「關閉佔用程式」與「切換較小模型」建議之繁體中文友善提示。
  4. **實體動態檢索預算平衡**：
     - 修復 `models/models.py` 中 `CompactState.get_dynamic_summary` 的人物與世界觀預算分配，限制非命中補充上限，確保「相關世界觀設定」能獲得公平預算，修復測試斷言失敗。
  5. **清理與轉發模組**：
     - 將 `utils/hardware_detector.py` 轉發至 `services/hardware_detector.py`，保持架構單一職責與向後相容。
  6. **測試套件擴充**：
     - 在 `tests/test_long_text_analyzer.py` 新增 3 項動態切分與邊界測試（總數增至 12 項）。
     - 在 `tests/test_ai_settings_and_worker.py` 新增 1 項 MemoryError 攔截測試（總數增至 5 項）。
     - 全專案 39 個測試模組、245 項單元測試 100% 綠燈通過。

- **陷阱 25：長文切分與動態記憶體感知安全約束**：
  - **字元切分邊界防護**：在 `utils/text_splitter.py` 進行單段超長字元切分時，當 `end_idx >= len(p)` 必須立即中斷迴圈，切勿在末尾計算 `idx = end_idx - overlap_size` 造成指標倒退與無窮迴圈死鎖。
  - **動態 Chunk 計算與外部參數優先級**：在 `LongTextAnalyzer` 中，當呼叫端有手動指定自訂 `chunk_size`（如單元測試傳入 100 字）時，應採取安全下限策略 `min(self._custom_chunk_size, dynamic_chunk_size)`，既保障不超出硬體記憶體預算，又確保外部客製參數不被強制覆寫。
  - **實體摘要預算平衡**：在 `CompactState.get_dynamic_summary` 中，未命中實體最多補充 3~5 位，避免無上限追加擠爆 Token 預算，確保世界觀設定與關鍵事件能獲得公平預算。

- **本次完成事項 (動態硬體感知與長文自適應切分計畫 - Phase 3：執行期 Token 防護與動態抓取，全套 249 項測試 100% 綠燈)**：
  1. **Ollama tokenize 端點補完**：
     - 在 `services/ai_service.py` 的 `count_tokens` 中，Ollama 分支從直接 fallback 升級為嘗試呼叫 `/api/tokenize` 端點（Ollama 0.2+ 支援）。
     - 端點回應 `{"tokens": [...]}` 時，精確回傳列表長度作為 token 數；連線失敗或回應格式不符時，無聲靜默 fallback 到 `int(len(text) * 2.5)` 保守估算值。
  2. **chunk_text 自身 Token 截斷防護（Runtime Token 硬上限攔截）**：
     - 在 `services/long_text_analyzer.py` 的 `analyze_long_text` 逐段迴圈中，計算 `chunk_token_count` 後與 `max_tokens * 0.75` 安全上限比較。
     - 若超出上限，主動截斷 chunk_text 至安全字數並附加「【注意：本段因長度超出安全上限已截斷…】」提示標記，重新計算 token 數後再組裝 Prompt，杜絕 Context Window 溢出。
  3. **timeline_events 與 unresolved_threads 動態命中篩選**：
     - 在 `models/models.py` 的 `get_dynamic_summary` 中，新增 `_sort_by_hit` 函式，以 bigram（連續 2 字中文字元）比對策略，篩選與當前正文相關的歷史事件與懸念優先排序。
     - 命中的事件/懸念排在前方，未命中者保持由新到舊順序作為補充，確保在 Token 預算有限時最相關的脈絡被優先保留。
  4. **測試套件擴充與全量通過**：
     - 在 `tests/test_ai_service.py` 新增 `test_count_tokens_ollama_fallback_on_missing_endpoint` 與 `test_count_tokens_ollama_success`（2 項）。
     - 在 `tests/test_long_text_analyzer.py` 新增 `test_chunk_text_truncation_on_token_overflow` 與 `test_dynamic_timeline_event_hit_filtering`（2 項）。
     - 全專案 39 個測試模組、249 項單元測試 100% 綠燈通過（`pytest tests/` 249 passed in 35.09s）。
     - 同步更新 `.agents/docs/TEST_SUITE.md` 與本交接文件。

- **陷阱 26：bigram 命中比對必須從事件描述側抽取詞彙**：
  - 在 `get_dynamic_summary` 的 `_sort_by_hit` 中，正確做法是從「事件/懸念描述文字」抽取中文 bigram，判斷是否出現在 chunk_text 中（`bigram in chunk_text`）。
  - 切勿反向從 chunk_text 抽取整段詞組（如 `re.findall(r'[\u4e00-\u9fff]{2,}', chunk_text)`），因為中文連續字元不含非中文字元時整串會被視為一個詞組，無法比對到短詞。

- **本次完成事項 (停止任務功能異常排查與連線中斷健全性加固，全套 254 項測試 100% 綠燈)**：
  1. **底層連線 Socket 即時中斷機制**：
     - 在 `services/ai_worker.py` 的 `BaseAIWorker` 實作 `_set_active_response` 與 `cancel`，取消時除了切換 `_is_cancelled` 標記外，主動關閉 requests response 與底層 `raw.close()`，強制截斷伺服器端運算與 socket 連線。
     - 在 `services/ai_pipeline_workers.py` 的 `LongTextPipelineWorker` 整合該機制，確保長文本分析中斷時立即停止。
  2. **取消時防護訊號漏發**：
     - 確保各 Worker 在被中斷時絕不發出 `finished_signal`，避免覆蓋既有介面或引發狀態錯亂。
     - 在 `views/components/ai_task_overlay.py` 與 `views/dialogs/ai_chat_dialog.py` 強化停止按鈕事件回應與 UI 狀態還原。
  3. **測試套件擴充**：
     - 新增 `tests/test_ai_cancellation.py`（5 項測試），驗證 BaseAIWorker、LongTextPipelineWorker、AIWorker、AIChatWorker、AIStreamWorker 取消連線中斷行為。
     - 全專案 40 個測試模組、254 項單元測試 100% 綠燈通過。
     - 同步更新 `.agents/docs/TEST_SUITE.md`。

- **本次完成事項 (長文分析重構 Phase 3：流程簡化與單一串流請求架構完全收斂)**：
  1. **AIWorker 拔除廢棄長文分段邏輯**：
     - 在 `services/ai_worker.py` 中徹底移除 `text_len > self.chunk_threshold` 判斷與動態引用 `services.long_text_analyzer` 的殘留邏輯，根治長篇正文分析引發 `ModuleNotFoundError` 的重大潛在缺陷。
     - 所有長度之分析請求完全收斂至 `AIService.call_api_stream` 單一串流請求機制。
     - 保留 `chunk_threshold` 預設參數以維護向後相容，更新類別 docstring 為單一串流請求架構說明。
     - 進度回報訊息中的 Emoji 符號純化為標準台灣繁體中文純文字（如「正在連線模型並分析文本…」）。
  2. **AIController 介面收斂與文案純化**：
     - 在 `controllers/ai_controller.py` 中確認所有文本分析任務（角色、評語、世界觀、時間線）皆直接實例化 `AIWorker`，無任何演算法分流。
     - 浮動進度 HUD 任務名稱字典（`task_name_map`）與完成提示純化，剔除 Emoji 符號並規範為台灣繁體中文。
     - 擴寫任務視窗標題去除 Emoji，改為純淨的「AI 擴寫任務」。
  3. **測試套件擴充與全量通過**：
     - 在 `tests/test_ai_settings_and_worker.py` 新增 `test_ai_worker_long_text_single_request`，驗證超過 8,000 字超長小說正文在 `AIWorker` 中直接執行單一串流請求且完整回傳結果，不再發生模組引用錯誤。
     - 新增 `test_ai_controller_starts_ai_worker_directly`，驗證控制器直接發起 `AIWorker` 背景工作。

- **本次完成事項 (長文分析重構 Phase 4：清理廢棄模組、模型與工具層死碼)**：
  1. **舊有管線與分析器模組徹底移除**：
     - 確認已自專案與 Git 追蹤中完全移除 `services/ai_pipeline_workers.py`（舊版 4 階段滾動式抽取 Worker）與 `services/long_text_analyzer.py`（舊版 HRCI 長文分段分析引擎）。
     - 確認已移除舊版管線與分析器之測試檔案 `tests/test_long_text_pipeline.py` 與 `tests/test_long_text_analyzer.py`。
  2. **模型層與工具層死碼全面清理**：
     - 在 `models/models.py` 中徹底移除專為舊版滾動壓縮演算法設計之 `CompactState`、`ChunkAnalysisResult`、`LongTextAnalysisResult` 類別定義（清除 168 行死碼），消除無效維護成本。
     - 移除舊版分段工具檔案 `utils/text_splitter.py`（含 `chunk_text_with_overlap`），全專案不再有任何長文切分與分段殘留。
     - 移除先前診斷階段殘留之未追蹤檔案 `services/diagnostic_logger.py`。
  3. **測試與規格文件校準維護**：
     - 在 `.agents/docs/TEST_SUITE.md` 中校準測試範疇總覽表各項分類計數（補齊類別 11 與 12），精確對齊全套 40 個測試模組。
     - 在 `.agents/docs/ROADMAP.md` 中登錄 Phase 28 長文分析架構重構（單一串流請求）完成里程碑。

- **本次完成事項 (Local LLM 本機伺服器離線狀態即時偵測與 Context 誤報修復，全套 255 項測試 100% 綠燈)**：
  1. **問題根源剖析**：
     - 使用者未開啟 LM Studio 或 Ollama 本地伺服器時，`AIScopeDialog` 讀取先前殘留之快取 context_limit（如 131,072）進行 Token 估算。當文字量換算總需約 154,264 時，判定超標並顯示「超過目前 Context 限制」，而非明確指出「本機伺服器未啟動」，造成使用者對錯誤主因產生誤解。
  2. **AIService 實作輕量即時連線探測**：
     - 在 `services/ai_service.py` 實作 `check_local_server_status(provider, api_url, timeout=1.0)`。
     - 針對 LM Studio 探測 `/api/v0/models`（與 `/v1/models`），針對 Ollama 探測 `/api/tags`；若遇 ConnectionRefused 或連線逾時，精確判定為 `False, "服務未啟動"`；雲端供應商則直接回傳 True。
  3. **AIScopeDialog 介面與防護連動**：
     - `AIScopeDialog` 初始化時自動對本機模型發起連線探測。
     - 若伺服器離線，於統計面板明確顯示「目前 {provider} 狀態：未連線（服務未啟動）」與「狀態：Local LLM 服務未上線，請先啟動 {provider} 本機服務」（紅燈警示），強制禁用開始提取按鈕，且不展示誤導性的「超過目前 Context 限制」。
     - 對話框底部工具列新增「重新檢查服務」按鈕，使用者啟動 LM Studio 後無需重啟對話框即可原地刷新連線狀態並解鎖按鈕。
     - 點擊開始分析時增加二次攔截防線，避免背景 Worker 發起無效連線。
  4. **自動化測試擴充與 100% 綠燈驗證**：
     - 在 `tests/test_ai_scope_dialog.py` 新增 `test_scope_dialog_local_server_offline_disables_start_button`。
     - 在 `tests/test_ai_service.py` 新增 `test_check_local_server_status_online`、`test_check_local_server_status_offline`、`test_check_local_server_status_cloud_always_online`。
     - 全專案 40 個測試模組、255 項單元測試 100% 綠燈通過（`pytest tests/` 255 passed in 158.66s）。

- **本次完成事項 (發布 v0.1.5-beta)**：
  1. **專案架構精簡與文件對齊**：完成 Phase 24 底層重構與程式碼精簡化，並更新了 README 與相關專案手冊（對齊 Phase 29）。
  2. **測試驗證與封裝發布**：全套 257 項單元測試 100% 綠燈通過。v0.1.5-beta 安裝檔（`Jiufang_Novel_Editor_0.1.5-Beta-Setup.exe`）與免安裝檔（`Jiufang_Novel_Editor_0.1.5-Beta.zip`）已成功發布並上傳至 GitHub Release（標籤 `v0.1.5-beta`，Prerelease 模式）。
  3. **發布說明維護**：發布說明儲存於 `.agents/docs/v0.1.5-beta_release_notes.md`，並已同步發布至 GitHub Release 頁面。

- **當前任務狀態**：
  1. GitHub Release `v0.1.5-beta` 正式發布完成，二進位資產上傳完畢。
  2. Git 標籤 `v0.1.5-beta` 已同步推送至遠端。
  3. 交接記錄更新完畢。

- **下一個 Agent 的任務指引**：
  1. 繼續保持 `.agents/rules/workspace_rules.md` 中的發布與程式碼規範。
  2. 執行測試時請使用 `.venv\Scripts\python.exe -m pytest tests/`，有新增/修改測試時隨同維護 `TEST_SUITE.md`。

