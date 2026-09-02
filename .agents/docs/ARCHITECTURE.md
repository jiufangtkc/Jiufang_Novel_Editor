# 九方小說編輯器 (Jiufang Novel Editor) — 系統總體架構與 Agent 導航手冊

> 最後更新：2026-09-03
> 本文件專為後續接手的開發者與 AI Agent 設計，提供由上而下的「上帝視角 (Bird's-eye view)」，協助快速掌握專案全貌與架構紅線。

## 一、 專案規模與定位

本專案屬於**中型 (Medium-scale)** 桌面端應用程式：
- **技術棧**：Python 3.10+、PyQt6 (GUI)、SQLite (本地資料庫)。
- **架構特徵**：擁有超過 30 個 Python 模組、143 項完整單元測試、嚴格的 MVC 分層架構。
- **核心定位**：為長篇小說創作者打造的「一站式、純本地、AI 賦能」桌面寫作軟體，強調無干擾純文字寫作與結構化資料管理。

---

## 二、 核心架構：嚴格的 MVC 模式 (Strict MVC)

專案採用嚴格分離的 MVC (Model-View-Controller) 設計模式，所有模組依職責劃分，**嚴禁跨界操作**。

### 1. 依賴流向 (Dependency Flow)
`Views (UI)` ↔ `Controllers (邏輯)` → `Services (資料/外部服務)` → `Models (資料結構)`
- **View** 只負責觸發 Signal，不處理任何商業邏輯。
- **Controller** 負責接收 View 的 Signal，呼叫 Service 處理資料，再將結果更新回 View。
- **Service** 只負責 I/O 操作 (資料庫、API、檔案讀寫)，完全不知道 UI 的存在。

### 2. 目錄結構與職責地圖 (Directory Map)

```text
Jiufang_Novel_Editor/
├── main.py                         # 系統進入點 (Entry Point)：初始化 QApplication -> MainWindow -> MainController
├── models/                         # [Model 層] 純資料結構 (Data Structures)
│   └── models.py                   # 定義 JneProject, ProjectInfo, ChapterNode, CardNode 等 dataclass 與 MARK_COLOR_MAP
├── views/                          # [View 層] 視覺與互動介面 (UI Components)
│   ├── main_window.py              # 應用程式主視窗（僅負責頂層 Layout 組合與 Signal 橋接）
│   ├── components/                 # 可重複使用的 UI 獨立元件 (如 LeftPanelView, RightPanelView, MenuBuilder, 編輯器, 卡片, 圖表)
│   └── dialogs/                    # 獨立的彈出視窗 (如 AI 對話框、檢查器、設定視窗)
├── controllers/                    # [Controller 層] 業務邏輯中樞 (Business Logic)
│   ├── main_controller.py          # ★ 核心聚合器：持有所有子控制器實例，管理共享狀態
│   └── (其他 12 個子控制器)          # 各司其職 (Tree, Editor, Search, Stats, Project, Autosave, Theme, Card, Export, AI, Snapshot, Backup)
├── services/                       # [Service 層] 資料存取與外部通訊 (Data & External API)
│   ├── database.py                 # ★ 唯一真實資料來源 (Source of Truth)：處理 SQLite (.db) 的 CRUD 操作
│   ├── database_migrations.py      # SQLite schema_version 版本化升級與 Migration Pipeline
│   ├── storage.py                  # 僅限舊版 JSON 專案向後相容讀取（已封存寫入功能）
│   ├── ai_service.py               # 處理 OpenAI/Gemini/Claude/本地端 LLM 的 API 請求
│   ├── app_settings_service.py     # 應用程式全域設定讀取與儲存
│   ├── backup_service.py           # ZIP 專案打包與還原備份
│   └── lint_service.py             # 繁中贅詞與文風檢查
├── utils/                          # 通用工具模組 (與特定業務邏輯無關)
│   ├── font_manager.py             # 全域字型 (芫荽字體) 管理
│   ├── theme_manager.py            # 暗色主題色彩定義與樣式管理
│   └── file_utils.py               # 檔案路徑與時間戳排序工具
├── tests/                          # 自動化測試套件 (Pytest)，覆蓋率高
├── story/                          # 使用者正式專案存檔位置 (.db)
├── Temp_doc/                       # 系統自動暫存位置 (.db，上限 100 個)
└── Export/                         # 匯出產物位置 (.docx, .txt, .md, .epub)
```

---

## 三、 子控制器通訊機制 (Inter-Controller Communication)

這是本專案**最重要**的架構防禦機制，設計用來解決中型專案常見的「循環依賴 (Circular Import)」問題。

### 🚨 絕對禁止 (CRITICAL RULE)
**子控制器之間（例如 `TreeController` 與 `EditorController`）絕對禁止互相 `import`！**

### ✅ 標準做法 (The Standard Way)
1. 所有的子控制器都在 `MainController.__init__` 中被實例化。
2. 每個子控制器的 `__init__` 都必須接收 `main_controller` 的參考，並儲存為 `self.mc`。
3. 當需要跨控制器呼叫時，一律透過 `self.mc` 作為橋樑。
   - 例如：`TreeController` 需要更新編輯器內容時，呼叫 `self.mc.editor_controller.update_editor(text)`。

---

## 四、 資料持久化策略 (Persistence Strategy)

### 1. SQLite 為王 (SQLite is the Source of Truth)
- 專案在 Phase 3 經歷了重大重構，**已完全廢棄 JSON 作為專案存檔格式**。
- 所有的暫存檔 (`Temp_doc/`) 與正式存檔 (`story/`) 皆為標準的 SQLite 資料庫 (`.db`)。
- `services/database.py` 內建 `schema_version` 版本化 Migration Pipeline，升級可追溯且不可逆。
- `services/storage.py` 僅作為**歷史包袱的相容讀取**（已封死寫入路徑），嚴禁在其中開發新功能。

### 2. Dataclass 作為記憶體內快取
- 軟體運行時，整個專案的資料樹會被反序列化為 `models.py` 中的 `JneProject` dataclass 結構（存在記憶體中）。
- 使用者每次觸發儲存（或自動暫存）時，`database.py` 會將當下的 `JneProject` 狀態寫入 SQLite。
- **專案屬性管理**：所有與專案相關的屬性（如字型、字體大小、目標字數）皆存放在 `JneProject.project_info` (`ProjectInfo` 結構) 中，嚴禁在 `JneProject` 頂層新增或移除屬性。

### 3. 全域應用設定 (App Settings)
- 軟體本身的偏好設定（非專案級別），如視窗大小、AI API Keys、文風檢查白名單等，獨立存放在根目錄的 `.json` 檔中（`ai_settings.json`, `app_settings.json`, `lint_settings.json`）。
- 這些設定**不會**跟隨 SQLite 專案檔移動。

---

## 五、 六大核心子系統概覽

1. **樹狀章節與卡片系統 (Tree & Card System)**
   - 樹狀節點 (`ChapterNode`) 支援卷、章、幕 (Scene) 三層級。
   - 卡片節點 (`CardNode`) 採用獨立巢狀結構，負責管理大綱、設定與人物卡。
2. **純文字專注編輯器 (Pure Text Editor)**
   - 自訂 `JneTextEdit`，攔截所有富文本貼上 (`setAcceptRichText(False)`)，維持極簡純文字。支援 Markdown 雙模式與 F11 沉浸寫作。
3. **版本快照與備份 (Snapshot & Backup)**
   - 內建基於 SQLite 表格的輕量級版本快照 (`snapshots` 表)。
   - 支援將整個 `.db` 打包成 ZIP 並還原。
4. **多模型 AI 助手 (Multi-provider AI)**
   - 支援線上 (OpenAI/Gemini/Claude/Grok) 與本地端 (Ollama/LM Studio)。
   - 包含多輪對話 (`AIChatDialog`) 與智慧續寫，強制在非同步 `QThread` (`AIWorker`) 執行以防 UI 阻塞。
5. **數據儀表板與日誌 (Dashboard & Logs)**
   - 寫作歷程儲存於 SQLite `writing_logs` 表，包含 AI 介入度追蹤。
   - `WritingChartView` 提供 GitHub 打卡熱力圖、長條圖、環形圖等多維度視覺化。
6. **文風與贅詞引擎 (Linting Engine)**
   - 獨立的 `LintService`，透過正則表達式 (Regex) 掃描四種繁體中文寫作常見瑕疵（公文冗贅、被動語態、高頻虛詞、疊字），並支援白名單過濾。

---

## 六、 Agent 開發指南 (Guide for Future Agents)

當你準備開始修改程式碼時，請遵循以下檢查清單：
1. **讀取交接紀錄**：永遠先看 `HANDOVER.md` 的第 3、4 節，確認目前是否有未知的陷阱或尚未完成的重構。
2. **定位邏輯位置**：
   - 如果是改 UI 顏色或排版 ➡️ `views/` 或 `utils/theme_manager.py`
   - 如果是改按鈕點擊後的行為 ➡️ `controllers/`
   - 如果是改存檔內容或資料庫欄位 ➡️ `services/database.py` 與 `models/models.py`
3. **單點修改原則**：專案已達 10B 本地模型可維護的最佳化狀態，請每次僅針對單一功能進行最小範圍的修改，避免「牽一髮而動全身」的大規模重構。
4. **測試保證**：所有的邏輯修改後，必須執行 `python -m pytest tests/ -v` 確保現有 143 項核心測試不被破壞。

### 🤖 針對 10B 等級模型的特別守則 (Rules for 10B LLMs)
由於本專案採用嚴格 MVC 且部分控制器（如 `main_controller.py`, `project_controller.py`）規模較大，10B 等級模型在進行工具呼叫 (Tool Calls) 時容易迷失或產生幻覺，陷入無盡的取代失敗循環。請務必遵守：
- **禁止猜測行號或內容**：在進行 `replace_file_content` 或 `multi_replace_file_content` 前，**絕對要先使用 `view_file`** 確認該片段目前的真實內容。
- **2 次失敗即停**：如果檔案修改工具連續失敗兩次，**請立即停止嘗試**，改為回報問題或重新讀取整個檔案，嚴禁死循環。
- **微小化修改**：不要試圖一次重寫整個檔案。只修改你確定的那個函式或那幾行程式碼。
- **避免正則地獄**：遇到複雜的多行字串，不要用正則去猜測空白，直接從 `view_file` 複製出來作為 `TargetContent`。
