# 九方小說編輯器 — 更新與修改歷史 (Changelog)

## 歷史紀錄 1
設定資料集匯出精靈與閱讀檔格式化排版
- **實作 `DatasetExportDialog` 匯出精靈**：
  在 `views/dialogs/dataset_export_dialog.py` 實作資料集專屬匯出對話框，繼承 `BaseDialog` 並支援主題自適應、高對比度核取方塊。作家可透過樹狀結構勾選特定分類與卡片（支援全選/全不選與父子連動），並自由選擇匯出為「Word 閱讀檔 (*.docx)」、「Markdown 閱讀檔 (*.md)」或「九方備份檔 (*.json)」。
- **實作 `DatasetFormatter` 與動態標題降級機制**：
  在 `utils/dataset_formatter.py` 實作結構化文字產生器。針對作家建立的多層卡片結構，前三層依序轉為 Markdown 標題（H1 分類、H2 頂層卡片、H3 子卡片）；第四層及更深層（Depth >= 4）自動觸發動態降級，轉為帶有階層麵包屑路徑的清單項目（`* **[母層 > 子層] 卡片名稱**`）與引言縮排區塊，徹底避免過深 Heading 破壞大綱結構與文書排版。
- **重構 `CardController.export_dataset`**：
  整合匯出精靈與過濾邏輯，支援過濾後卡片資料匯出為 JSON 備份檔、Markdown 檔案或透過既有 `MarkdownConverter` 轉為排版優雅的 Word (.docx) 文件。
- **選單區分與快速鍵整合**：
  在 `views/components/menu_builder.py` 將原有的「匯出(&E)...」明確更名為「匯出小說文本(&E)...」（快捷鍵 Ctrl+E），並新增「匯出設定資料集(&D)...」（快捷鍵 Ctrl+Shift+E），徹底消除使用者對於小說內文與設定資料集匯出的混淆。
- **單元測試建立與綠燈驗證**：
  新增 `tests/unit/test_dataset_export.py`（4 項測試），測試覆蓋 5 層深層降級、勾選過濾、Docx 渲染與選單動作綁定，全套 260 項測試維持 100% 綠燈。

## 歷史紀錄 2
UI 介面清理與精簡
- **移除右側面板已過時的卡片預覽按鈕**：
  由於編輯器已全面導入富文本所見即所得，原有的「📖 預覽 / 📝 編輯」切換按鈕、QTextEdit HTML 預覽視窗與相關切換邏輯已失去作用。因此將其從 `views/components/right_panel_view.py` 中徹底移除，精簡了介面元件並減少狀態維護成本。同步移除了 `test_right_panel_split.py` 中的相關測試，確保測試套件維持 100% 綠燈。

## 歷史紀錄 3
排版工具與渲染修復
- **修復 Qt HTML 引擎剔除段首全形空白的問題**：
  在 `utils/markdown_utils.py` 的 `render_markdown_inline` 函式中，透過正則表達式將全形空白（`\u3000`）使用 `<span style="white-space:pre">` 包裹。此舉成功防止 Qt 的 `setHtml` 引擎在渲染 `<p>` 標籤時自動剔除段首全形空白，徹底解決了使用者切換章節後排版效果（縮排）消失的 BUG。

## 歷史紀錄 4
程式碼架構瘦身與精簡重構
- **完全棄用舊版 JSON 格式存檔**：
  移除了 `project_controller.py` 中龐大且不再被呼叫的 `_migrate_legacy_dict_to_jne_project` 與多餘的 JSON 相關邏輯，專案全面強制使用 SQLite。
- **外部化 AI Prompt 模板**：
  建立 `resources/prompts/` 將角色、印象、世界觀、時間線、延續寫作等 6 大 Prompt 從 `services/ai_settings_service.py` 剝離成純文字檔，降低核心程式碼負載。
- **共用 UI 元件 `BaseDialog` 提取**：
  新增 `views/common/base_dialog.py`，全數封裝 `ThemeManager.apply_theme_to_dialog(self)` 與 `self.scale_factor` 等邏輯，並成功重構 `views/dialogs/` 下的 22 個 `QDialog` 類別，大幅削減重複樣板程式碼。
- **測試套件架構分層**：
  將 `tests/` 底下 40 個測試檔重構至 `tests/unit/`、`tests/integration/`、`tests/ui/`，並修正所有 `sys.path` 問題，257 項測試維持 100% 綠燈。

## 歷史紀錄 5
實作全系列 AI 功能的滾動式抽取演算法
- **實作 `LongTextPipelineWorker`**：
  在 `services/ai_pipeline_workers.py` 實作了 4 階段滾動式抽取演算法（分段、預掃描、滾動抽取、收尾）。此 Worker 動態支援 `"character", "impression", "world", "timeline"` 等不同任務類型的 JSON diff 抽取，並最終轉換成卡片相容格式。
- **整合 `AIController` 與 `AIScopeDialog`**：
  將所有分析任務與 `AIScopeDialog` 綁定。現在包含文學評語、世界觀、時間線梳理等功能，在啟動前皆可選擇範圍與切換「前沿大模型 / 本地小模型」。
- **工具建立**：
  在 `utils/text_splitter.py` 建立了 `chunk_text_with_overlap` 函式，專司處理長篇文字的分段，支援 overlap 控制以防脈絡截斷。通過。

## 歷史紀錄 6
**本次完成事項（編輯器底層重構統一、雙重貼上模式與資料集匯入匯出）**：
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

## 歷史紀錄 7
**本次完成事項（LM Studio /v1/tokenize 終端機報錯消除、純本機零延遲 Token 估算、根除選取文本計算卡頓、全套測試擴充至 257 項 100% 綠燈）**：
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

## 歷史紀錄 8
**本次完成事項 (Phase 25：AI 誠信光譜指標精準化與創作日誌全域 UI 縮放自適應，全套 193 項單元測試 100% 綠燈)**：
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

## 歷史紀錄 9
**本次完成事項 (進步計劃第一階段：P0 潛在缺陷修復，全套 226 項單元測試 100% 綠燈)**：
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

## 歷史紀錄 10
**本次完成事項 (進步計劃第二階段：P1 技術債與功能連結補完，全套 228 項單元測試 100% 綠燈)**：
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

## 歷史紀錄 11
**本次完成事項 (進步計劃第三階段：P2 專案精簡與架構重構，全套 235 項單元測試 100% 綠燈)**：
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

## 歷史紀錄 12
**本次完成事項 (長文分析 HRCI 演算法最佳化、動態實體命中檢索與 8GB 顯存防溢出，全套 236 項測試 100% 綠燈)**：
1. **分塊常數調優**：將 `DEFAULT_CHUNK_SIZE` 由 4,000 字下調至 2,800 字（約 2,000 tokens），重疊區間設為 200 字，符合 8GB GPU 小模型的推論安全預算。
  2. **突破實體數量限制**：重構 `CompactState` 與 `get_relevant_summary(chunk_text)`，全局無上限收納上百位角色與設定，透過正文命中掃描僅動態注入當前段落活躍實體（500 字以內），徹底解決長篇小說龐大人物與名詞遺漏問題。
  3. **終端總結預算控制（Context Budget Controller）**：重構 `build_synthesis_prompt` 與 `_format_final_state_summary`，動態分配各分段摘要額度（上限 3,200 字），以出場頻次排序展示全景高密度索引，徹底根治 16k context window 爆表（`finish_reason: length`）截斷問題。
  4. **測試套件擴充與全量通過**：在 `test_long_text_analyzer.py` 新增 50+ 實體動態命中測試與 17 段超長篇總結長度控制測試，全專案 37 個測試模組、236 項單元測試 100% 綠燈通過。

## 歷史紀錄 13
**本次完成事項 (AI 中斷請求與網路連線層串流重構，全套 236 項測試 100% 綠燈)**：
1. **替換網路底層**：將 `urllib.request` 替換為現代化的 `requests`，解決同步阻塞無法中斷的問題。
  2. **全面串流化 (Streaming by Default)**：將所有 LLM API 的呼叫（包含原本阻塞式的 `call_api`）全部改由底層的 `call_api_stream` 實作，並保留相容性。
  3. **實作即時連線中斷**：加入 `is_cancelled_callback` 機制。現在當使用者點擊取消時，系統會立即中斷網路迴圈並關閉 tcp socket 連線，強制截斷伺服器端的運算。
  4. **相容性修復與加固**：確保了串流模式下對「思考型模型」（如 DeepSeek R1）的 `reasoning_content` 的相容性，並補齊了 `AIContinuationWorker` 的 `cancel` 介面。
  5. **測試驗證**：全專案 236 項單元測試維持 100% 綠燈通過。

## 歷史紀錄 14
**本次完成事項 (動態硬體感知與長文自適應切分計畫 - Phase 1：工具層基礎建設)**：
1. 在 `requirements.txt` 中新增 `pynvml` 與 `psutil` 依賴。
  2. 實作 `services/hardware_detector.py` 建立 `get_available_memory_mb()`，支援 NVIDIA GPU VRAM 偵測、System RAM 偵測與安全 Fallback。
  3. 新增 `tests/test_hardware_detector.py` 單元測試並透過 Mock 完成 3 種情境驗證，測試 100% 通過。

## 歷史紀錄 15
**本次完成事項 (動態硬體感知與長文自適應切分計畫 - Phase 2：分析器架構約束與事前動態切分，全套 245 項測試 100% 綠燈)**：
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

## 歷史紀錄 16
**本次完成事項 (動態硬體感知與長文自適應切分計畫 - Phase 3：執行期 Token 防護與動態抓取，全套 249 項測試 100% 綠燈)**：
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

## 歷史紀錄 17
**本次完成事項 (停止任務功能異常排查與連線中斷健全性加固，全套 254 項測試 100% 綠燈)**：
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

## 歷史紀錄 18
**本次完成事項 (長文分析重構 Phase 3：流程簡化與單一串流請求架構完全收斂)**：
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

## 歷史紀錄 19
**本次完成事項 (長文分析重構 Phase 4：清理廢棄模組、模型與工具層死碼)**：
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

## 歷史紀錄 20
**本次完成事項 (Local LLM 本機伺服器離線狀態即時偵測與 Context 誤報修復，全套 255 項測試 100% 綠燈)**：
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

## 歷史紀錄 21
**本次完成事項 (資料集卡片 UI 最佳化：移除手動儲存，改為自動儲存，全套 257 項測試 100% 綠燈)**：
1. **UI 簡化**：移除右側資料集面板中的「儲存卡片變更」按鈕，避免使用者在未手動儲存即切換卡片時遺失內容。
  2. **自動儲存實作**：在 `views/components/right_panel_view.py` 中，將 `card_title_edit` 與 `card_content_edit` 的 `textChanged` 訊號直接連結至儲存邏輯，實現「邊打邊存」的即時同步。
  3. **防禦機制**：在 `show_card_detail` 載入內容時加入 `blockSignals(True)` 防護，避免程式更改文字時觸發多餘的儲存訊號。
  4. **修復工具列崩潰 Bug**：實作了 `BaseRichTextEdit` 遺漏的 `toggle_line_prefix` 方法，徹底修復在卡片編輯器點擊「標題 (H)」與「清單項目 (•)」按鈕時導致的 Crash 問題，並支援多行選取一次性切換前綴。
  5. **寫作日誌邏輯對齊 (NET 字數)**：將 `stats_controller.py` 中背景紀錄並寫入資料庫 `writing_logs` 的字數演算法，從「毛字數 (Gross, 僅累加不扣除)」修改為「淨字數 (Net)」。現在當天存入資料庫的進度會強制對齊 UI 的 `today_written_count`，徹底解決崩潰或重啟後，讀取到的「今日進度」大於「專案總進度」的資料不一致問題。
  6. **測試與防護**：更新相關單元測試，確保全套 257 項單元測試 100% 綠燈。

## 歷史紀錄 22
**本次完成事項 (發布 v0.1.6-beta)**：
1. **資料集卡片自動儲存與崩潰修復**：
     - 右側面板卡片編輯實現即時自動儲存（Auto-save），移除手動儲存按鈕並加強載入訊號阻斷。
     - 補齊 `BaseRichTextEdit.toggle_line_prefix`，修復工具列標題與清單按鈕崩潰問題。
     - 寫作日誌字數計算對齊主介面淨字數（Net Word Count），消除重啟前後數據不一致。
  2. **測試驗證與封裝發布**：
     - 全套 40 個模組、257 項單元與整合測試 100% 綠燈通過（耗時 22 秒）。
     - v0.1.6-beta 安裝檔（`Jiufang_Novel_Editor_0.1.6-Beta-Setup.exe`）與免安裝檔（`Jiufang_Novel_Editor_0.1.6-Beta.zip`）收納於 `pre-release/` 資料夾並發布。
  3. **發布說明維護**：
     - 依據同儕創作者視角、禁止 Emoji 與台灣繁體中文規範撰寫發布說明，儲存於 `.agents/docs/v0.1.6-beta_release_notes.md`。

## 歷史紀錄 23
**本次完成事項 (設定資料集匯出精靈實作，全套 260 項測試 100% 綠燈)**：
1. **介面選單**：更名「匯出小說文本(&E)...」(Ctrl+E)，新增「匯出設定資料集(&D)...」(Ctrl+Shift+E)。
  2. **精靈對話框**：實作 `DatasetExportDialog`，具備分類與卡片核取樹狀圖、全選/全不選、以及 Word / Markdown / JSON 三種格式切換。
  3. **排版格式化**：實作 `DatasetFormatter`，支援動態標題降級與麵包屑階層標記，整合至 `CardController.export_dataset`。
  4. **自動化測試與文件**：新增 `tests/unit/test_dataset_export.py`（4 項測試），全套 260 項單元與整合測試 100% 綠燈通過，同步更新 `TEST_SUITE.md` 與 `HANDOVER.md`。

