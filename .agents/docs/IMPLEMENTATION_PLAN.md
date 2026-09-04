# 九方小說編輯器 — Phase 20 系統重構與防護最佳化計畫

> 規劃日期：2026-09-01
> 規劃目標：清理累積技術債、預防潛在狀態衝突、進一步最佳化大型檔案可讀性
> 執行階段：Phase 20

---

## 一、 現存技術債與潛在風險分析 (Tech Debt & Risks)

### 1. 檔案過大與模組內聚性降低 (Large Files)
- **`services/database.py` (848 行)**
  - **現況**：目前承載了資料庫連線、`schema_version` v1 至 v6 的完整遷移邏輯 (Migrations)、專案存檔反序列化 (`_project_to_dict`)、各項 CRUD，以及 Snapshot 處理。
  - **風險**：隨著功能迭代，檔案行數可能突破千行，增加 10B LLM 理解難度與出錯機率。
- **`controllers/project_controller.py` (815 行)**
  - **現況**：已經抽離了備份與快照功能，但仍負責新專案建立、載入/儲存核心邏輯、自動暫存排程 (`auto_autosave`) 與崩潰還原 (`crash_recovery`)。
  - **風險**：邏輯過度集中，尤其 `_build_jne_project` 等大型資料結構轉換與 UI 更新混雜，不利於單一職責原則 (SRP)。

### 2. 狀態同步與潛在衝突 (State Synchronization Conflicts)
- **右側資料集面板 vs 主樹狀結構**
  - **現況**：Phase 19 新增了在右側面板下方直接編輯卡片標題與內容的功能。
  - **風險**：如果在左側主樹狀結構也選中了同一個節點進行更名，或者在主編輯器中修改，可能會引發「資料覆寫 (Data Overwrite)」或「UI 未同步」的衝突。
- **Scene 幕屬性編輯的雙重入口**
  - **風險**：場景的屬性（時間、地點、POV 等）若能從右側面板編輯，同時如果存在其他彈出視窗（如 `SceneMetadataDialog`），可能產生資料不同步的競態條件。

### 3. 初始化與邊界條件小 Bug (Minor Bugs)
- **`current_project_path` 初始化**：B6 (未在 `__init__` 初始化) 雖在 Phase 16 嘗試修復，但隨著存檔路徑自訂 (Phase 18) 的引入，路徑狀態的變更可能帶來新的不一致性。

---

## 二、 Phase 20 分階段執行計畫 (Execution Plan)

> [!IMPORTANT]
> 接下來接手的 Agent 請嚴格按照以下階段進行，每完成一階段必須執行 `pytest tests/ -v` 確保 126 項測試未受破壞。

### Phase 20.1: Database Service 瘦身與拆分
**目標**：將 `database.py` 拆分，降低模組複雜度。
1. **建立 `services/database_migrations.py`**：將 `update_schema` 以及 `_migrate_vX_to_vY` 等所有結構升級邏輯抽離。
2. **建立 `services/database_core.py` (可選)**：處理純 SQLite 連線與基礎執行。
3. **主檔重構**：`database.py` 僅保留 CRUD 與高層 API 介面，依賴 `database_migrations.py` 進行初始化檢查。
4. **驗證**：確保 `tests/test_database.py` 與 `tests/test_phase12.py` 中的 migration 測試全數通過。

### Phase 20.2: Project Controller 模組化
**目標**：減輕 `project_controller.py` 負擔。
1. **拆分 `AutosaveController`**：將自動暫存 (`auto_autosave`)、計時器管理、垃圾桶清理、崩潰還原 (`crash_recovery`) 的邏輯獨立為一個新的子控制器。
2. **重構 ProjectController**：僅保留 `load_project`, `save_project_as`, `open_project` 等最核心的手動/初始化專案生命週期功能。
3. **驗證**：確保 `tests/test_autosave_and_startup.py` 通過。

### Phase 20.3: UI 狀態同步防護機制加固
**目標**：徹底消除右側資料面板與左側主樹/主編輯器的同步衝突。
1. **單一資料流 (Single Source of Truth) 確認**：確保右側卡片編輯時，修改的是唯一的 `CardNode` 或 `ChapterNode` 實例，且修改後透過單一 Signal `card_content_updated` 通知所有相關 View（左樹、右樹、主編輯器）重新整理 UI。
2. **鎖定機制 (Editing Lock)**：當使用者在右側面板編輯某卡片時，考慮鎖定主編輯器對應內容，或即時雙向綁定 (Two-way binding)。
3. **驗證**：擴充 `tests/test_right_panel_split.py`，模擬左側更名與右側編輯同時發生的情況，確保資料模型一致。

### Phase 20.4: GitHub Action 與自動化整合 (可選)
**目標**：利用已建立的 GitHub 環境，增加自動化。
1. **建立 `.github/workflows/python-tests.yml`**：加入自動化 Pytest 測試，確保未來 push 時自動檢查。
2. **檢閱 `.gitignore`**：確認 `.agents/` 的規則是否正確（目前已允許 `docs/`, `rules/`, `build/` 提交）。

---

## 三、 給下一個 Agent 的交接提醒
- **不要隨意更改 `MARK_COLOR_MAP`**：它位於 `models/models.py`，請直接 import 使用。
- **MVC 邊界**：拆分 Controller 時，記得在 `main_controller.py` 中正確註冊，並將參考 (`self.mc`) 傳入。
- **小步快跑**：每次只執行 20.1, 20.2 這樣的一個小階段，完成並通過測試後才進行下一個。
