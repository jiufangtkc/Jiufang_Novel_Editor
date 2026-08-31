# 九方小說編輯器 (Jiufang Novel Editor)

<div align="center">

**專為長篇小說創作者打造的「一站式、純本地、AI 賦能」桌面寫作軟體**

![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green)
![Database](https://img.shields.io/badge/Storage-SQLite-orange)
![License](https://img.shields.io/badge/License-MIT-purple)

</div>

---

## 📖 專案簡介

**九方小說編輯器** 是一套以 Python 3.10+ 與 PyQt6 開發的高效能小說創作軟體。針對長篇創作的痛點設計，結合純文字沉浸寫作、樹狀結構化大綱、卡片式設定集、繁體中文專屬排版校對，以及支援主流雲端與本地端大型語言模型（LLM）的智慧創作助手。

---

## ✨ 核心特色

- 🖋️ **純文字沉浸寫作 (Focus Mode)**
  - 自動攔截並過濾外部富文本格式，維持乾淨純粹的純文字創作環境。
  - 支援 `F11` 全螢幕沉浸寫作、打字機滾動模式（Typewriter Mode）。
  - 支援自訂寫作字型（內建高品質芫荽字體）、字體大小與版面縮放。

- 🌲 **三層樹狀大綱與卡片系統 (Tree & Cards)**
  - 支援「卷、章、幕 (Scene)」三層樹狀階層結構。
  - 獨立巢狀卡片節點，便於管理世界觀、人物設定、劇情伏筆與大綱靈感。

- 🤖 **多模型 AI 創作顧問 (AI Copilot)**
  - 支援 OpenAI (GPT-4o)、Google (Gemini)、Anthropic (Claude)、xAI (Grok)。
  - 支援本機離線模型（Ollama、LM Studio），保障作品隱私不外洩。
  - 內建小說評析、人物關係提取、世界觀整理、時間線梳理與智慧續寫功能。

- 📊 **即時統計與繁體中文校對 (Stats & Linter)**
  - 精確統計中文字數、標點符號、閱讀時間估算與每日碼字進度追蹤。
  - 內建繁體中文贅詞檢查與語病修正建議。

- 💾 **純本地 SQLite 資料庫與雙重防護 (Data Safety)**
  - 所有專案均以標準 SQLite (`.db`) 格式儲存，單檔便攜、高讀寫效能。
  - 內建定時自動暫存與版本快照（Snapshot）機制，保障創作心血不遺失。
  - 支援一鍵 ZIP 專案打包備份與多格式匯出（Word `.docx`、純文字 `.txt`、Markdown `.md`、EPUB）。

---

## 🛠️ 技術架構

本專案遵循嚴格的 **MVC (Model-View-Controller)** 架構設計：

- **View 層 (`views/`)**：純 UI 元件佈局與 Signal 傳遞，不包含任何業務邏輯。
- **Controller 層 (`controllers/`)**：業務邏輯中樞，透過 `MainController` 統一調度 11 個子控制器。
- **Service 層 (`services/`)**：負責 SQLite 資料庫操作、AI API 請求、設定檔與備份服務。
- **Model 層 (`models/`)**：定義資料結構 Dataclass（如 `JneProject`、`ChapterNode`、`CardNode`）。

---

## 🚀 快速開始

### 1. 系統需求
- Python 3.10 或更高版本
- Windows 10 / 11（已提供 Windows 專用安裝程式支援）

### 2. 安裝步驟

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

# 安裝依賴套件
pip install -r requirements.txt
```

### 3. 啟動軟體

```bash
python main.py
```

---

## 🧪 執行自動化測試

專案具備完整的自動化單元測試套件：

```bash
pytest tests/
```


---

## 📄 開源授權

本專案依據 [MIT License](LICENSE) 授權條款開源。
