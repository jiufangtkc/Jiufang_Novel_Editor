# 九方小說編輯器 — 全面審計報告與技術債修復計畫

> 審計日期：2026-08-30
> 審計範圍：所有 MD 文件、全部 12 個 Controller、6 個 Service、4 個 Utils、16 個測試檔案
> 測試結果：**83/83 全數通過**（8.78s）

---

## 一、MD 文件現況評估與必要更新

### 需要更新的文件

| 文件 | 問題 | 狀態 |
|---|---|---|
| [ARCHITECTURE.md](file:///c:/Users/yenfu/OneDrive/JiuFangTKC/655.AI_agent/Jiufang_Novel_Editor/ARCHITECTURE.md) | 1. 最後更新標記停在 2026-08-25，應更新至 2026-08-30 | 需更新 |
| | 2. 第 10 行聲稱「68 項完整單元測試」，實際已為 **83 項** | 需更新 |
| | 3. 第 37 行聲稱「其他 9 個子控制器」，Phase 15 後已拆出 `SnapshotController` 與 `BackupController`，應為 **11 個子控制器** | 需更新 |
| | 4. 未提及 `app_settings_service.py` 與 `backup_service.py` 這兩個 service | 需更新 |
| [HANDOVER.md](file:///c:/Users/yenfu/OneDrive/JiuFangTKC/655.AI_agent/Jiufang_Novel_Editor/HANDOVER.md) | 1. 最後更新標記停在 2026-08-27 | 需更新 |
| | 2. 聲稱「68/68 個單元測試」，應為 **83/83** | 需更新 |
| | 3. 第 4 節內容為舊版的修復紀錄，需反映最新狀態 | 需更新 |
| | 4. 未記錄本次發現的 bug（見第二節） | 需更新 |
| [ROADMAP.md](file:///c:/Users/yenfu/OneDrive/JiuFangTKC/655.AI_agent/Jiufang_Novel_Editor/ROADMAP.md) | 1. 最後更新停在 2026-08-27 | 需更新 |
| | 2. Phase 15 狀態為「進行中」，但根據 `IMPLEMENTATION_PLAN.md` 已標記為完成 | 需更新 |
| [IMPLEMENTATION_PLAN.md](file:///c:/Users/yenfu/OneDrive/JiuFangTKC/655.AI_agent/Jiufang_Novel_Editor/IMPLEMENTATION_PLAN.md) | 1. 第 3 行規畫日期停在 2026-08-25，狀態標記不一致 | 需更新 |
| | 2. 第 45 行「二、階段依賴與執行順序」標題重複出現兩次 | 需修復 |
| [OPTIMIZATION_PLAN.md](file:///c:/Users/yenfu/OneDrive/JiuFangTKC/655.AI_agent/Jiufang_Novel_Editor/OPTIMIZATION_PLAN.md) | 全部 10 個子階段已完成，但文件仍具參考價值（歷史紀錄） | 不需更新 |
| [workspace_rules.md](file:///c:/Users/yenfu/OneDrive/JiuFangTKC/655.AI_agent/Jiufang_Novel_Editor/.agents/rules/workspace_rules.md) | 1. 「重要檔案索引」中 IMPLEMENTATION_PLAN 描述為「Phase 6-12 執行規格」，應更新 | 需更新 |
| | 2. 「修改前必讀」中第一條引用了 `HANDOVER.md` 的舊節號 | 需更新 |
| | 3. 缺少對新增 Controller（Snapshot、Backup）的提及 | 需更新 |
| | 4. 缺少本次審計發現之已知 Bug 的警示 | 需更新 |

---

## 二、發現的 Bug 與技術債

### Bug 清單

| 編號 | 嚴重度 | 位置 | 問題描述 |
|---|---|---|---|
| **B1** | **高** | [project_controller.py:265-270](file:///c:/Users/yenfu/OneDrive/JiuFangTKC/655.AI_agent/Jiufang_Novel_Editor/controllers/project_controller.py#L265-L270) | **`_build_jne_project()` 序列化 WritingLogEntry 時遺漏 AI 介入度欄位**。僅複製 `date`, `duration`, `word_count`，完全丟失 `ai_continuation_count`, `ai_continuation_chars`, `ai_chat_count` 三個欄位。**後果**：每次存檔（暫存/正式/快照），所有 AI 介入度數據歸零，寫作儀表板的 AI 環形圖數據永久遺失。 |
| **B2** | **高** | [project_controller.py:370-373](file:///c:/Users/yenfu/OneDrive/JiuFangTKC/655.AI_agent/Jiufang_Novel_Editor/controllers/project_controller.py#L370-L373) | **`load_project_data()` 反序列化 WritingLogEntry 時同樣遺漏 AI 介入度欄位**。與 B1 構成「存讀雙殺」，即便資料庫中有正確數據也會被載入時丟棄。 |
| **B3** | **中** | [tree_controller.py:370](file:///c:/Users/yenfu/OneDrive/JiuFangTKC/655.AI_agent/Jiufang_Novel_Editor/controllers/tree_controller.py#L370) | **`restore_cache()` 僅處理 `type == "file"` 的節點，忽略 `type == "scene"` 節點**。當從垃圾桶還原含有 scene 節點的章節時，scene 節點的字數不會被回填到 `file_word_stats`，導致全文字數統計偏低。 |
| **B4** | **中** | [theme_controller.py:318](file:///c:/Users/yenfu/OneDrive/JiuFangTKC/655.AI_agent/Jiufang_Novel_Editor/controllers/theme_controller.py#L318) | **`update_icons()` 中的 `update_tree_item` 僅處理 `type == "file"` 的圖示更新，忽略 `type == "scene"` 節點**。切換主題時，scene 節點的圖示不會跟隨主題配色更新（不會崩潰，但視覺上不一致）。 |
| **B5** | **低** | [card_controller.py:317](file:///c:/Users/yenfu/OneDrive/JiuFangTKC/655.AI_agent/Jiufang_Novel_Editor/controllers/card_controller.py#L317) | **右鍵選單「全部展開」的 lambda 綁定邏輯多餘**。第 317 行 `act_expand.triggered.connect(item.setExpanded if True else None)` 始終為真，多連接了一次 `setExpanded` method reference（非 callable with argument），不會崩潰但屬於冗餘程式碼。 |
| **B6** | **低** | [project_controller.py](file:///c:/Users/yenfu/OneDrive/JiuFangTKC/655.AI_agent/Jiufang_Novel_Editor/controllers/project_controller.py) | **`current_project_path` 未在 `__init__` 中初始化**。使用 `hasattr(self, 'current_project_path')` 檢查（L213, L626），但若 `auto_load_latest_temp` 走 Temp_doc 路徑成功載入時也會設定 `self.current_project_path`（L178），在該 attribute 未定義的情況下直接賦值雖不會報錯，但缺乏初始化是一種程式碼氣味。 |

### 技術債清單

| 編號 | 影響 | 位置 | 描述 |
|---|---|---|---|
| **D1** | 可維護性 | `theme_controller.py` L320-322, `tree_controller.py` L410-412, `project_controller.py` L410-413 | **`color_map` 進度標記色碼重複定義三次**。目前分別在 `update_icons`, `show_tree_context_menu`, `load_project_data` 中各自硬編碼一份相同的 mark → color 對應表。應抽取至 `models/models.py` 或 `utils/` 中統一定義。 |
| **D2** | 可維護性 | [project_controller.py](file:///c:/Users/yenfu/OneDrive/JiuFangTKC/655.AI_agent/Jiufang_Novel_Editor/controllers/project_controller.py) | **檔案仍有 648 行**。Phase 15 已拆出 Snapshot 與 Backup，但 `get_active_db_path` 仍在 ProjectController 中（雖合理，但 L620-647 的 Phase 10 區段標題註解已過時）。 |
| **D3** | 可維護性 | [database.py](file:///c:/Users/yenfu/OneDrive/JiuFangTKC/655.AI_agent/Jiufang_Novel_Editor/services/database.py) | **`database.py` 有 810 行**，涵蓋 Schema Migration、CRUD、Snapshot、Proofread CRUD。隨著功能增加，應考慮拆分為 `database_migration.py` 等子模組。但當前功能穩定，非緊急。 |
| **D4** | 資料完整性 | `_project_to_dict` / `_dict_to_project` | 快照系統的 `_project_to_dict` 中 `project_info` 區段未序列化 `target_word_count`，還原快照後會遺失專案目標字數設定。 |

---

## 三、修復計畫

### Phase 16：Bug 修復與文件同步

> [!IMPORTANT]
> 以下修改不涉及新功能開發，僅修復已發現的 bug 與同步文件至最新狀態。

#### 16.1 修復 B1 + B2：WritingLogEntry AI 介入度欄位存讀雙殺

**修改檔案**：[project_controller.py](file:///c:/Users/yenfu/OneDrive/JiuFangTKC/655.AI_agent/Jiufang_Novel_Editor/controllers/project_controller.py)

**修改內容 1**（L265-270，`_build_jne_project`）：
```diff
 for log in self.mc.writing_logs:
     project.writing_logs.append(WritingLogEntry(
         date=log.date,
         duration=log.duration,
-        word_count=log.word_count
+        word_count=log.word_count,
+        ai_continuation_count=getattr(log, "ai_continuation_count", 0),
+        ai_continuation_chars=getattr(log, "ai_continuation_chars", 0),
+        ai_chat_count=getattr(log, "ai_chat_count", 0)
     ))
```

**修改內容 2**（L370-373，`load_project_data`）：
```diff
 self.mc.writing_logs = [
-    WritingLogEntry(date=l.date, duration=l.duration, word_count=l.word_count)
+    WritingLogEntry(
+        date=l.date, duration=l.duration, word_count=l.word_count,
+        ai_continuation_count=getattr(l, "ai_continuation_count", 0),
+        ai_continuation_chars=getattr(l, "ai_continuation_chars", 0),
+        ai_chat_count=getattr(l, "ai_chat_count", 0)
+    )
     for l in project.writing_logs
 ]
```

---

#### 16.2 修復 B3：restore_cache 遺漏 scene 節點

**修改檔案**：[tree_controller.py](file:///c:/Users/yenfu/OneDrive/JiuFangTKC/655.AI_agent/Jiufang_Novel_Editor/controllers/tree_controller.py)

**修改內容**（L370）：
```diff
-            if data and data.get("type") == "file":
+            if data and data.get("type") in ("file", "scene"):
```

---

#### 16.3 修復 B4：update_icons 遺漏 scene 節點

**修改檔案**：[theme_controller.py](file:///c:/Users/yenfu/OneDrive/JiuFangTKC/655.AI_agent/Jiufang_Novel_Editor/controllers/theme_controller.py)

**修改內容**（L318 之後增加 scene 分支）：
```diff
                 elif t_type == "file":
                     if mark != "None" and mark:
                         # ... existing mark logic ...
                     else:
                         item.setIcon(0, create_custom_icon("file", self.view.file_icon_color, self.view.scale_factor))
+                elif t_type == "scene":
+                    if mark != "None" and mark:
+                        color_map = { ... }
+                        if mark in color_map:
+                            self.mc.tree.set_item_mark(item, color_map[mark], mark)
+                    else:
+                        item.setIcon(0, create_custom_icon("folder", "#7EB8F7", self.view.scale_factor))
```

---

#### 16.4 修復 B5：清理多餘 lambda 綁定

**修改檔案**：[card_controller.py](file:///c:/Users/yenfu/OneDrive/JiuFangTKC/655.AI_agent/Jiufang_Novel_Editor/controllers/card_controller.py)

**修改內容**（L316-318）：
```diff
-            act_expand = menu.addAction("▼ 全部展開")
-            act_expand.triggered.connect(item.setExpanded if True else None)
-            act_expand.triggered.connect(lambda: item.setExpanded(True))
+            act_expand = menu.addAction("▼ 全部展開")
+            act_expand.triggered.connect(lambda: item.setExpanded(True))
```

---

#### 16.5 修復 B6：初始化 current_project_path

**修改檔案**：[project_controller.py](file:///c:/Users/yenfu/OneDrive/JiuFangTKC/655.AI_agent/Jiufang_Novel_Editor/controllers/project_controller.py)

**修改內容**（`__init__` 方法中新增）：
```diff
 def __init__(self, main_controller):
     self.mc = main_controller
+    self.current_project_path: str = ""
```

---

#### 16.6 修復 D4：快照序列化遺漏 target_word_count

**修改檔案**：[database.py](file:///c:/Users/yenfu/OneDrive/JiuFangTKC/655.AI_agent/Jiufang_Novel_Editor/services/database.py)

**修改內容 1**（`_project_to_dict`，L538-545）：
```diff
         return {
             "project_info": {
                 "title": project.project_info.title,
                 "logline": project.project_info.logline,
                 "global_font_family": project.project_info.global_font_family,
                 "global_font_size": project.project_info.global_font_size,
                 "editor_font_family": project.project_info.editor_font_family,
-                "editor_font_size": project.project_info.editor_font_size
+                "editor_font_size": project.project_info.editor_font_size,
+                "target_word_count": getattr(project.project_info, "target_word_count", 100000)
             },
```

**修改內容 2**（`_dict_to_project`，L572-578）：
```diff
             project.project_info = ProjectInfo(
                 ...
                 editor_font_family=p_info_d.get("editor_font_family", "Iansui"),
-                editor_font_size=p_info_d.get("editor_font_size", 12)
+                editor_font_size=p_info_d.get("editor_font_size", 12),
+                target_word_count=p_info_d.get("target_word_count", 100000)
             ),
```

---

#### 16.7 更新全部 MD 文件

依照第一節的評估結果，同步更新以下文件的：
1. 最後更新日期
2. 測試數量（68 → 83）
3. 子控制器數量（9 → 11）
4. Phase 15 狀態標記
5. workspace_rules.md 的索引與已知 Bug 警示

---

## 四、驗證計畫

1. 修復 B1/B2 後，新增測試案例驗證 `_build_jne_project()` 與 `load_project_data()` 是否正確保留 AI 介入度欄位。
2. 修復 B3 後，驗證從垃圾桶還原 scene 節點時字數統計是否正確回填。
3. 全部修改完成後執行 `pytest tests/ -v`，確保 83 項（或更多）測試全數通過。

---

## Open Questions

> [!IMPORTANT]
> **D1（進度標記色碼重複定義）是否要在本次一併修復？**
> 抽取至 `models/models.py` 定義 `MARK_COLOR_MAP` 常量，然後在三處引用。改動範圍涉及 3 個檔案但變更極小，建議一併處理。

> [!IMPORTANT]
> **D3（database.py 810 行）是否要進行拆分？**
> 功能穩定且測試完備，建議暫緩，待下一個功能性 Phase 時再處理。
