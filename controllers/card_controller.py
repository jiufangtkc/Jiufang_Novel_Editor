import uuid
from typing import Optional, List
from PyQt6.QtWidgets import QTreeWidgetItem, QMenu, QMessageBox, QInputDialog, QApplication
from PyQt6.QtCore import Qt
from views.components.right_panel_view import ROLE_CARD_ID, ROLE_CATEGORY, ROLE_NODE_TYPE
from views.dialogs.card_detail_dialog import CardDetailDialog
from models.models import CardNode, BUILTIN_CATEGORIES, CATEGORY_DISPLAY_NAMES, CATEGORY_ICONS


class CardController:
    """負責資料集卡片的樹狀導航 UI、資料增刪改與序列化。
    
    架構說明（Data-driven）：
      - 卡片資料統一存放在 mc.project_cards（CardNode dataclass）。
      - UI 的樹狀導航（QTreeWidget）是 mc.project_cards 的純渲染結果。
      - 任何卡片操作（新增/刪除/改名）都先修改 mc.project_cards，再呼叫
        rebuild_card_tree() 重新渲染。
      - 序列化時直接從 mc.project_cards 讀取，不再遍歷 UI Widget。
    """

    def __init__(self, main_controller):
        self.mc = main_controller

    @property
    def view(self):
        return self.mc.view

    @property
    def card_tree(self):
        return self.view.card_tree

    # =========================================================================
    # 初始化與信號連接
    # =========================================================================

    def connect_signals(self):
        """連接右側面板的 Signal（在 MainController.connect_signals 中呼叫）。"""
        rp = self.view.right_panel
        rp.signal_card_selected.connect(self.on_card_item_clicked)
        rp.signal_context_menu_requested.connect(self.on_context_menu)
        rp.signal_add_card_requested.connect(self.add_core_card)
        rp.signal_add_category_requested.connect(self.add_custom_category)
        rp.signal_card_dropped.connect(self.on_card_dropped)

    # =========================================================================
    # 樹狀導航 — 建立 / 重建與狀態同步
    # =========================================================================

    def sync_expansion_states_from_tree(self):
        """將 UI 上的分類展開狀態與各卡片節點的 is_collapsed 狀態同步至資料模型。"""
        tree = self.card_tree
        root = tree.invisibleRootItem()

        # 1. 收集頂層分類展開狀態
        expanded_cats = []
        for i in range(root.childCount()):
            cat_item = root.child(i)
            cat_key = cat_item.data(0, ROLE_CATEGORY)
            if cat_key and cat_item.isExpanded():
                expanded_cats.append(cat_key)

        if hasattr(self.mc, 'project_info') and self.mc.project_info:
            self.mc.project_info.expanded_categories = expanded_cats

        # 2. 遞迴同步各卡片節點的 is_collapsed
        all_nodes = {}
        for cards in self.mc.project_cards.values():
            self._collect_all_nodes(cards, all_nodes)

        def sync_item_collapse(item: QTreeWidgetItem):
            card_id = item.data(0, ROLE_CARD_ID)
            if card_id and card_id in all_nodes:
                all_nodes[card_id].is_collapsed = not item.isExpanded()
            for j in range(item.childCount()):
                sync_item_collapse(item.child(j))

        for i in range(root.childCount()):
            cat_item = root.child(i)
            for j in range(cat_item.childCount()):
                sync_item_collapse(cat_item.child(j))

    def rebuild_card_tree(self, expanded_categories=None):
        """根據 mc.project_cards 重新建立整個樹狀導航。"""
        tree = self.card_tree
        tree.blockSignals(True)

        # 決定分類展開狀態
        target_expanded = None
        if expanded_categories is not None:
            target_expanded = set(expanded_categories)
        elif getattr(getattr(self.mc, 'project_info', None), 'expanded_categories', None) is not None:
            target_expanded = set(self.mc.project_info.expanded_categories)
        else:
            # 從現有 UI 讀取（若有），否則預設全展開
            root = tree.invisibleRootItem()
            if root.childCount() > 0:
                target_expanded = set()
                for i in range(root.childCount()):
                    cat_item = root.child(i)
                    if cat_item.isExpanded():
                        cat = cat_item.data(0, ROLE_CATEGORY)
                        if cat:
                            target_expanded.add(cat)

        tree.clear()

        category_order = getattr(self.mc, '_project_category_order', None)
        if not category_order:
            # 從 project_cards 的 key 順序重建（相容舊版）
            category_order = list(self.mc.project_cards.keys())
            for builtin in BUILTIN_CATEGORIES:
                if builtin not in category_order:
                    category_order.append(builtin)

        rp = self.view.right_panel

        for category_key in category_order:
            if category_key not in self.mc.project_cards:
                continue

            display_name = CATEGORY_DISPLAY_NAMES.get(category_key, category_key)
            cat_item = rp.make_category_item(category_key, display_name)

            cards = self.mc.project_cards.get(category_key, [])
            for card_node in cards:
                self._add_card_node_to_tree(card_node, cat_item, category_key)

            tree.addTopLevelItem(cat_item)

            # 恢復分類展開狀態（若 target_expanded 為 None 則預設展開）
            if target_expanded is None or category_key in target_expanded:
                cat_item.setExpanded(True)
            else:
                cat_item.setExpanded(False)

            # 確保在依附到樹之後，遞迴套用各卡片節點的展開/收合狀態
            for i, card_node in enumerate(cards):
                if i < cat_item.childCount():
                    self._apply_card_expansion(cat_item.child(i), card_node)

        # 更新下拉選單
        custom_cats = [k for k in category_order if k not in BUILTIN_CATEGORIES]
        rp.rebuild_category_combo(category_order, custom_cats)

        tree.blockSignals(False)

    def _apply_card_expansion(self, item: QTreeWidgetItem, card_node: CardNode):
        """遞迴套用卡片節點的展開/收折狀態。"""
        item.setExpanded(not card_node.is_collapsed)
        for i, child_node in enumerate(card_node.children):
            if i < item.childCount():
                self._apply_card_expansion(item.child(i), child_node)

    def _add_card_node_to_tree(self, card_node: CardNode, parent_item: QTreeWidgetItem,
                                category_key: str) -> QTreeWidgetItem:
        """遞迴地將 CardNode 加入樹狀導航。"""
        rp = self.view.right_panel
        item = rp.make_card_item(
            card_id=card_node.id,
            title=card_node.title,
            category_key=category_key,
            color_hex=card_node.color,
            is_child=(parent_item.data(0, ROLE_NODE_TYPE) == "card")
        )
        parent_item.addChild(item)

        for child_node in card_node.children:
            self._add_card_node_to_tree(child_node, item, category_key)

        return item

    # =========================================================================
    # 卡片操作 — 新增 / 刪除 / 子卡片
    # =========================================================================

    def add_core_card(self, category: str):
        """在指定分類下新增一張空白卡片，並立即開啟編輯對話框。"""
        if category not in self.mc.project_cards:
            self.mc.project_cards[category] = []

        new_card = CardNode(title="新卡片")
        self.mc.project_cards[category].append(new_card)
        self._sync_category_order()
        self.rebuild_card_tree()
        self.mc.project.save_temp_doc()

        # 找到新建的節點並打開編輯框（僅在視窗可見時才開啟，避免測試環境 hang）
        new_item = self._find_tree_item_by_id(new_card.id)
        if new_item:
            self.card_tree.setCurrentItem(new_item)
            if self.view.isVisible():
                self._open_card_detail(new_item)

    def add_child_card(self, parent_card_id: str, category: str):
        """在指定父卡片下新增子卡片。"""
        parent_node = self._find_card_node_by_id(parent_card_id, category)
        if not parent_node:
            return

        child = CardNode(title="新子卡片")
        parent_node.children.append(child)
        self.rebuild_card_tree()
        self.mc.project.save_temp_doc()

        new_item = self._find_tree_item_by_id(child.id)
        if new_item:
            self.card_tree.setCurrentItem(new_item)
            self._open_card_detail(new_item)

    def delete_card(self, card_id: str, category: str):
        """從資料中遞迴刪除指定卡片（含其所有子卡片）。"""
        cards = self.mc.project_cards.get(category, [])
        removed = self._remove_card_by_id(cards, card_id)
        if not removed:
            # 嘗試在其他分類中搜尋（防禦）
            for cat, cat_cards in self.mc.project_cards.items():
                if self._remove_card_by_id(cat_cards, card_id):
                    break
        self.rebuild_card_tree()
        self.mc.project.save_temp_doc()

    def _remove_card_by_id(self, cards: List[CardNode], target_id: str) -> bool:
        """從列表中遞迴移除 id 符合的 CardNode，回傳是否成功。"""
        for i, card in enumerate(cards):
            if card.id == target_id:
                cards.pop(i)
                return True
            if self._remove_card_by_id(card.children, target_id):
                return True
        return False

    def add_custom_category(self):
        """新增使用者自訂大分類（無 AI 功能支援）。"""
        name, ok = QInputDialog.getText(
            self.view,
            "新增自訂分類",
            "請輸入新分類名稱（此分類不支援 AI 功能）："
        )
        if not ok or not name.strip():
            return

        display_name = name.strip()
        # 產生英文 key（用 uuid 的前8碼確保唯一性）
        cat_key = f"custom_{uuid.uuid4().hex[:8]}"

        self.mc.project_cards[cat_key] = []
        # 在 category_order 中加入
        if not hasattr(self.mc, '_project_category_order'):
            self.mc._project_category_order = list(self.mc.project_cards.keys())
        if cat_key not in self.mc._project_category_order:
            self.mc._project_category_order.append(cat_key)

        # 記錄顯示名稱（供 rebuild_card_tree 使用）
        CATEGORY_DISPLAY_NAMES[cat_key] = display_name

        self.rebuild_card_tree()
        self.mc.project.save_temp_doc()

    def rename_category(self, category_key: str, current_display_name: str):
        """重新命名自訂分類。"""
        if category_key in BUILTIN_CATEGORIES:
            QMessageBox.information(self.view, "提示", "內建分類名稱不允許修改。")
            return

        new_name, ok = QInputDialog.getText(
            self.view, "重新命名分類", "請輸入新的分類名稱：",
            text=current_display_name
        )
        if ok and new_name.strip():
            CATEGORY_DISPLAY_NAMES[category_key] = new_name.strip()
            self.rebuild_card_tree()
            self.mc.project.save_temp_doc()

    def delete_category(self, category_key: str):
        """刪除自訂分類（內建分類不可刪）。"""
        if category_key in BUILTIN_CATEGORIES:
            QMessageBox.information(self.view, "提示", "內建分類不可刪除。")
            return

        display_name = CATEGORY_DISPLAY_NAMES.get(category_key, category_key)
        cards_count = len(self.mc.project_cards.get(category_key, []))
        msg = f"確定要刪除分類「{display_name}」"
        if cards_count > 0:
            msg += f" 及其中的 {cards_count} 張卡片"
        msg += " 嗎？此操作無法復原。"

        reply = QMessageBox.question(
            self.view, "確認刪除分類", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.mc.project_cards.pop(category_key, None)
            if hasattr(self.mc, '_project_category_order'):
                try:
                    self.mc._project_category_order.remove(category_key)
                except ValueError:
                    pass
            CATEGORY_DISPLAY_NAMES.pop(category_key, None)
            self.rebuild_card_tree()
            self.mc.project.save_temp_doc()

    # =========================================================================
    # 事件處理
    # =========================================================================

    def on_card_item_clicked(self, item: QTreeWidgetItem):
        """點擊卡片節點時，打開 CardDetailDialog。"""
        self._open_card_detail(item)

    def _open_card_detail(self, item: QTreeWidgetItem):
        """根據 item 中的 card_id 找到 CardNode，打開詳細編輯對話框。"""
        card_id = item.data(0, ROLE_CARD_ID)
        category = item.data(0, ROLE_CATEGORY)
        if not card_id:
            return

        card_node = self._find_card_node_by_id(card_id, category)
        if not card_node:
            # 若在指定分類找不到，全域搜尋
            card_node, category = self._find_card_node_globally(card_id)
        if not card_node:
            return

        display_name = CATEGORY_DISPLAY_NAMES.get(category, "資料集卡片")
        dlg = CardDetailDialog(
            parent=self.view,
            title=card_node.title,
            content=card_node.content,
            color_hex=card_node.color,
            category_name=display_name
        )

        def on_detail_saved(new_title: str, new_content: str, new_color: str):
            card_node.title = new_title
            card_node.content = new_content
            card_node.color = new_color
            # 更新樹狀節點顯示名稱
            item.setText(0, f"  {new_title.strip() if new_title.strip() else '（未命名卡片）'}")
            self.mc.project.save_temp_doc()

        dlg.signal_saved.connect(on_detail_saved)
        dlg.exec()

    def on_context_menu(self, item, global_pos):
        """右鍵選單：卡片節點 / 分類節點 / 空白區域 各有不同選項。"""
        menu = QMenu(self.view)

        if item is None:
            # 空白區域點擊
            act_add = menu.addAction("＋ 新增卡片")
            act_add.triggered.connect(lambda: self.view.right_panel._on_add_card_clicked())
            act_add_cat = menu.addAction("⊕ 新增自訂分類")
            act_add_cat.triggered.connect(self.add_custom_category)

            menu.addSeparator()

            act_expand_all = menu.addAction("▼ 展開所有分類")
            act_expand_all.triggered.connect(lambda: self.set_all_categories_expanded(True))
            act_collapse_all = menu.addAction("▶ 收合所有分類")
            act_collapse_all.triggered.connect(lambda: self.set_all_categories_expanded(False))

        elif item.data(0, ROLE_NODE_TYPE) == "category":
            cat_key = item.data(0, ROLE_CATEGORY)
            display_name = CATEGORY_DISPLAY_NAMES.get(cat_key, cat_key)

            act_add = menu.addAction(f"＋ 在「{display_name}」中新增卡片")
            act_add.triggered.connect(lambda: self.add_core_card(cat_key))
            menu.addSeparator()

            if cat_key not in BUILTIN_CATEGORIES:
                act_rename = menu.addAction("✏️ 重新命名分類")
                act_rename.triggered.connect(lambda: self.rename_category(cat_key, display_name))
                act_del_cat = menu.addAction("🗑️ 刪除此分類")
                act_del_cat.triggered.connect(lambda: self.delete_category(cat_key))
                menu.addSeparator()

            act_expand = menu.addAction("▼ 全部展開")
            act_expand.triggered.connect(lambda: item.setExpanded(True))
            act_collapse = menu.addAction("▶ 全部收合")
            act_collapse.triggered.connect(lambda: item.setExpanded(False))

        elif item.data(0, ROLE_NODE_TYPE) == "card":
            card_id = item.data(0, ROLE_CARD_ID)
            category = item.data(0, ROLE_CATEGORY)

            # ── 1. 編輯與複製 ───────────────────────────
            act_open = menu.addAction("🔍 開啟詳細編輯")
            act_open.triggered.connect(lambda: self._open_card_detail(item))

            act_rename = menu.addAction("✏️ 重新命名")
            act_rename.triggered.connect(lambda: self.rename_card(card_id, category))

            act_dup = menu.addAction("📋 建立副本")
            act_dup.triggered.connect(lambda: self.duplicate_card(card_id, category))

            act_copy_txt = menu.addAction("📄 複製內文到剪貼簿")
            act_copy_txt.triggered.connect(lambda: self.copy_card_content(card_id, category))

            act_add_child = menu.addAction("＋ 新增子卡片")
            act_add_child.triggered.connect(lambda: self.add_child_card(card_id, category))

            menu.addSeparator()

            # ── 2. 移動到其他分類 ───────────────────────
            move_menu = menu.addMenu("→ 移動到...")
            for target_cat, target_display in CATEGORY_DISPLAY_NAMES.items():
                if target_cat != category and target_cat in self.mc.project_cards:
                    if target_cat == "ai_chat":
                        continue  # 不允許手動移入 AI 對話紀錄
                    act_move = move_menu.addAction(target_display)
                    act_move.triggered.connect(
                        lambda checked, tc=target_cat, cid=card_id, fc=category:
                        self.move_card(cid, fc, tc)
                    )

            # ── 3. 排序與展開 ───────────────────────────
            act_up = menu.addAction("⬆️ 上移")
            act_up.triggered.connect(lambda: self.move_card_up(card_id, category))

            act_down = menu.addAction("⬇️ 下移")
            act_down.triggered.connect(lambda: self.move_card_down(card_id, category))

            if item.childCount() > 0:
                act_expand_child = menu.addAction("▼ 展開子卡片")
                act_expand_child.triggered.connect(lambda: item.setExpanded(True))
                act_collapse_child = menu.addAction("▶ 收合子卡片")
                act_collapse_child.triggered.connect(lambda: item.setExpanded(False))

            menu.addSeparator()

            # ── 4. 刪除 ─────────────────────────────────
            act_del = menu.addAction("🗑️ 刪除此卡片")
            act_del.triggered.connect(lambda: self._confirm_delete_card(card_id, category))

        menu.exec(global_pos)

    def rename_card(self, card_id: str, category: str):
        """快速重新命名卡片標題。"""
        card_node = self._find_card_node_by_id(card_id, category)
        if not card_node:
            card_node, category = self._find_card_node_globally(card_id)
        if not card_node:
            return

        new_title, ok = QInputDialog.getText(
            self.view, "重新命名卡片", "請輸入卡片名稱：", text=card_node.title
        )
        if ok and new_title.strip():
            card_node.title = new_title.strip()
            self.rebuild_card_tree()
            self.mc.project.save_temp_doc()

    def duplicate_card(self, card_id: str, category: str):
        """建立指定卡片的副本（含所有子卡片），並插入在同層緊鄰位置。"""
        res = self._find_card_parent_and_index(card_id, category)
        if not res:
            return
        parent_list, idx, parent_node, card_node = res
        clone_node = self._clone_card_node_recursive(card_node, is_root=True)
        parent_list.insert(idx + 1, clone_node)
        self.rebuild_card_tree()
        self.mc.project.save_temp_doc()

    def _clone_card_node_recursive(self, src: CardNode, is_root: bool = True) -> CardNode:
        """遞迴複製 CardNode 及其子卡片，產生新 UUID。"""
        title = f"{src.title} (副本)" if is_root else src.title
        clone = CardNode(
            title=title,
            id=str(uuid.uuid4()),
            content=src.content,
            color=src.color,
            is_collapsed=src.is_collapsed,
            children=[self._clone_card_node_recursive(child, is_root=False) for child in src.children]
        )
        return clone

    def copy_card_content(self, card_id: str, category: str):
        """將卡片內文（或標題）複製到系統剪貼簿。"""
        card_node = self._find_card_node_by_id(card_id, category)
        if not card_node:
            card_node, category = self._find_card_node_globally(card_id)
        if not card_node:
            return

        text_to_copy = card_node.content if card_node.content.strip() else card_node.title
        QApplication.clipboard().setText(text_to_copy)
        self.mc.update_status_bar()

    def move_card_up(self, card_id: str, category: str):
        """將卡片在同層列表中向上移動一位。"""
        res = self._find_card_parent_and_index(card_id, category)
        if not res:
            return
        parent_list, idx, parent_node, card_node = res
        if idx > 0:
            parent_list[idx], parent_list[idx - 1] = parent_list[idx - 1], parent_list[idx]
            self.rebuild_card_tree()
            self.mc.project.save_temp_doc()

    def move_card_down(self, card_id: str, category: str):
        """將卡片在同層列表中向下移動一位。"""
        res = self._find_card_parent_and_index(card_id, category)
        if not res:
            return
        parent_list, idx, parent_node, card_node = res
        if idx < len(parent_list) - 1:
            parent_list[idx], parent_list[idx + 1] = parent_list[idx + 1], parent_list[idx]
            self.rebuild_card_tree()
            self.mc.project.save_temp_doc()

    def set_all_categories_expanded(self, expanded: bool):
        """展開或收合所有分類頂層項目。"""
        root = self.card_tree.invisibleRootItem()
        for i in range(root.childCount()):
            cat_item = root.child(i)
            cat_item.setExpanded(expanded)

    def _find_card_parent_and_index(self, card_id: str, category: str):
        """尋找卡片所在的清單、索引、父節點與卡片物件本身。
        回傳 (parent_list, index, parent_node, card_node) 或 None。
        """
        cards = self.mc.project_cards.get(category, [])
        def _search(node_list, parent=None):
            for idx, node in enumerate(node_list):
                if node.id == card_id:
                    return node_list, idx, parent, node
                res = _search(node.children, node)
                if res:
                    return res
            return None
        return _search(cards)

    def _confirm_delete_card(self, card_id: str, category: str):
        """詢問確認後刪除卡片。"""
        card_node = self._find_card_node_by_id(card_id, category)
        if not card_node:
            return
        has_children = bool(card_node.children)
        msg = f"確定要刪除卡片「{card_node.title}」"
        if has_children:
            msg += f" 及其 {len(card_node.children)} 個子卡片"
        msg += " 嗎？"

        reply = QMessageBox.question(
            self.view, "確認刪除",  msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.delete_card(card_id, category)

    def move_card(self, card_id: str, from_category: str, to_category: str):
        """將卡片從一個分類移動到另一個分類（只移動頂層卡片）。"""
        cards_from = self.mc.project_cards.get(from_category, [])
        # 找到並移除
        card_node = None
        for i, c in enumerate(cards_from):
            if c.id == card_id:
                card_node = cards_from.pop(i)
                break
        if not card_node:
            return

        if to_category not in self.mc.project_cards:
            self.mc.project_cards[to_category] = []
        self.mc.project_cards[to_category].append(card_node)
        self.rebuild_card_tree()
        self.mc.project.save_temp_doc()

    def on_card_dropped(self):
        """拖放完成後，同步樹狀 UI 的新順序到 mc.project_cards。"""
        self._sync_project_cards_from_tree()
        self.mc.project.save_temp_doc()

    def _sync_project_cards_from_tree(self):
        """從 QTreeWidget 的當前順序重建 mc.project_cards（拖放後使用）。"""
        tree = self.card_tree
        root = tree.invisibleRootItem()

        # 先清空所有分類的列表（只清空在樹中有對應節點的）
        seen_categories = set()
        for i in range(root.childCount()):
            cat_item = root.child(i)
            cat_key = cat_item.data(0, ROLE_CATEGORY)
            if cat_key:
                seen_categories.add(cat_key)

        # 建立 id → CardNode 映射（需要保留原始資料）
        all_nodes = {}
        for cat_cards in self.mc.project_cards.values():
            self._collect_all_nodes(cat_cards, all_nodes)

        # 依照樹的新順序重建
        for i in range(root.childCount()):
            cat_item = root.child(i)
            cat_key = cat_item.data(0, ROLE_CATEGORY)
            if not cat_key or cat_key not in self.mc.project_cards:
                continue
            new_list = []
            for j in range(cat_item.childCount()):
                card_item = cat_item.child(j)
                card_id = card_item.data(0, ROLE_CARD_ID)
                if card_id and card_id in all_nodes:
                    node = all_nodes[card_id]
                    node.children = self._rebuild_children_from_tree(card_item, all_nodes)
                    node.is_collapsed = not card_item.isExpanded()
                    new_list.append(node)
            self.mc.project_cards[cat_key] = new_list

    def _collect_all_nodes(self, cards: List[CardNode], result: dict):
        for card in cards:
            result[card.id] = card
            self._collect_all_nodes(card.children, result)

    def _rebuild_children_from_tree(self, item: QTreeWidgetItem, all_nodes: dict) -> List[CardNode]:
        children = []
        for i in range(item.childCount()):
            child_item = item.child(i)
            child_id = child_item.data(0, ROLE_CARD_ID)
            if child_id and child_id in all_nodes:
                node = all_nodes[child_id]
                node.children = self._rebuild_children_from_tree(child_item, all_nodes)
                node.is_collapsed = not child_item.isExpanded()
                children.append(node)
        return children

    def _sync_category_order(self):
        """確保 mc._project_category_order 與 mc.project_cards 的 key 同步。"""
        existing_order = getattr(self.mc, '_project_category_order', None)
        if not existing_order:
            self.mc._project_category_order = list(self.mc.project_cards.keys())
        else:
            for key in self.mc.project_cards:
                if key not in existing_order:
                    existing_order.append(key)

    # =========================================================================
    # 搜尋輔助
    # =========================================================================

    def _find_card_node_by_id(self, card_id: str, category: str) -> Optional[CardNode]:
        """在指定分類中遞迴搜尋 CardNode。"""
        cards = self.mc.project_cards.get(category, [])
        return self._search_in_list(cards, card_id)

    def _find_card_node_globally(self, card_id: str):
        """在所有分類中搜尋，回傳 (CardNode, category_key) 或 (None, None)。"""
        for cat, cards in self.mc.project_cards.items():
            node = self._search_in_list(cards, card_id)
            if node:
                return node, cat
        return None, None

    def _search_in_list(self, cards: List[CardNode], target_id: str) -> Optional[CardNode]:
        for card in cards:
            if card.id == target_id:
                return card
            found = self._search_in_list(card.children, target_id)
            if found:
                return found
        return None

    def _find_tree_item_by_id(self, card_id: str) -> Optional[QTreeWidgetItem]:
        """在 QTreeWidget 中遞迴搜尋節點。"""
        root = self.card_tree.invisibleRootItem()
        return self._search_tree_item(root, card_id)

    def _search_tree_item(self, parent: QTreeWidgetItem, card_id: str) -> Optional[QTreeWidgetItem]:
        for i in range(parent.childCount()):
            item = parent.child(i)
            if item.data(0, ROLE_CARD_ID) == card_id:
                return item
            found = self._search_tree_item(item, card_id)
            if found:
                return found
        return None

    # =========================================================================
    # 序列化 / 反序列化（Data-driven，不依賴 UI Widget）
    # =========================================================================

    def serialize_card(self, card_node: CardNode) -> dict:
        return {
            "title": card_node.title,
            "content": card_node.content,
            "color": card_node.color,
            "is_collapsed": card_node.is_collapsed,
            "id": card_node.id,
            "children": [self.serialize_card(c) for c in card_node.children]
        }

    def serialize_all_cards(self) -> dict:
        """從 mc.project_cards 直接序列化（不依賴 UI）。"""
        result = {}
        for mode, cards in self.mc.project_cards.items():
            result[mode] = [self.serialize_card(c) for c in cards]
        return result

    def deserialize_card(self, card_data: dict, parent_list: list, parent_card=None):
        """從 dict 建立 CardNode 並加入列表。"""
        card = CardNode(
            title=card_data.get("title", ""),
            id=card_data.get("id", str(__import__('uuid').uuid4())),
            content=card_data.get("content", ""),
            color=card_data.get("color", "#3C3F41"),
            is_collapsed=card_data.get("is_collapsed", False)
        )
        parent_list.append(card)
        for child_data in card_data.get("children", []):
            self.deserialize_card(child_data, card.children, card)

    def deserialize_all_cards(self, cards_data: dict):
        """從 dict 反序列化到 mc.project_cards，然後重建樹狀 UI。"""
        # 清空現有資料
        self.mc.project_cards = {}

        for mode, cards_list in cards_data.items():
            self.mc.project_cards[mode] = []
            for card_data in cards_list:
                self.deserialize_card(card_data, self.mc.project_cards[mode])

        # 確保內建分類存在
        for cat in BUILTIN_CATEGORIES:
            if cat not in self.mc.project_cards:
                self.mc.project_cards[cat] = []

        self._sync_category_order()
        self.rebuild_card_tree()

    def clear_cards_ui(self):
        """清空卡片資料並重建空樹狀導航。"""
        self.mc.project_cards = {cat: [] for cat in BUILTIN_CATEGORIES}
        self.mc._project_category_order = list(BUILTIN_CATEGORIES)
        self.rebuild_card_tree()

    def update_cards_buttons_state(self):
        """更新新增卡片按鈕狀態（此版本中固定啟用）。"""
        self.view.btn_add_card.setEnabled(True)

    # =========================================================================
    # AI 對話紀錄相關
    # =========================================================================

    def save_ai_chat_record(self, title: str, content: str):
        """將一次 AI 對話儲存為卡片，存入 ai_chat 分類。"""
        if "ai_chat" not in self.mc.project_cards:
            self.mc.project_cards["ai_chat"] = []

        record_card = CardNode(
            title=title,
            content=content,
            color="#1a2a3a"
        )
        # 最新的紀錄放最前面
        self.mc.project_cards["ai_chat"].insert(0, record_card)
        self.rebuild_card_tree()
        self.mc.project.save_temp_doc()
