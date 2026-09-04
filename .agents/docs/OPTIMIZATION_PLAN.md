# 九方小說編輯器 — 專案深度檢視與最佳化計畫 (Phase 14)

> 針對專案進行非破壞性靜態掃描與架構檢視後，產出此最佳化計畫。此計畫專為 10B 以下規模之小型模型設計，任務切割極為細緻，確保每次只更動單一邏輯或模組。

---

## 壹、 專案現狀評估與核心發現

### 1. 模組運作狀態 (Operation Status)
✅ **運作正常**：
- **MVC 架構邊界嚴謹**：`views` 僅發送信號，`controllers` 透過 `main_controller` 代理橋接，無循環依賴。
- **背景非同步處理良好**：AI 擴寫與串流解析已抽離至 Worker 執行緒，不阻塞主視窗。
- **資料單一真相來源**：SQLite (`database.py`) CRUD 邏輯穩定，專案樹 (`JneProject`) 與資料庫映射正常。

### 2. 審美不統一情形 (Aesthetic Inconsistencies)
⚠️ **主題引擎 (ThemeManager) 破窗效應**：
在 `views/main_window.py` 內部存在大量 **Inline Stylesheet (寫死的 CSS 樣式)**，完全繞過了 `theme_manager.py` 的統一管控。這會導致切換主題（如綠影、青瓷）時，部分介面依然卡在「預設深色」的顏色。
- **被硬編碼的元件**：
  - `lbl_current_file` (編輯器頂部檔名)：硬編碼了 `background-color: #2d2d2d;`。
  - `JNEStatusBar` (狀態列)：硬編碼了 `#2d2d2d`、按鈕 `#3d3d3d`、hover `#4d4d4d`。
  - `trash_list_widget` (垃圾桶清單)：硬編碼了 `#252526` 與選取狀態 `#094771`。
  - `btn_save_scene_info` (幕資訊儲存按鈕)：硬編碼了 `#0e639c` (藍色)。
  - `lbl_focus_banner` (沉浸模式提示)：硬編碼了 `rgba(30, 30, 30, 180)`。

### 3. 技術債的殘留 (Technical Debt)
⚠️ **God Object 跡象**：
- `views/main_window.py` 長達近 700 行。選單建立 (`setup_menus`)、左面板、中央面板、右面板的所有 UI 宣告全擠在 `init_ui()` 中，未來新增介面時將極難維護。
- `services/storage.py` 保留了向後相容舊 JSON 專案的功能，但裡面卻還留有 `save_project_to_json` 的方法。既然專案已宣告「全面採用 SQLite」，保留寫入 JSON 的程式碼是一顆未爆彈。

### 4. 潛在的維護風險 (Maintenance Risks)
⚠️ **SQLite 手動 Schema Migration 脆弱**：
- `database.py` 的 `init_db` 方法使用純字串 SQL 與 `PRAGMA table_info` 來手動檢查與新增欄位（如 `scene_pov`、`ai_chat_count`）。隨著專案迭代，此種手動打補丁的方式極易出錯且難以追蹤版本號，缺乏標準的 Database Migration 系統。

---

## 貳、 最佳化執行階段 (Phase 14 Execution Plan)

為了讓小模型 (10B 以下) 能安全接手，以下計畫將修改範圍嚴格切割。**每次執行請只挑選一個小階段完成。**

### 🎯 階段 A：UI 審美與主題一致性修復 (Theme Consistency)
> **目標**：拔除 `main_window.py` 中的硬編碼樣式，將其轉移至 `theme_manager.py`。
- [x] **Phase 14.1**：在 `THEME_COLORS` 與 `BASE_THEME_TEMPLATE` 中新增缺失的鍵值，例如 `status_bar_bg`, `status_btn_bg`, `trash_list_bg`, `scene_btn_bg` 等。（✅ 已完成）
- [x] **Phase 14.2**：修改 `views/main_window.py`，移除 `lbl_current_file`、`lbl_focus_banner` 與 `JNEStatusBar` 的硬編碼 `setStyleSheet`，改為設定對應的 `setObjectName`，讓 `theme_manager.py` 自動套用。（✅ 已完成）
- [x] **Phase 14.3**：移除 `main_window.py` 中 `trash_list_widget` 與 `btn_save_scene_info` 的硬編碼，確認所有主題（包含 default, green, celadon 等）切換時不會出現顏色斷層。（✅ 已完成）

### 🎯 階段 B：MainWindow UI 類別瘦身 (UI Component Refactoring)
> **目標**：將 `main_window.py` 拆分為小元件，降低單一檔案行數。
- [x] **Phase 14.4**：將「選單列建立」邏輯（包含 `setup_menus` 相關）從 `main_window.py` 抽離至新檔案 `views/components/menu_builder.py`。（✅ 已完成）
- [x] **Phase 14.5**：將「左方面板」（包含樹狀結構與垃圾桶切換）抽離為獨立元件類別 `LeftPanelView`。（✅ 已完成）
- [x] **Phase 14.6**：將「右方面板」（包含資料集與 TabWidget）抽離為獨立元件類別 `RightPanelView`，讓 `MainWindow` 僅負責 Layout 排版。（✅ 已完成）

### 🎯 階段 C：遺留程式碼封存防護 (Legacy Code Safelocking)
> **目標**：防止舊程式碼被誤用。
- [x] **Phase 14.7**：修改 `services/storage.py`，刪除 `save_project_to_json` 等「寫入」相關方法。僅保留 `load_project_from_json` 與對應的私有轉譯函式，徹底封死存回 JSON 的路徑。（✅ 已完成）
- [x] **Phase 14.8**：在 `storage.py` 頂端與 `load_project_from_json` 中加入警告註解與 `warnings.warn("StorageService 僅供舊版相容，勿用於新功能")`，確保未來開發者與 Agent 清楚其定位。（✅ 已完成）

### 🎯 階段 D：SQLite 資料庫遷移防禦 (Database Robustness)
> **目標**：建立基礎的資料庫版本號機制，取代脆弱的 `PRAGMA` 手動查核。
- [x] **Phase 14.9**：在 `database.py` 中新增 `schema_version` 表。（✅ 已完成）
- [x] **Phase 14.10**：將原本散落於 `init_db` 中的 `ALTER TABLE` 邏輯，改寫為基於 `schema_version` 的序列化升級函式 (`_upgrade_v1_to_v2`, `_upgrade_v2_to_v3`, `_upgrade_v3_to_v4`, `_upgrade_v4_to_v5`)，確保資料庫升級過程為不可逆且可追溯的 Pipeline。（✅ 已完成）
