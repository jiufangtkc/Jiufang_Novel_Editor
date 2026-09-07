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

有鑑於現在很少有專門為了繁體中文環境而開發的小說創作軟體，又因為自己有一些想做的東西，所以決定試著用 Antigravity 開發看看心中想像的自用小說寫作專案平台。
作為一個根本不懂程式的人，有賴於 AI 時代的來臨，起初只是想寫來自用而已，但我本身就是個程式麻瓜，使用 AI 進行開發，略略等於拾人牙慧。於是我將整個專案做成開源軟體，後續或許有機會得到更多人的迴響，再將其做得更好。
這個 GitHub 專案的內容，絕大部分都是 AI 寫的，主要運用了 Local LLM ，前沿模型的部分則用了 Gemini 3.x Flash 以及 3.1 Pro，另外還有少量的 Opus 免費額度。

- **開發這個軟體有幾個目的：**
  - 開發一個我自己用了覺得順手的編輯器。
  - 融入創作者 AI 輔助誠信光譜，讓有使用/不使用 AI 的小說創作者，都可以透過這個小說創作軟體，打造出如實呈現的創作日誌，自證自己的作品的 AI 介入程度，或者是完全的「手作小說」。
  - 一站式的創作環境，作家可以創造樹狀結構的資料集，方便管理自己的小說世界。
  - 一鍵匯出單檔全文，或者一鍵產生基本的 Epub 電子書格式，成就自己心目中的投稿者/出版者樣貌。

作為不懂程式設計的人，本軟體肯定有很多不周延的地方，但以外行人來說，做到能用的地步，我就已經很滿足了。
謝謝大家來到這個頁面，請見證這個程式門外漢弄出來的奇怪專案吧。

**以下內容為 AI 整理的功能說明**

九方小說編輯器是一套以 Python 3.10+ 與 PyQt6 開發的小說創作軟體。主要考量長篇小說寫作時常見的痛點，整合純文字寫作介面、樹狀結構化大綱、卡片式設定集、繁體中文排版檢查，以及可搭配雲端或本機端語言模型的創作輔助功能。

---

## 功能設計與寫作考量

- **純文字專注寫作**
  - 自動攔截並過濾外部貼上的富文本格式，維持純文字內容，避免版面樣式受到干擾。
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
