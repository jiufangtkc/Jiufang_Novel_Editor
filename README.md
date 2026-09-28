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

## 專案緣起與初衷

> **最後更新：2026-09-28**

這是一套為了繁體中文長篇小說創作而打造的桌面端寫作工具。

我是九方思想貓，一位長篇小說創作者。在實際撰寫數十萬字長篇小說的過程中，常遇到市面既有寫作工具無法完全契合中文創作習慣的痛點——例如繁體中文直角引號與段首縮排的相容性、複雜多線的世界觀卡片管理、章節樹的三層架構（卷、章、幕），以及長篇創作中對於資料完全本機化儲存與防崩潰機制的嚴苛要求。

本專案並非商業軟體公司的產品，而是我帶著長篇小說創作者的實務需求與理念，借助現代 AI 輔助開發工具（Antigravity、Local LLM、Gemini 等）協同編寫而成的開源作品。專案採用嚴謹的 MVC 分層架構，具備完整的 SQLite 資料庫管理、70 多個功能模組，以及 262 項自動化單元與整合測試（100% 通過驗證）。

我將這套工具開源釋出，希望能提供給同樣投入長篇小說創作的同儕朋友一個安靜、穩定且順手的寫作環境。

---

## 核心設計理念

- **符合長篇小說習慣的結構管理**
  - 提供「卷、章、幕」三層樹狀大綱，支援節點右鍵轉換類型、整卷複製與同層自由排序。
  - 獨立的右側設定資料集面板，可建立多層巢狀卡片有條理地管理人物設定、世界觀地理、勢力關係與伏筆筆記。

- **客觀透明的創作日誌（誠信指標）**
  - 無論是否在寫作中運用 AI 輔助，系統皆忠實區分並記錄「手寫字數」與「AI 續寫字數」，產出透明客觀的創作日誌，供作者自由決定如何向讀者自證創作歷程。

- **專注寫作體驗**
  - 支援打字機捲動模式（Typewriter Mode），讓輸入游標恆定保持在視線水平高度。
  - 支援 F11 全螢幕沉浸寫作，可自訂字級大小、版面縮放，並預載開源「芫荽」字體。

- **純本機資料儲存與防護**
  - 專案資料統一採標準 SQLite 資料庫（.db）儲存，單檔便於個人手動備份與雲端同步（如 Dropbox、Google Drive）。
  - 內建定時自動暫存、崩潰自動恢復（Crash Recovery）與多版本快照機制，確保稿件不受無預警異常干擾。
  - 開啟專案時自動記憶並復原上次編輯的章節節點與游標位置，保持無縫接續的寫作心流。

- **出版與投稿標準匯出**
  - 支援一鍵將整部作品匯出為排版標準的 Word（.docx）、符合排版規範的 EPUB 電子書、Markdown（.md）以及純文字（.txt）檔案，縮短自完稿至出版投稿的轉換流程。
  - 支援設定資料集獨立匯出精靈，深層卡片動態標題降級排版，方便製作設定集閱讀本。

- **本機與雲端 AI 輔助**
  - 支援連線至本機離線模型（Ollama、LM Studio），保障寫作資料完全不離開個人電腦；亦可自由選用 OpenAI、Gemini、Claude 等雲端 API。
  - 輔助功能偏向設定梳理、人物關係整理與排版校對建議，不干擾創作者的主體性。

---

## 軟體架構

本專案採用嚴格 MVC（Model-View-Controller）分層架構：

- **View 層 (`views/`)**：純 UI 元件佈局與 Signal 傳遞，不包含業務邏輯。
- **Controller 層 (`controllers/`)**：業務邏輯與流程中樞，由 `MainController` 調度子控制器。
- **Service 層 (`services/`)**：處理 SQLite 資料庫存取、AI API 請求、設定檔與檔案匯出服務。
- **Model 層 (`models/`)**：定義資料結構 Dataclass（如 `JneProject`、`ChapterNode`、`CardNode`）。

---

## 快速開始

### 1. 下載已打包版本
Windows 使用者可直接至 [Releases 頁面](https://github.com/jiufangtkc/Jiufang_Novel_Editor/releases) 下載：
- 自動安裝程式（Setup.exe）
- 免安裝綠色版（.zip，解壓縮後直接執行 `Jiufang_Novel_Editor.exe`）

### 2. 從原始碼執行
- Python 3.10 或更高版本
- Windows 10 / 11

```powershell
# 複製專案
git clone https://github.com/jiufangtkc/Jiufang_Novel_Editor.git
cd Jiufang_Novel_Editor

# 建立並啟動虛擬環境 (推薦)
python -m venv .venv
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
# Windows (CMD)
.\.venv\Scripts\activate.bat

# 安裝相依套件
pip install -r requirements.txt

# 啟動軟體
python main.py
```

---

## 自動化測試

專案包含完整的單元與整合測試套件（41 個測試模組、262 項測試，維持 100% 綠燈）：

```powershell
# Windows 繁體中文環境下執行完整測試
py -m pytest tests/
```

---

## 交流與授權

- **問題回報與交流**：若在創作過程中遇到問題或有實務寫作流程建議，歡迎至 [GitHub Issues](https://github.com/jiufangtkc/Jiufang_Novel_Editor/issues) 提出交流討論。
- **開源授權**：本專案依據 [MIT License](LICENSE) 授權條款開源。
