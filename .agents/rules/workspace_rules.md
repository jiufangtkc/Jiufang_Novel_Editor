---
trigger: always_on
---

# 九方小說編輯器 — Workspace 開發規則

## 專案慣例

- 絕對遵守事項：無論是發布文案、程式碼註解、程式內容、UI 顯示文字等，只要使用到繁體中文，都必須嚴格使用「台灣語境」的繁體中文。（例如：使用「最佳化」而非「優化」、「專案」而非「項目」等）。
- commit message、程式註解、文件一律使用繁體中文（台灣用語）。
- 所有新增或修改的程式碼應遵循既有的 MVC 分層：
  - `views/`：純 UI 佈局與 signal 發射，不包含業務邏輯。
  - `controllers/`：業務邏輯與事件處理。
  - `services/`：資料存取與外部 API 互動。
  - `models/`：dataclass 定義。
  - `utils/`：與業務無關的工具函式。

## 重要檔案索引

- **架構總覽**：`.agents/docs/ARCHITECTURE.md`
- **交接紀錄**：`.agents/docs/HANDOVER.md`（必讀！包含陷阱提示）
- **測試套件說明**：`.agents/docs/TEST_SUITE.md`（完整自動測試清單與維護規範）
- **開發規劃**：`.agents/docs/ROADMAP.md`


## 修改前必讀

- 動到儲存/讀取流程前，先讀 `HANDOVER.md` 第 3 節「陷阱」。
- 動到卡片系統前，先理解 `CardWidget` 的序列化路徑（Controller 的 `serialize_all_cards` / `deserialize_all_cards`）。
- 動到主題或進度標記前，注意 `theme_manager.py` 中的 `THEME_COLORS` dict 與 `models.models.MARK_COLOR_MAP`。

## 禁止事項

- **不要**將 `services/` 中的 `StorageService` 或 `DatabaseService` 改為直接操作 UI 元件。
- **不要**在 `views/` 的元件中直接 import `MainController`。View 與 Controller 之間的溝通應透過 signal。
- **不要**將打包或發布腳本（例如 `build.bat`、`Jiufang_Novel_Editor.spec`、`setup.iss` 等）放置於專案根目錄。所有打包相關工具與設定檔必須嚴格收納於 `.agents/build/` 中。

## 執行後必做
- **交接紀錄**：`HANDOVER.md`（必做，提醒後面的 agent 必讀！包含已知問題、陷阱等提示）
- **測試清單維護**：若任務中有新增、修改或刪除測試案例，**必須同步更新** `.agents/docs/TEST_SUITE.md`，維持測試項目與說明的一致性。

## 發布規則與文案風格規範 (Release Rules & Copywriting Guidelines)

### 1. 溝通定位與視角
- **同儕創作者交流**：發布文案（包含 README、GitHub Release 說明、更新日誌）必須始終站在「同為長篇小說創作者」的角度出發，禁止使用商業行銷或軟體廠商推銷產品的浮誇語氣。
- **務實與平實**：清楚說明在創作流程中遇到了什麼問題、本次更新如何解決該問題、有哪些已知限制與注意事項。保持謙遜、冷靜與客觀。

### 2. 文案風格與 Agent 溝通禁令
- **嚴格禁止表情符號（Emoji）**：不得在與使用者對話、程式開發溝通、任何公開文案、標題、表格或 Release Notes 中使用 Emoji。
- **保持專業與客觀**：與使用者溝通及設計程式時，禁止使用浮誇用語、盲目讚美或討好式用語（如「太棒了」、「非常精彩」、「震撼推出」、「極致享受」等）。請保持冷靜、務實、專業的態度。
- **繁體中文排版規範**：一律使用台灣繁體中文；中英數字之間必須保留半形空格；中文使用全形標點與直角引號「」；專有名詞遵循官方大小寫。

### 3. 版本發布標準作業流程 (Release SOP)
- **步驟一：全套單元測試驗證**
  發布前必須完整執行 `pytest tests/`，確認所有單元測試 100% 綠燈通過，若有任何失敗項目絕不可強行發布。
- **步驟二：打包建置與檔案收納**
  打包腳本一律收納於 `.agents/build/` 中，嚴禁將 `.spec`、`.bat` 或 `.iss` 移至根目錄。產出的安裝檔（Setup.exe）與綠色版壓縮檔（.zip）應放置於 `pre-release/` 目錄。
- **步驟三：編寫客觀發布說明 (Release Notes)**
  依照同儕創作者視角編寫更新摘要，條列說明各項更新內容，並附上 Windows 安裝版與免安裝版之檔案清單與解壓縮提醒。
- **步驟四：Git 提交、推送與標籤**
  將修改提交至 Git，推送至遠端 `main` 分支，並依版本號建立 Git Tag（如 `v0.1.3-beta`）推送到遠端。
- **步驟五：GitHub Release 發布與檔案上傳**
  在 GitHub 建立對應標籤的 Release（目前階段標記為 Pre-release），上傳 Setup.exe 與 Zip 檔案。
- **步驟六：維護交接文件**
  發布完成後，必須更新 `.agents/docs/HANDOVER.md` 記錄發布細節，若有增修測試需同步更新 `.agents/docs/TEST_SUITE.md`。

## 🤖 10B 等級中小模型專屬防卡死守則 (Anti-loop Rules for 10B LLMs)

為了避免 10B 規模的模型在修改程式碼時陷入 tool-call 死循環（例如 `multi_replace_file_content` 失敗後反覆嘗試），請**所有**接手本專案的 Agent 嚴格遵守以下四條鐵律：

1. **防死循環原則 (No Tool-call Loops)**：
   - 如果使用取代工具 (replace) 修改檔案連續失敗 **2 次**，**必須立即停止嘗試**。
   - 改為使用 `view_file` 重新讀取該程式碼區塊確認實際行數與內容，或者直接終止工具呼叫並向使用者回報困難。嚴禁無意義地反覆盲猜。
2. **讀取優先 (Read Before Write)**：
   - 在修改任何檔案前，強制要求先用 `view_file` 讀取要修改的具體行數範圍。
   - 絕對不要依賴舊的上下文記憶或憑空捏造的程式碼進行替換。
3. **小步快跑 (Small Incremental Steps)**：
   - 每次只處理一個微小的原子任務（例如：只拆分一個函數、只修改一個按鈕顏色）。
   - 處理完後立刻執行 `pytest tests/` 驗證，不要一次修改超過 50 行程式碼。遇到超過 500 行的檔案（如 `project_controller.py`），應考慮拆分而不是大範圍重寫。
4. **避免正則與空白地獄 (Avoid Regex/Whitespace Hell)**：
   - 遇到複雜字串或多行縮排，不要用猜測的空白或正則去匹配。先讀檔抓取精確字串，複製貼上作為 `TargetContent`。