# 九方小說編輯器 — 交接文件

> 最後更新：2026-08-30，完成「Phase 16：全面審計與技術債修復 (Plan 02)」，85/85 個單元測試全數通過。

## 0. ⚠️ 專案交接守則 (CRITICAL RULES)

1. **嚴格的範圍控制**：每次修改聚焦於指派任務檔案，不要發散，不要隨意大範圍破壞架構。
2. **每次結束必寫交接記錄**：當完成任務，**必須**修改本 `HANDOVER.md` 的「第 4 節 (目前執行狀態)」，清楚寫下變更內容與下一個 Agent 的指引。
3. **MVC 架構原則**：`views/` 保持純 UI、`controllers/` 處理業務邏輯、`services/` 專司資料存取。
4. **遇錯即停**：如果測試未通過，請立即排查修復後再進入下一步。

---

## 1. 你接手的是什麼

這是一個基於 Python + PyQt6 的桌面端小說寫作軟體，目前 Phase 1 到 Phase 16 已經全部開發完畢且完成全方位最佳化與防護：
- **核心寫作與結構**：樹狀目錄、巢狀卡片系統、純文字無格式編輯、沉浸模式、大綱總覽模式、場景/幕管理。
- **儲存與備份**：純 SQLite 儲存（含 `schema_version` 版本化 Migration Pipeline）、自動暫存優先載入、版本快照管理 (`SnapshotController`)、ZIP 備份/還原 (`BackupController`)、垃圾桶管理。
- **寫作輔助與檢查**：尋找與取代、全文檢索、多格式匯出 (docx/txt/md/epub)。
- **AI 整合**：多輪對話、智慧續寫（含防護開關）、本機模型偵測 (Ollama/LM Studio)。
- **數據追蹤**：寫作儀表板（趨勢折線圖、熱力圖、各章長條圖、AI 介入度環形圖）、AI 介入度記錄 (手寫 vs AI)。
- **文風檢查**：繁中贅詞偵測（公文冗贅、被動弱句、高頻虛詞、相鄰重複詞）、白名單與自訂詞庫。
- **架構最佳化 (Phase 13~15)**：資料模型去冗餘、集中主題對應 (`THEME_NAME_MAP`)、共用暫存檔時間序排序 (`utils/file_utils.py`)、舊版專案 JSON 遷移邏輯分離、Controller 拆分瘦身、10B LLM 防卡死守則落實。
- **系統全面審計與品質修復 (Phase 16 - Plan 02)**：
  - 徹底解決寫作日誌 AI 介入度欄位存讀丟失問題 (B1/B2)。
  - 補齊垃圾桶還原時 scene 節點字數回填 (B3) 與主題切換時 scene 節點圖示更新 (B4)。
  - 標記色彩常數集中化 (`models.MARK_COLOR_MAP`)，消除多處重複硬編碼 (D1)。
  - 快照系統完整序列化目標字數 `target_word_count` (D4)。
  - 全面同步架構與規劃文件，單元測試擴充至 85 項並全數通過。

---

## 2. 重構與開發歷史

```
原始狀態 --- main.py 3000+ 行的 God Object
    |
    ├── Phase 1 ~ Phase 5：基礎架構與 API 整合
    ├── Phase 6：MainController 二次拆分（6 個子控制器），資料層統一
    ├── Phase 7：尋找與取代 + 跨章節全文搜尋
    ├── Phase 8 ~ 8.5：沉浸模式 + 大綱模式 + 幕管理系統
    ├── Phase 9：多格式匯出
    ├── Phase 10：版本管理與專案備份
    ├── Phase 11：AI 對話模式與進階整合
    ├── Phase 12：贅詞偵測 + 寫作儀表板升級 + AI 介入度記錄
    |
    ▼── 功能開發完畢，進入最佳化階段 ──
    |
    ├── Phase 13：技術債與冗餘代碼清理（✅ 全部完成）
    ├── Phase 14：專案深度檢視與架構防護最佳化（✅ 全部完成）
    ├── Phase 15：Agent 友善化與 Controller 拆分（✅ 全部完成）
    │   ├── 15.1 拆分 SnapshotController 與 BackupController
    │   ├── 15.2 建立 10B LLM 防卡死守則
    │   └── 15.3 修復右側面板收合與 UI 縮放 Bug
    └── Phase 16：全面審計與技術債修復 Plan 02（✅ 全部完成）
        ├── 16.1 修復 WritingLogEntry AI 介入度存讀雙殺 (B1/B2)
        ├── 16.2 修正 restore_cache 與 update_icons 之 scene 節點支援 (B3/B4)
        ├── 16.3 集中 MARK_COLOR_MAP 標記色碼 (D1)
        ├── 16.4 快照序列化補齊 target_word_count (D4)
        └── 16.5 文件全面同步與單元測試擴充 (85/85 通過)
```

---

## 3. 需要特別注意的陷阱與設計規則

### 陷阱 1：儲存架構已完全廢棄 JSON 格式
- 專案存檔、另存新檔、`Temp_doc/` 自動暫存檔全面採用 SQLite (`.db`)。
- `services/storage.py` 僅供向後相容舊檔遷移使用，寫入方法已徹底封死。

### 陷阱 2：AI 請求必須在非同步執行緒
- 絕對不要在 Qt 主執行緒同步呼叫 API，避免介面卡頓。在單元測試中若測試 UI 流程，應 mock worker.start。

### 陷阱 3：API Key 與專案檔案隔離
- `ai_settings.json` 與 `lint_settings.json` 為本機全域設定，不會寫入 SQLite 專案資料庫中。

### 陷阱 4：子控制器之間不得互相 import
- 所有子控制器在 `__init__` 接收 `main_controller` 實例（`self.mc`），跨控制器操作一律透過 `self.mc.xxx` 存取，嚴禁子控制器互相 import，防止 Circular Import。

### 陷阱 5：JneProject 資料模型層級
- 專案字型、書名、大綱設定皆統一放置於 `project.project_info` (`ProjectInfo` dataclass) 中，請勿在 `JneProject` 頂層新增冗餘 getter/setter 或屬性。

### 陷阱 6：QSS Template 字串格式化大括號轉義
- `theme_manager.py` 的 `BASE_THEME_TEMPLATE` 會使用 `format(**colors)`，CSS 選擇器內的普通大括號必須寫為雙大括號 `{{` 與 `}}`，僅有要被代換的變數（如 `{status_bar_bg}`）保留單大括號。

### 陷阱 7：章節標記色碼統一常數
- 章節與幕的進度標記色碼（Draft, 1st Edit, 2nd Edit, Final, Discarded）一律統一引用 `models.models.MARK_COLOR_MAP`，禁止在 Controller 或 View 中自行硬編碼字典。

---

## 4. 目前執行狀態與下一步指引 (CURRENT STATUS & NEXT STEPS)

- **本次完成事項**：
  1. **軟體圖示更新與多格式生成**：
     - 將使用者提供之九宮格 + 貓爪 + 書本新版圖示完成高精準度圓角去背處理（抗鋸齒遮罩移除棋盤格殘影）。
     - 生成 1024x1024 高解析度與 512x512 標準透明背景 PNG (`resources/icons/app_icon_1024.png`, `resources/icons/app_icon.png`)。
     - 生成完整 Windows 多層解析度 ICO 檔案 (`resources/icons/app_icon.ico`，包含 16x16, 24x24, 32x32, 48x48, 64x64, 128x128, 256x256)。
     - 整合至視窗圖示 (`main.py`) 與 PyInstaller 打包腳本 (`Jiufang_Novel_Editor.spec`, `build.bat`)。
  2. **測試驗證**：85/85 個單元測試全數通過。
- **當前任務狀態**：**新版軟體圖示已轉換並全域套用完畢。**
- **下一個 Agent 的任務指引**：
  專案目前架構穩固、測試完整且軟體圖示已全面更新。後續如有新增功能需求，請依循既有 MVC 分層架構與 10B 模型防卡死守則（見 `workspace_rules.md`）進行小步推進。

