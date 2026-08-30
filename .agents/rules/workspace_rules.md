---
trigger: always_on
---

# 九方小說編輯器 — Workspace 開發規則

## 專案慣例

- 程式碼變數名、函式名用英文；UI 上顯示給使用者的文字用繁體中文。
- commit message、程式註解、文件一律使用繁體中文（台灣用語）。
- 所有新增或修改的程式碼應遵循既有的 MVC 分層：
  - `views/`：純 UI 佈局與 signal 發射，不包含業務邏輯。
  - `controllers/`：業務邏輯與事件處理。
  - `services/`：資料存取與外部 API 互動。
  - `models/`：dataclass 定義。
  - `utils/`：與業務無關的工具函式。

## 重要檔案索引

- **架構總覽**：`ARCHITECTURE.md`
- **交接紀錄**：`HANDOVER.md`（必讀！包含陷阱提示）
- **開發規劃**：`ROADMAP.md`
- **實施計畫**：`IMPLEMENTATION_PLAN.md`（Phase 1-16 系統規格與修復紀錄）

## 修改前必讀

- 動到儲存/讀取流程前，先讀 `HANDOVER.md` 第 3 節「陷阱」。
- 動到卡片系統前，先理解 `CardWidget` 的序列化路徑（Controller 的 `serialize_all_cards` / `deserialize_all_cards`）。
- 動到主題或進度標記前，注意 `theme_manager.py` 中的 `THEME_COLORS` dict 與 `models.models.MARK_COLOR_MAP`。

## 禁止事項

- **不要**將 `services/` 中的 `StorageService` 或 `DatabaseService` 改為直接操作 UI 元件。
- **不要**在 `views/` 的元件中直接 import `MainController`。View 與 Controller 之間的溝通應透過 signal。
- **不要**刪除 `StorageService`——即使切換到 SQLite，仍需保留 JSON 讀取能力（舊檔相容）。

## 執行後必做
- **交接紀錄**：`HANDOVER.md`（必做，提醒後面的 agent 必讀！包含已知問題、陷阱等提示）

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