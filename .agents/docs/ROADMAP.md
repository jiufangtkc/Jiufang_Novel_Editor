# 九方小說編輯器 — 開發規劃

> 最後更新：2026-09-01（完成 Phase 19，右側資料集面板分欄重構與雲端同步機制）。

## 開發進度總覽

| 階段 | 主題 | 狀態 | 核心成果 |
|---|---|---|---|
| Phase 1 | 資料模型與 dataclass | ✅ 已完成 | 建立 `models/models.py`，定義 UUID 與資料節點 |
| Phase 2 | MVC 架構拆分 | ✅ 已完成 | 拆分 UI 視圖至 `views/`，建立 `MainController` |
| Phase 3 | 儲存層升級（SQLite） | ✅ 已完成 | 建立 `services/database.py`，全面放棄 JSON，暫存與存檔統一採用 SQLite (`.db`) |
| Phase 4 | AI 輔助與卡片生成 | ✅ 已完成 | 支援 OpenAI (ChatGPT)、Gemini、Claude、Grok、Ollama、LM Studio 與思考型模型 |
| Phase 4.5 | 卡片專屬視窗與 Markdown 雙模式 | ✅ 已完成 | 實作 `CardDetailDialog` 與 `Ctrl+M` Markdown模式/純文字切換 |
| Phase 4.6 | 全局開源芫荽字體與持久化 | ✅ 已完成 | 建置 `FontManager`，支援全局與編輯器獨立字型持久化 |
| Phase 5 | 匯出標準化、Controller 拆分與單元測試 | ✅ 已完成 | `python-docx` 匯出、`ExportController`、`AIController` 拆分、`tests/` 測試全數通過 |
| Phase 6 | MainController 二次拆分與資料層統一 | ✅ 已完成 | 拆分為 6 個子控制器，消除 dict↔dataclass 迴圈，清理技術債，13/13 測試全過 |
| Phase 7 | 尋找與取代 + 全文搜尋 | ✅ 已完成 | 嵌入式 `Ctrl+F/H` 搜尋列、`Ctrl+Shift+F` 跨章節搜尋對話框、頂部「編輯」選單 |
| Phase 8 | 沉浸模式 + 大綱模式 | ✅ 已完成 | `F11` 全螢幕無干擾沉浸寫作、`Ctrl+Shift+O` 全書大綱總覽、頂部「檢視」選單 |
| Phase 8.5 | 幕 (Scene) 管理系統 | ✅ 已完成 | scene 節點、幕屬性資料集頁籤整合、DB migration、向後相容 |
| Phase 9 | 多格式匯出 | ✅ 已完成 | docx / txt / md / epub 多格式匯出、自訂路徑與合併/分割模式 |
| Phase 9.5 | PyInstaller 打包 | ❌ 已經取消，不實施 | 打包為 Windows `.exe` 可執行檔 |
| Phase 10 | 版本管理與備份 | ✅ 已完成 | SQLite 快照 (snapshots)、SnapshotDialog、ZIP 專案備份/還原 (BackupService) |
| Phase 11 | AI 對話 + 續寫 | ✅ 已完成 | 多輪對話視窗、編輯器/卡片右鍵整合、續寫（含安全開關與心流警告）、本地模型偵測 |
| Phase 12 | 贅詞偵測 + 儀表板 + AI 介入度 | ✅ 已完成 | 繁中贅詞檢查引擎、白名單與自訂詞庫維護、4大圖表視覺化(趨勢/熱力圖/各章/AI環形圖)、AI 介入度累計追蹤 |
| Phase 13 | 程式碼最佳化與技術債清理 | ✅ 已完成 | 移除冗餘代碼、抽取重複邏輯、統一主題與設定管理、相容 10B LLM 維護規則 |
| Phase 14 | 專案深度檢視與架構防護最佳化 | ✅ 已完成 | 主題一致性 QSS 統一渲染、主視窗拆分瘦身 (MenuBuilder/LeftPanel/RightPanel)、封存 StorageService 寫入、SQLite 版本化遷移 Pipeline |
| Phase 15 | Agent 友善化與技術債清理 | ✅ 已完成 | 文件更新、10B LLM 防卡死守則、Controller 拆分瘦身 (`SnapshotController`, `BackupController`) 與穩定性測試修復 |
| Phase 16 | 全面審計與技術債修復 (Plan 02) | ✅ 已完成 | B1-B6 Bug 修復、全數文件同步、HRCI 長篇分析演算法、縮放引導 |
| Phase 17 | 近期功能強化與 UI 更新 | ✅ 已完成 | 自訂介面欄位佈局、UI縮放記憶、軟體圖示更新、AI角色提取、樹狀面板狀態存檔，126/126 測試通過 |
| Phase 18 | 存檔路徑自訂與雲端同步遷移 | ✅ 已完成 | 支援自訂存檔路徑、自動建立目錄、安全遷移歷史稿件與暫存檔 |
| Phase 19 | 右側資料集面板分欄重構 | ✅ 已完成 | 移除底部多餘控制列，改為上下兩欄垂直分欄（上方樹狀導航，下方卡片內容與幕屬性編輯） |

---

## 實施計畫詳細規格

完整的各階段規格請參見 `IMPLEMENTATION_PLAN.md` 或各階段子文件。
