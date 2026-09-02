# 九方小說編輯器 — 自動測試套件說明書 (Test Suite)

> **最後更新**：2026-09-03  
> **測試總數**：154 項自動化測試（26 個測試模組）  
> **重要規則**：任何 Agent 在新增、修改或刪除測試案例時，**必須同步更新本文件**！

---

## 1. 測試執行指引

在 Windows 繁體中文環境下，執行測試請指定 `tests/` 目錄，避免根目錄其他文字檔案干擾 pytest collection：

```powershell
# 執行全部 154 項測試
C:\Python314\python.exe -m pytest tests/

# 僅檢驗測試收集清單（不實際執行）
C:\Python314\python.exe -m pytest tests/ --collect-only -q

# 執行單一測試檔案
C:\Python314\python.exe -m pytest tests/test_daily_progress_sync.py

# 執行特定關鍵字測試
C:\Python314\python.exe -m pytest tests/ -k "test_scene"
```

---

## 2. 測試範疇總覽架構

| 分類領域 | 測試模組檔名 | 測試數 | 核心測試目標 |
| :--- | :--- | :---: | :--- |
| **1. AI 輔助與長文本分析** | `test_ai_character_extraction.py`<br>`test_ai_chat.py`<br>`test_ai_continuation.py`<br>`test_ai_service.py`<br>`test_long_text_analyzer.py` | 23 | 結構化角色提取、LaTeX 清理、章節內文提取、AI 聊天面板、智慧續寫、長文本滑動視窗分析與中斷機制 |
| **2. 編輯器與右側資料卡片** | `test_controllers.py`<br>`test_right_panel_split.py`<br>`test_card_detail_dialog.py` | 23 | 9 大子控制器協同、右側雙層上下分離面板、卡片更名即時連動、卡片 Markdown 所見即所得與預覽、純文字無格式貼上 |
| **3. 章節樹與三層結構（幕）** | `test_context_menus.py`<br>`test_scene.py` | 18 | 節點右鍵操作（排序/更名/複製副本/整卷複製/標記）、第三層「幕 (Scene)」節點資料結構與 metadata（時間/地點/POV）持久化相容 |
| **4. 資料庫、備份與路徑移轉** | `test_database.py`<br>`test_daily_progress_sync.py`<br>`test_backup.py`<br>`test_snapshot.py`<br>`test_tree_expansion_persistence.py`<br>`test_storage_path.py` | 25 | SQLite 存取、當日目標與進度多設備同步 (v10 Migration)、自動備份與還原、多版本快照建立與恢復、樹狀展開狀態持久化、自訂存檔目錄遷移與安全驗證 |
| **5. 自動存檔與崩潰恢復** | `test_autosave_and_startup.py` | 9 | 啟動導引視窗（新建/開啟/最新）、異常退出崩潰自動恢復（Crash Recovery）、暫存檔配額清理與自動存檔週期 |
| **6. 審校、統計與寫作日誌** | `test_phase12.py`<br>`test_stats_settings.py` | 17 | 中文小說排版審校（重複詞/高頻虛詞/被動句/公文贅詞）、自訂詞庫與白名單、寫作日誌 AI 介入度追蹤、全書字數目標進度條 |
| **7. 視窗設定、大綱與匯出** | `test_window_settings.py`<br>`test_focus_and_outline.py`<br>`test_markdown_converter.py`<br>`test_export.py`<br>`test_search.py` | 29 | 初次啟動縮放導引、1:2:2 版面記憶、沉浸全螢幕專注模式、大綱即時檢索、全域搜尋取代、多格式匯出 (Docx/EPUB/MD/TXT) |
| **8. 主題樣式與對話框色彩** | `test_theme_dialogs.py` | 10 | 全 6 種主題之彈出視窗高對比度 Token、按鈕/核取/單選指示器渲染、所有對話框主題色彩套用相容 |

---

## 3. 各測試模組詳細項目清單

### 3.1 AI 輔助與長文本分析（23 項）

#### `test_ai_character_extraction.py` (6 項)
- `test_ai_dialogs_scale_and_styles`：測試 `AIScopeDialog` 與 `AICharacterReviewDialog` 支援 scale_factor 縮放與清晰外框。
- `test_ai_scope_content_extraction_tree`：測試提取多層樹狀目錄（卷-章-幕）內文與字數統計之正確性。
- `test_fallback_character_parsing`：測試模型未依規定標籤輸出（如純 Markdown 標題）時的 Fallback 容錯解析。
- `test_latex_and_tag_cleaning`：測試 LaTeX 關係指令與重複標籤的清理與富文本渲染。
- `test_markdown_highlighter_and_preview`：測試 `MarkdownHighlighter` 與 `CardDetailDialog` 預覽切換。
- `test_structured_character_parsing_5_elements`：測試結構化標籤格式解析，確認 5 大要素與獨立關係卡解析無誤。

#### `test_ai_chat.py` (4 項)
- `test_init_with_context`：測試 AI 聊天面板帶有目前章節上下文之初始化狀態。
- `test_init_without_context`：測試無上下文狀態下的 AI 聊天面板初始化。
- `test_insert_and_save_card_signals`：測試將 AI 回應插入正文或另存為資料卡片的信號發送。
- `test_message_formatting_and_history`：測試對話訊息排版格式與歷史對話記錄保存。

#### `test_ai_continuation.py` (3 項)
- `test_continuation_default_disabled`：驗證智慧續寫功能預設保持停用，避免未授權呼叫。
- `test_continuation_inserted_at_cursor`：驗證生成續寫文本能精準插入於編輯器游標所在位置。
- `test_continuation_worker_initialization`：驗證背景續寫非同步 Worker 初始化與參數傳遞。

#### `test_ai_service.py` (3 項)
- `test_default_settings_contains_openai_and_features`：驗證預設 `ai_settings.json` 正確包含 OpenAI 介面及各項 AI 功能開關。
- `test_detect_local_models_empty_or_offline`：驗證本地模型離線或無法連接時的例外捕捉與防禦處理。
- `test_load_and_save_settings`：驗證 AI 服務設定檔讀取與儲存之完整性。

#### `test_long_text_analyzer.py` (7 項)
- `test_split_into_chunks_short_text`：測試短文本的分塊處理（不切分）。
- `test_split_into_chunks_long_text_with_overlap`：測試超長篇小說的分塊演算法，包含段落邊界保留與滑動重疊視窗（Overlap）。
- `test_build_chunk_prompt`：測試動態注入角色摘要與當前分塊文字的 Prompt 建置。
- `test_parse_chunk_response_standard`：測試標準 JSON 格式分塊回應解析。
- `test_parse_chunk_response_fallback`：測試非標準或損毀 JSON 的容錯抽取與備援解析。
- `test_full_pipeline_rolling_analysis`：測試跨章節多區塊滾動分析完整管線。
- `test_cancellation`：測試長文本分析進行中，使用者點擊取消之中斷機制。

---

### 3.2 核心控制器與右側資料卡片（23 項）

#### `test_controllers.py` (12 項)
- `test_auto_load_latest_temp_priority_and_fallback`：測試優先自動載入最新暫存檔，若不存在則退回正式存檔。
- `test_card_controller_serialization`：測試 CardController 資料結構序列化與反序列化。
- `test_main_editor_plain_text_paste_and_preservation`：測試編輯器貼上純文字時，正文 Markdown 符號（如 `**粗體**`）完好保留。
- `test_mark_color_map_consistency`：測試標記顏色常數對應之一致性。
- `test_project_controller_build_and_load`：測試 ProjectController 構建專案資料結構與還原載入。
- `test_stats_controller_markdown_exclusions`：測試 Markdown 語法符號不計入正文字數之排除邏輯。
- `test_stats_controller_word_count_and_exclusions`：測試 StatsController 字數統計與排除條件。
- `test_subcontrollers_initialization`：測試 9 大子控制器（Subcontrollers）實例化並注入 MainController。
- `test_theme_controller_apply_theme`：測試 ThemeController 套用日夜間主題樣式。
- `test_theme_menu_scaling`：測試 ThemeManager 針對高解析度縮放之 scale_qss 與 QSS 縮放計算。
- `test_trash_permanent_delete_and_clear`：測試垃圾桶永久刪除單一節點與一鍵清空功能。
- `test_tree_controller_create_and_query_item`：測試 TreeController 樹狀節點建立與查詢。
- `test_volume_and_book_title_independence`：測試修改書名與修改第一卷名稱各自獨立、互不干擾。
- `test_writing_log_ai_fields_roundtrip`：驗證 `_build_jne_project` 與 `load_project_data` 完整保留 AI 介入度欄位。

#### `test_right_panel_split.py` (9 項)
- `test_card_rename_sync_with_editing_panel`：測試卡片更名時，下方正在編輯中的面板標題即時連動更新。
- `test_click_card_loads_content`：測試點選卡片節點時，下方欄位切換至編輯頁 (Index 1) 並載入標題與內文。
- `test_click_category_shows_placeholder`：測試點擊分類節點時切換回預設提示頁 (Index 0)。
- `test_delete_editing_card_resets_to_placeholder`：測試當正在編輯的卡片遭刪除時，下方重設為提示頁。
- `test_initial_state_placeholder`：測試右側下方預設呈現提示導引頁面。
- `test_markdown_highlighter_and_formatting`：測試卡片編輯區支援富文本所見即所得與工具列格式化。
- `test_markdown_preview_toggle`：測試卡片 Markdown 預覽模式切換。
- `test_save_card_from_panel`：測試在下方欄位修改內容並儲存，資料模型與上方面板節點皆正確同步。
- `test_scene_panel_switch`：測試切換為「幕」屬性編輯面板 (Index 2)。

#### `test_card_detail_dialog.py` (2 項)
- `test_plain_text_editing_and_data`：測試卡片獨立詳情視窗之文字編輯與資料儲存。
- `test_plain_text_paste_strips_formatting`：測試貼上外來網頁或富文本時，自動清洗為純文字。

---

### 3.3 章節樹與三層結構「幕」（18 項）

#### `test_context_menus.py` (9 項)
- `test_card_copy_content`：測試卡片右鍵複製內文至剪貼簿。
- `test_card_duplicate`：測試卡片複製副本（含子階層卡片）。
- `test_card_move_up_and_down`：測試卡片節點同層順序上移與下移。
- `test_card_rename`：測試卡片重新命名。
- `test_tree_clear_mark`：測試清除目錄樹節點之進度標記色彩。
- `test_tree_duplicate_file_node`：測試單一章節節點建立副本。
- `test_tree_duplicate_folder_with_children`：測試整卷資料夾（含其下所有子章節）完整建立副本。
- `test_tree_move_up_and_down`：測試目錄樹同層節點上移與下移。
- `test_tree_rename_node`：測試目錄樹節點重新命名。

#### `test_scene.py` (9 項)
- `test_file_node_scene_fields_default_empty`：驗證一般章節節點的幕欄位預設保持空字串。
- `test_scene_fields_default_empty`：驗證幕節點三大 metadata（時間、地點、POV）預設均為空字串。
- `test_scene_node_literal_valid`：驗證 `'scene'` 為合法的 node_type。
- `test_save_and_load_scene_node`：驗證儲存含幕節點專案後，讀取資料結構精確一致。
- `test_scene_fields_persist_on_overwrite`：驗證覆寫存檔（DELETE + INSERT）後幕屬性資料不遺失。
- `test_old_db_without_scene_columns`：驗證讀取未含幕欄位之舊版 DB 時自動 fallback 為空字串。
- `test_dialog_initial_values`：驗證幕屬性對話框開啟時正確帶入既有數值。
- `test_empty_initial_values`：驗證無初始值時對話框欄位呈現空白。
- `test_get_metadata_returns_correct_values`：驗證使用者在對話框修改後正確傳回更新值。

---

### 3.4 專案儲存、快照、備份與自訂路徑（25 項）

#### `test_database.py` (1 項)
- `test_save_and_load_project`：測試 SQLite 資料庫儲存專案並重新完整載入。

#### `test_daily_progress_sync.py` (7 項)
- `test_database_daily_target_persistence`：測試 `ProjectInfo.daily_target_word_count` 在 SQLite 資料庫之儲存與載入。
- `test_database_migration_v9_to_v10`：測試舊版 v9 資料庫自動平滑升級至 v10，並自動為 `project_info` 補齊 `daily_target_word_count` 欄位（預設 1000）。
- `test_load_project_restores_today_target_and_progress`：測試跨設備（Dropbox 等同步）開啟專案時，自動還原當日目標與當天累計寫作進度條。
- `test_load_project_different_date_resets_today_progress`：測試跨日開啟存檔時，歷史進度安全保留於日誌中，當日進度自動以 0 字重啟。
- `test_set_daily_target_persists_and_saves`：測試設定當日寫作目標字數時，即時持久化至專案資訊並觸發暫存。
- `test_clear_daily_progress_clears_today_log_and_saves`：測試清除當日進度時，同步清空寫作日誌中當日字數並觸發暫存，防止換設備或重開後復活。
- `test_flush_writing_session_syncs_with_today_written_count`：測試寫作結算 (flush) 時，當日日誌字數與狀態列即時進度維持嚴格一致。

#### `test_backup.py` (3 項)
- `test_backup_nonexistent_file_raises_error`：測試備份不存在的檔案時拋出正確例外。
- `test_create_and_inspect_backup`：測試備份建立與檔案完整性檢驗。
- `test_restore_backup_and_load`：測試還原備份檔案並載入專案。

#### `test_snapshot.py` (4 項)
- `test_delete_snapshot`：測試刪除特定快照版本。
- `test_load_and_restore_snapshot_integrity`：測試載入與還原快照之資料完整性。
- `test_save_and_list_snapshots`：測試快照建立並列出專案所有歷史快照。
- `test_snapshot_dialog_populate_and_selection`：測試快照管理視窗的清單呈現與點選切換。

#### `test_tree_expansion_persistence.py` (2 項)
- `test_database_expansion_persistence`：測試 DatabaseService 對樹狀展開狀態的資料庫儲存。
- `test_ui_tree_expansion_workflow`：測試完整 UI 流程：操作展開/折疊節點後存檔，重新開檔驗證樹狀展開狀態精準還原。

#### `test_storage_path.py` (6 項)
- `test_app_settings_storage_path_helpers`：測試 AppSettingsService 自訂存檔路徑解析輔助方法。
- `test_project_controller_open_storage_path_dialog_flow`：測試從控制器觸發路徑切換並重設當前專案儲存位置。
- `test_storage_migration_service_data_migration`：測試稿件與暫存檔跨目錄遷移。
- `test_storage_migration_service_ensure_directories`：測試自動補齊新目錄之 `Story` 與 `Temp_doc` 資料夾。
- `test_storage_migration_service_is_valid_writable_dir`：測試目錄存在性與寫入權限檢查。
- `test_storage_path_dialog_ui`：測試自訂儲存路徑對話框介面操作與重設預設值。

---

### 3.5 自動存檔與崩潰恢復（9 項）

#### `test_autosave_and_startup.py` (9 項)
- `test_autosave_settings_dialog_ui`：測試自動儲存設定視窗之偏好設定讀取與變更。
- `test_autosave_timer_and_file_limit_cleanup`：測試暫存檔數量清理邏輯：超過設定上限時，依時間優先移除最舊檔案。
- `test_crash_recovery_trigger`：測試當前次標記為異常退出且存在暫存檔時，自動觸發崩潰恢復機制並載入最新暫存。
- `test_default_app_settings_fields`：測試偏好設定預設包含暫存間隔與上限數量等欄位。
- `test_load_latest_story_project`：測試從多個書目與存檔中挑選最新異動之專案載入。
- `test_load_project_file_prompt_default_story_dir`：測試開檔選擇器之預設目錄定位於 Story 目錄。
- `test_menu_action_autosave_settings_exists`：驗證功能表選單已正確掛載自動存檔設定動作。
- `test_startup_dialog_actions`：測試啟動歡迎視窗卡片按鈕之導航動作。
- `test_startup_dialog_reject_sets_should_exit`：測試作者點擊啟動視窗關閉鈕時，控制器標記正常退出。

---

### 3.6 寫作審校、字數目標與寫作日誌（17 項）

#### `test_phase12.py` (12 項)
- `test_database_writing_logs_migration_and_persistence`：驗證 SQLite `writing_logs` 資料表自動 Migration 與 AI 介入度欄位保存。
- `test_lint_dialog_lifecycle_and_navigation`：驗證審校視窗初始化、重新掃描與跳轉信號發送。
- `test_lint_duplicate_words`：驗證相鄰重複詞彙偵測。
- `test_lint_high_density_particle`：驗證單句高頻虛詞（的、地、得、了）密度過高偵測。
- `test_lint_master_toggle_and_rule_switches`：驗證審校總開關與各規則獨立切換行為。
- `test_lint_passive_voice_detection`：驗證中文被動語態（被字句）弱句偵測。
- `test_lint_redundant_phrase_detection`：驗證公文與冗贅片語檢查規則。
- `test_lint_whitelist_and_custom_words`：驗證白名單可排除特定專有名詞，自訂贅詞可正常觸發警告。
- `test_lint_whitelist_dialog_add_delete`：驗證白名單維護視窗新增與刪除操作。
- `test_stats_controller_record_ai_activity`：驗證 StatsController 正確累計當日 AI 產出字數與活動次數。
- `test_writing_log_dashboard_and_chart_view`：驗證寫作日誌儀表板指標計算與視圖模式切換。
- `test_writing_log_entry_ai_fields`：驗證 WritingLogEntry dataclass 包含並正確初始化 AI 介入度欄位。

#### `test_stats_settings.py` (5 項)
- `test_database_schema_v6_target_word_count`：測試 SQLite schema v6 支援 target_word_count 欄位持久化。
- `test_project_progress_bar_and_target`：測試全書總字數進度條與寫作目標設定聯動。
- `test_status_bar_detailed_tooltip`：測試狀態列詳細統計 ToolTip 產生與規則說明。
- `test_word_count_rules_switching`：測試字數計算開關（含/不含空白、標點等）在不同設定下的統計結果。
- `test_word_count_settings_dialog`：測試計字設定對話框介面呈現與偏好設定讀取。

---

### 3.7 視窗設定、大綱檢視、搜尋與匯出（28 項）

#### `test_window_settings.py` (9 項)
- `test_app_settings_service_load_save`：測試 AppSettingsService 設定讀取與儲存。
- `test_apply_and_extract_settings`：測試 MainWindow 與 AppSettingsService 之間視窗幾何尺寸的套用與提取。
- `test_close_event_persists_settings`：測試視窗關閉事件觸發介面狀態持久化。
- `test_default_layout_ratios`：測試預設三欄比例為 1:2:2（左側 20%、編輯 40%、右側 40%）。
- `test_first_launch_initial_scale_dialog`：測試首次乾淨啟動彈出縮放設定視窗並正確儲存。
- `test_reset_project_state_preserves_scale`：測試開啟新專案時不將縮放比例重設為 1.0。
- `test_subsequent_launch_preserves_scale_without_dialog`：測試非首次啟動時直接套用已存比例且不彈出導引視窗。
- `test_theme_set_ui_scale_persists_settings`：測試 ThemeController.set_ui_scale 即時寫入 app_settings.json。
- `test_ui_scale_font_scaling`：測試縮放時工具列、狀態列與樹狀節點字型正確等比放大。

#### `test_focus_and_outline.py` (4 項)
- `test_focus_mode_lifecycle`：測試全螢幕沉浸專注模式進入與退出狀態。
- `test_outline_filter`：測試全書大綱即時關鍵字搜尋與章節過濾。
- `test_outline_open_chapter_and_mark_change`：測試在大綱檢視中快速選取章節跳轉與就地修改進度標記。
- `test_outline_view_population_and_stats`：測試大綱模式從目錄樹擷取資料、計算各卷各章字數與摘要。

#### `test_markdown_converter.py` (7 項)
- `test_parse_inline_tokens_plain`：測試純文字 Inline Token 解析。
- `test_parse_inline_tokens_mixed`：測試粗體、斜體、行內代碼等混合語法 Token 解析。
- `test_to_plain_text`：測試將 Markdown 轉換為純淨文字。
- `test_to_html_paragraphs`：測試將 Markdown 轉換為 HTML 段落結構。
- `test_to_html_paragraphs_empty_lines`：測試空行轉換為段落時的保留機制。
- `test_render_to_docx`：測試排版渲染為 Word (.docx) 段落結構。
- `test_markdown_to_html_empty_line_style`：測試富文本編輯器空行使用 `-qt-paragraph-type:empty` 樣式消除雙倍行高並確保 round-trip 無損還原。

#### `test_export.py` (4 項)
- `test_export_docx`：測試匯出為 Word (.docx) 文件。
- `test_export_epub`：測試匯出為標準 EPUB 電子書。
- `test_export_md`：測試匯出為 Markdown (.md) 文件。
- `test_export_txt`：測試匯出為純文字檔 (.txt)。

#### `test_search.py` (5 項)
- `test_find_in_editor_and_navigation`：測試編輯器內關鍵字搜尋與上一個/下一個導航。
- `test_global_search_across_chapters`：測試跨章節全書全文搜尋與結果摘要匹配。
- `test_search_controller_initialization`：驗證 SearchController 正確初始化並連接到 MainController。
- `test_search_options`：測試搜尋選項（區分大小寫、全字比對、正規表達式）。
- `test_single_replace_and_replace_all`：測試單次取代與全書一次取代。

---

### 3.8 主題樣式與對話框色彩（10 項）

#### `test_theme_dialogs.py` (10 項)
- `test_theme_manager_tokens_for_all_themes`：驗證所有 6 種主題皆具備高對比指示器、邊框與強調色 tokens。
- `test_initial_scale_dialog_indicators`：驗證初次啟動比例選擇視窗的 RadioButton 與選項卡片樣式。
- `test_export_scope_dialog_theme_awareness`：驗證匯出設定視窗支援高對比度 RadioButton 與 CheckBox。
- `test_word_count_settings_dialog_theme_awareness`：驗證字數統計設定視窗支援主題色。
- `test_autosave_settings_dialog_theme_awareness`：驗證自動存檔設定視窗支援主題色與 SpinBox。
- `test_storage_path_dialog_theme_awareness`：驗證存檔路徑視窗載入與控制項樣式。
- `test_global_search_dialog_theme_awareness`：驗證全域搜尋視窗樣式包含主題色彩。
- `test_snapshot_dialog_theme_awareness`：驗證快照視窗表格樣式與主題色整合。
- `test_scene_metadata_dialog_init`：驗證場景屬性視窗支援 QPlainTextEdit。
- `test_dialogs_across_all_themes`：驗證所有 6 種主題皆能透過 apply_theme_to_dialog 正確套用於對話框。

---

## 4. Agent 測試編寫與維護規範

1. **乾淨隔離原則**：
   - 涉及檔案或資料庫測試，必須使用 pytest 內建的 `tmp_path` fixture，**嚴禁在專案真實目錄中寫入測試資料**。
   - 涉及 PyQt UI 元件時，使用 `qapp` fixture 確保 QApplication 生命週期安全。
2. **小步驗證**：
   - 編寫完任何新測試後，立即以 `C:\Python314\python.exe -m pytest tests/<your_test_file>.py` 驗證單一測試。
   - 確保全部 136+ 項測試全數通過（`0 failures, 0 errors`）。
3. **文檔同步維護**：
   - 新增測試函數時，應包含清晰的 docstring 說明其測試邊界。
   - **必須同步更新本文件**，更新測試總數、模組項數與測試項目清單！
