# 九方小說編輯器 (Jiufang Novel Editor)

<div align="center">

<img src="pics/app_icon.png" width="200" alt="Jiufang Novel Editor Logo">

**針對繁體中文長篇小說創作打造的桌面寫作工具**

![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green)
![Database](https://img.shields.io/badge/Storage-SQLite-orange)
![License](https://img.shields.io/badge/License-MIT-purple)

</div>

---

## 專案簡介

> **最後更新：2026-09-10**

有鑑於市面上鮮少專門為繁體中文環境打造的小說創作軟體，加上自己對寫作工具有些特定需求，於是決定試著運用 Antigravity 與各式 AI 助手，動手開發心目中理想的小說寫作平台。

起初這只是一個外行人為了自用而發起的個人企劃。作為一個完全不懂程式設計的「程式麻瓜」，本專案的誕生完全仰賴 AI 時代的技術紅利。絕大部分的程式碼都是由 AI 撰寫而成——主要運用了 Local LLM 進行基礎開發，並借助 Gemini 3.1 Pro (High)、Gemini 3.8 Flash 以及少量 Claude Opus 來解決複雜架構與除錯。

隨著專案逐步迭代，它現在已經成長為一個具備嚴謹 MVC 架構、包含 70 多個模組（近 18,000 行程式碼）、並擁有 257 項全自動化單元測試 100% 覆蓋的「中型桌面應用程式」。
由於受惠於開源社群與 AI 的幫助，我決定將整個專案開源，希望能幫助到同樣在尋找好用寫作工具的創作者，或者吸引更多有志之士一起讓它變得更好。

- **開發這個軟體的核心目的：**
  - **打造順手的編輯器**：一個真正符合長篇小說創作者習慣的專屬寫作環境。
  - **首創 AI 輔助誠信光譜**：無論你是否使用 AI 輔助寫作，系統都會如實記錄「手作原創」與「AI 介入」的比例，幫助作家產出透明的創作日誌，用以自證作品的原創純度。
  - **一站式世界觀管理**：內建樹狀結構的資料卡片集，方便作家有條理地管理龐大複雜的小說世界設定。
  - **出版級匯出**：一鍵匯出標準的 Word 檔、純文字檔或是符合排版規範的 EPUB 電子書，縮短從創作到出版投稿的距離。

作為外行人，本軟體在程式設計上肯定還有許多不周延之處，但能將一個點子實現到如此高度可用、甚至具備企業級測試防護的地步，我已經非常滿足。
謝謝大家來到這個頁面，歡迎下載試用，一起見證這個由程式門外漢與 AI 共同締造的奇妙專案吧！

---

## 功能設計與寫作考量

- **專注寫作**
  - 支援打字機捲動模式（Typewriter Mode），讓當前輸入行保持在視線水平高度。
  - 支援 F11 全螢幕沉浸寫作，可自訂字級大小、版面縮放，並預載芫荽字體。

- **三層樹狀大綱與設定卡片**
  - 提供「卷、章、幕」三層結構，章節樹支援右鍵切換節點類型與同層排序。
  - 獨立的右側設定集面板，可以建立巢狀卡片整理世界觀、人物設定、伏筆與橋段筆記。

- **本機與雲端 AI 輔助**
  - 支援連線至本機離線模型（Ollama、LM Studio），保障寫作資料不離開個人電腦；亦可選用 OpenAI、Gemini、Claude 等雲端 API。
  - 輔助功能偏向設定梳理、人物關係整理與校對建議。
  - 寫作日誌忠實區分「手寫字數」與「AI 續寫字數」，提供清楚透明的數據記錄，便於作者自由決定如何向讀者交代創作歷程。

- **寫作歷程與習慣追蹤**
  - 提供寫作日誌儀表板，記錄每日寫作時長、字數變化與章節長度分佈。
  - 不監控日常鍵盤敲擊、剪貼或退格刪除行為，避免造成多餘的心理負擔。

- **本機資料儲存與備份**
  - 專案均儲存為標準 SQLite 檔案（.db），單一檔案便於攜帶與備份。
  - 具備定時自動暫存與版本快照（Snapshot）機制，降低當機或誤操作造成的損失。
  - 支援自訂專案存檔路徑（方便配合個人雲端硬碟同步），並可匯出為 Word（.docx）、純文字（.txt）、Markdown（.md）或 EPUB 格式。

---

## 軟體架構

本專案採用 MVC（Model-View-Controller）分層架構：

- **View 層 (`views/`)**：純 UI 元件佈局與 Signal 傳遞，不包含業務邏輯。
- **Controller 層 (`controllers/`)**：業務邏輯與流程中樞，由 `MainController` 調度子控制器。
- **Service 層 (`services/`)**：處理 SQLite 資料庫存取、AI API 請求、設定檔與檔案匯出服務。
- **Model 層 (`models/`)**：定義資料結構 Dataclass（如 `JneProject`、`ChapterNode`、`CardNode`）。

---

## 快速開始

### 1. 下載已打包版本
如果是 Windows 使用者且不想自行配置 Python 環境，可直接至 [Releases 頁面](https://github.com/jiufangtkc/Jiufang_Novel_Editor/releases) 下載：
- 自動安裝程式（Setup.exe）
- 免安裝綠色版（.zip，解壓縮後直接執行 `Jiufang_Novel_Editor.exe`）

### 2. 從原始碼執行
- Python 3.10 或更高版本
- Windows 10 / 11

```bash
# 複製專案
git clone https://github.com/jiufangtkc/Jiufang_Novel_Editor.git
cd Jiufang_Novel_Editor

# 建立並啟動虛擬環境 (推薦)
python -m venv .venv
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# Windows (CMD)
.venv\Scripts\activate.bat

# 安裝相依套件
pip install -r requirements.txt

# 啟動軟體
python main.py
```

---

## 自動化測試

專案包含完整的單元測試套件：

```bash
pytest tests/
```

---

## 開源授權

本專案依據 [MIT License](LICENSE) 授權條款開源。
