# 純本機 AI 語意校稿引擎與架構減法重構指南 (Phase 30 Migration Guide)

> 本文件專為接續執行的開發者與 AI Agent 設計，提供由雲端/長文分析轉向「純本機 AI 語意校稿與修稿引擎」之完整落地路徑與四階段實施規範。

---

## 一、 背景與重構動機

1. **現狀瓶頸**：
   - 專案早期嘗試讓本地小模型（8B/10B 規模、8K 脈絡）執行長篇小說（五至六萬字）之全書分析、人物抽取、世界觀梳理與多輪對話，導致系統維護成本飆升（需維護 6 家雲端 API 路由與複雜的 Token 估算器），且本地小模型在全書長文本推論時極易超出顯存（OOM）或耗時過長。
   - 智慧續寫與擴寫功能實務上介入了作家的核心創作主體性，偏離了長篇創作者最真實的工具需求。
2. **戰略轉向**：
   - 全面移除商業雲端 API（OpenAI、Claude、Gemini、Grok）與所有生成型/長文抽取功能。
   - 聚焦於高局部性（High Locality）、低耗損且對寫作心流幫助最大的「錯別字檢查、用詞糾正與段落修稿建議」。
   - 現有資料庫已在 Schema v8 預留 `proofread_results` 與 `proofread_ignored_rules` 兩張表格，前端亦已具備 `AIProofreadDialog`，目前僅缺真實推論引擎實裝。

---

## 二、 架構變更對照表 (Architecture Diff)

| 模組維度 | 重構前 (Current) | 重構後 (Target Phase 30) |
|---|---|---|
| **模型後端** | 支援 OpenAI、Gemini、Claude、Grok、Ollama、LM Studio | **僅支援本地端點**（Ollama / LM Studio / 相容本地端點） |
| **核心功能** | 對話、續寫、評語、角色、世界觀、時間線、校稿 (Mock) | **純本機雙軌校稿引擎**（`LintService` 規則 + `AIProofread` 語意） |
| **UI 視窗** | 8 個 AI 專屬 Dialog/HUD/Overlay | **僅保留 2 個視窗**：`AIProofreadDialog`、`AISettingsDialog` |
| **通訊協定** | 多供應商特化 SDK 與請求分支、串流擴寫、Token 估算器 | **標準本地 OpenAI 相容介面**（`/v1/chat/completions`） |
| **資料庫** | Schema v14（維持向後相容） | **Schema v14 完全不變**，無破壞性 Migration |
| **日誌統計** | 累計續寫字數、對話次數、各功能詳細次數 | 收斂為手創度 100%、累計記錄 `proofread` 校稿次數 |

---

## 三、 四階段執行步驟與實作規範

```
[Phase 1: 核心校稿引擎落地] ──> [Phase 2: UI 介面與外圍模組剪裁] ──> [Phase 3: Controller/Service 深層解耦] ──> [Phase 4: 測試重整與文件固化]
```

### 階段一：本機 AI 校稿核心推論引擎實裝與驗證 (Phase 1)
* **核心檔案**：
  - `services/ai_worker.py`
  - `controllers/ai_controller.py`
  - `tests/unit/test_ai_proofread_worker.py` (新增)
* **實作要點**：
  1. 在 `services/ai_worker.py` 實作 `AIProofreadWorker(BaseAIWorker)`：
     - 繼承 `BaseAIWorker`，確保具備 `cancel()` 關閉 Socket 機制。
     - 傳入參數：`text_content: str`, `chapter_name: str`, `node_id: str`, `options: dict`。
     - 信號：`finished_signal(list)`, `progress_signal(int, int, str)`, `error_signal(str)`。
  2. 設計結構化 JSON 輸出 Prompt：
     - 要求模型輸出純 JSON 陣列：`[{"category": "typo"|"usage"|"suggestion", "original_text": "...", "suggestion": "...", "reason": "...", "char_offset": 0, "match_len": 0}]`。
     - 提示詞需嚴格約束：不得大幅改寫內文文風，僅針對確鑿錯字、顛倒詞與病句。
  3. 分塊策略（Chunking）：
     - 單次推論限制在 2,000 字以內，若章節過長依段落換行切分批次推論後彙整。
  4. 改寫 `AIController.handle_start_proofread`：
     - 移除寫死字串比對假資料，改由非同步啟動 `AIProofreadWorker`。
     - 收到結果後，比對 `proofread_ignored_rules` 過濾後呼叫 `DatabaseService.save_proofread_result`。
* **驗證指標**：
  - 新增 `tests/unit/test_ai_proofread_worker.py`，以 Mock 驗證推論解析成功、回傳格式錯誤防禦、取消與逾時處理。

---

### 階段二：UI 介面收斂與多餘入口拆除 (Phase 2)
* **核心檔案**：
  - `views/components/menu_builder.py`
  - `views/components/jne_text_edit.py`
  - `views/components/right_panel_card_editor.py`
  - `views/dialogs/ai_settings_dialog.py`
* **實作要點**：
  1. `menu_builder.py`：
     - 清除 `action_ai_chat`、`action_ai_continuation`、`action_ai_impression`、`action_ai_character`、`action_ai_world`、`action_ai_timeline`。
     - 「AI 助手」選單僅保留：
       - `action_ai_proofread`（AI 校稿...）
       - `action_ai_settings`（本機 AI 設定...）
  2. `jne_text_edit.py` 與 `right_panel_card_editor.py`：
     - 右鍵選單移除「與 AI 討論」、「AI 智慧擴寫」與「AI 結構化分析」選單項。
  3. `ai_settings_dialog.py`：
     - 移除 OpenAI、Gemini、Claude、Grok 的 API Key 輸入框。
     - 僅保留 Ollama / LM Studio 端點網址、連線測試按鈕、模型下拉選單與逾時秒數。
  4. 廢棄 UI 視窗清理：
     - 自 `controllers/ai_controller.py` 中移除對 `AIChatDialog`、`AIExpansionDialog`、`AIScopeDialog`、`AIPreviewDialog`、`AICharacterReviewDialog`、`AITaskOverlay`、`AIFloatingHUD` 的引用。
* **驗證指標**：
  - 手動啟動 GUI 驗證所有選單點擊無崩潰，介面俐落乾淨。

---

### 階段三：Controller 與 Service 層深度解耦與死碼清理 (Phase 3)
* **核心檔案**：
  - `controllers/ai_controller.py`
  - `services/ai_service.py`
  - `services/ai_settings_service.py`
  - `services/ai_worker.py`
  - `services/writing_log_service.py`
  - `controllers/stats_controller.py`
* **實作要點**：
  1. `controllers/ai_controller.py` 瘦身：
     - 刪除續寫、擴寫、角色抽取、單卡/多卡生成等無用方法。
     - 專職負責 `open_ai_settings_dialog`、`open_ai_proofread_dialog`、`handle_start_proofread`、`handle_proofread_status_change` 與 `handle_proofread_ignore_rule`。
  2. `services/ai_service.py` 簡化：
     - 移除 Anthropic / Google Gemini 特殊協定封裝，統一走本地標準 OpenAI 相容格式。
     - 移除 `TokenEstimator` 依賴。
  3. `services/ai_worker.py` 清理：
     - 移除 `AIWorker`、`AIChatWorker`、`AIContinuationWorker`、`AIStreamWorker`。
  4. 日誌與統計相容：
     - `writing_log_service.py` 與 `stats_controller.py` 維持 `proofread` 次數累計，手創比例恆定為 100%。
* **驗證指標**：
  - 專案核心控制器行數大幅下降，無任何未使用的死碼。

---

### 階段四：測試套件重整、架構文件同步與版本標記 (Phase 4)
* **核心檔案**：
  - `tests/`
  - `.agents/docs/ARCHITECTURE.md`
  - `.agents/docs/TEST_SUITE.md`
  - `.agents/docs/HANDOVER.md`
  - `CHANGELOG.md`
* **實作要點**：
  1. 測試套件重整：
     - 移除已廢棄之對話、續寫、角色抽取相關測試（`test_ai_chat.py`, `test_ai_continuation.py`, `test_ai_character_extraction.py`, `test_ai_scope_dialog.py`, `test_token_estimator.py`）。
     - 更新 `test_stats_ai_breakdown.py`、`test_phase12.py` 與 `test_p0_bug_fixes.py` 中的斷言。
  2. 執行全套測試：
     - 執行 `python -m pytest tests/`，確認通過率 100%。
  3. 同步文件：
     - 更新架構圖與測試清單，於 `HANDOVER.md` 標記 Phase 30 完成。
* **驗證指標**：
  - 全套測試 100% 綠燈，文件與程式碼精確吻合。

---

## 四、 接手 Agent 必讀禁令與陷阱 (Rules for Next Agent)

1. **嚴禁破壞性 Migration**：不得修改或刪除 SQLite 既有欄位（如 `writing_logs.ai_details`），保持反序列化防禦。
2. **遵守 10B 模型小步快跑原則**：每次僅執行一個 Phase，修改前務必先使用 `view_file` 閱讀目標程式碼，連續失敗 2 次立即停止盲猜。
3. **台灣繁體中文排版規範**：所有 UI 文字、註解與訊息一律嚴格使用台灣繁體中文（如「最佳化」、「專案」、「使用者」），嚴禁 Emoji 與破折號語氣強化。
4. **絕對禁止阻塞 UI 執行緒**：推論必須在 `AIProofreadWorker`（QThread）中執行，且必須響應使用者隨時中斷。
