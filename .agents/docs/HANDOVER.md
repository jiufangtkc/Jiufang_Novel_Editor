# 九方小說編輯器 — 交接文件

> 最後更新：2026-09-01，完成 Phase 20「系統重構、模組化與狀態防護加固」，全部 127 項單元測試全數通過。

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

---

## 4. 目前執行狀態與下一步指引 (CURRENT STATUS & NEXT STEPS)

- **本次完成事項 (Phase 20)**：
  1. **`services/database_migrations.py` 獨立模組**：將 SQLite 資料庫 v1～v9 的完整 Schema 升級邏輯、版本檢測與 Migration Pipeline 獨立抽離，`DatabaseService` 大幅瘦身至更清晰高內聚的狀態。
  2. **`controllers/autosave_controller.py` 獨立控制器**：將自動暫存 (`save_temp_doc`)、排程計時器、暫存檔案清理 (`clean_files_limit`)、崩潰還原 (`auto_load_latest_temp`) 與暫存設定對話框完全抽離，減輕 `ProjectController` 負擔。
  3. **UI 狀態同步與防護加固**：在卡片更名 (`rename_card`) 時，加入對右側下方正處於編輯狀態之面板標題的連動同步，防止因點擊儲存造成舊標題覆寫。
  4. **單元測試全數通過**：全套 **127 項測試 100% 通過**（含新增之連動同步測試與子控制器初始化驗證）。
- **當前任務狀態**：Phase 20 系統重構、模組化與狀態防護加固已全部實作完畢並通過驗證。
- **下一個 Agent 的任務指引**：
  1. 軟體核心功能、MVC 分層、各子模組規模與單元測試已達到極度穩健的最佳狀態。
  2. 後續可根據使用者提出的具體新功能需求（如更多自訂匯出範本、新主題配色、AI 提示詞自訂庫等）進行持續迭代。
  3. 任何修改請繼續嚴格遵守 10B LLM 防卡死守則與 MVC 邊界規範。若需打包釋出，僅可使用 `.agents/build/build.bat`。

