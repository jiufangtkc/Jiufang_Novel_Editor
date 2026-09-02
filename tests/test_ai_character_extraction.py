import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication, QTextEdit
from services.ai_service import AIService
from utils.markdown_highlighter import MarkdownHighlighter
from utils.markdown_utils import markdown_to_html
from views.dialogs.card_detail_dialog import CardDetailDialog


class TestAICharacterExtraction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_structured_character_parsing_5_elements(self):
        """測試結構化標籤格式解析，確認 5 大要素與獨立關係卡解析無誤。"""
        sample_output = """
===CHARACTER_START===
【角色姓名】莫庸
【外觀年齡】約 25 歲
【外觀特徵】半妖化體徵（已收斂），眼神沉靜孤高，手持泛著微光的道劍。
【人物側寫】深邃內省、專注致志，自仙轉魔後持續追尋道心真義，具極強同理心。
【已知行動】在碎星庭中漫步沉思，順著劍意指引跨越太印境登階。
【人事物關聯】與越無憂同行；與道劍心靈交感；探尋仙魔轉化之謎。
===CHARACTER_END===

===CHARACTER_START===
【角色姓名】越無憂
【外觀年齡】外表約 22 歲女子
【外觀特徵】褐膚麗人，氣質高貴堅定，手持道劍。
【人物側寫】神秘、果決、慈愛，目標導向且具備宏大人生地圖。
【已知行動】在木屋中留下不告而別的指引，以虛影形式伴隨莫庸登階。
【人事物關聯】引導莫庸；身負神秘重任。
===CHARACTER_END===

===RELATIONSHIP_START===
【卡片標題】全景角色關係網
【關係梳理】
- 莫庸與越無憂：互為精神指引與考驗者。
- 莫庸與道劍：性命交修。
===RELATIONSHIP_END===
"""
        parsed = AIService.parse_character_extraction_result(sample_output, scope_title="碎星庭篇")
        characters = parsed["characters"]
        rel_card = parsed["relationship_card"]

        self.assertEqual(len(characters), 2)
        c1 = characters[0]
        self.assertEqual(c1["name"], "莫庸")
        self.assertEqual(c1["title"], "【角色】莫庸")
        self.assertIn("約 25 歲", c1["age"])
        self.assertIn("半妖化體徵", c1["appearance"])
        self.assertIn("深邃內省", c1["profile"])
        self.assertIn("在碎星庭中漫步", c1["actions"])
        self.assertIn("越無憂", c1["relations"])
        self.assertIn("#AI角色 #人物設定 #莫庸", c1["content"])

        c2 = characters[1]
        self.assertEqual(c2["name"], "越無憂")
        self.assertEqual(c2["title"], "【角色】越無憂")
        self.assertIn("褐膚麗人", c2["appearance"])

        # 關係卡驗證
        self.assertIsNotNone(rel_card)
        self.assertIn("全景角色關係網", rel_card["title"])
        self.assertIn("#AI角色關係 #關係網", rel_card["content"])
        self.assertIn("莫庸與越無憂", rel_card["content"])

    def test_fallback_character_parsing(self):
        """測試模型未按標籤輸出（如使用 Markdown 標題）時的 Fallback 解析。"""
        sample_markdown = """
### 1. 劍星
* **外貌特徵：** 白衣仗劍，劍眉星目。
* **外觀年齡：** 青年劍客，約 20 歲。
* **性格特點：** 熱血正直，嫉惡如仇。
* **核心行為：** 斬妖除魔，守護宗門。
* **關係網：** 莫庸的同門師弟。

### 2. 黑袍長老
* **外貌特徵：** 面容枯槁，黑霧籠罩。
* **外觀年齡：** 六十歲老者。
* **性格特點：** 陰險狡詐，謀求長生。
* **核心行為：** 策劃血祭大陣。
* **關係網：** 宗門背叛者，敵對陣營。

### 角色關係總結
劍星與黑袍長老為死敵，誓要為同門報仇。
"""
        parsed = AIService.parse_character_extraction_result(sample_markdown, scope_title="青雲山篇")
        characters = parsed["characters"]
        rel_card = parsed["relationship_card"]

        self.assertGreaterEqual(len(characters), 2)
        names = [c["name"] for c in characters]
        self.assertIn("劍星", names)
        self.assertIn("黑袍長老", names)

        # 驗證欄位抽取
        jianxing = next(c for c in characters if c["name"] == "劍星")
        self.assertIn("白衣仗劍", jianxing["appearance"])
        self.assertIn("20 歲", jianxing["age"])
        self.assertIn("熱血正直", jianxing["profile"])

        self.assertIsNotNone(rel_card)
        self.assertIn("死敵", rel_card["content"])

    def test_markdown_highlighter_and_preview(self):
        """測試 MarkdownHighlighter 與 CardDetailDialog 預覽切換。"""
        editor = QTextEdit()
        highlighter = MarkdownHighlighter(editor.document())
        editor.setPlainText("## 標題測試\n**粗體文字**\n- 清單項目\n【外貌特徵】俊美非凡")

        self.assertTrue(len(highlighter.highlighting_rules) > 5)

        # 測試 CardDetailDialog 預覽模式切換
        dlg = CardDetailDialog(parent=None, title="角色卡", content="## 莫庸\n**年齡**：25")
        self.assertEqual(dlg.stack.currentIndex(), 0)  # 預設為編輯模式

        dlg.toggle_preview_mode()
        self.assertEqual(dlg.stack.currentIndex(), 1)  # 切換為預覽模式
        self.assertIn("莫庸", dlg.preview_browser.toPlainText())

        dlg.toggle_preview_mode()
        self.assertEqual(dlg.stack.currentIndex(), 0)  # 切換回編輯模式

    def test_ai_dialogs_scale_and_styles(self):
        """測試 AIScopeDialog 與 AICharacterReviewDialog 支援 scale_factor 與清晰外框。"""
        from views.dialogs.ai_scope_dialog import AIScopeDialog
        from views.dialogs.ai_character_review_dialog import AICharacterReviewDialog
        from views.main_window import MainWindow

        main_win = MainWindow()
        main_win.scale_factor = 1.5

        # 1. 測試 AIScopeDialog 縮放與樣式
        scope_dlg = AIScopeDialog(parent=main_win)
        self.assertEqual(scope_dlg.scale_factor, 1.5)
        self.assertEqual(scope_dlg.width(), int(540 * 1.5))
        self.assertEqual(scope_dlg.height(), int(640 * 1.5))
        # 驗證字型縮放
        self.assertEqual(scope_dlg.radio_all.font().pointSize(), int(9 * 1.5))
        self.assertEqual(scope_dlg.txt_title.font().pointSize(), int(9 * 1.5))
        self.assertEqual(scope_dlg.btn_start.font().pointSize(), int(9 * 1.5))
        scope_dlg.close()

        # 2. 測試 AICharacterReviewDialog 縮放與樣式
        sample_result = {
            "parsed_characters": [{"name": "莫庸", "title": "【角色】莫庸", "content": "測試內文"}],
            "parsed_relationship": {"title": "【關係網】", "content": "關係網內文"}
        }
        review_dlg = AICharacterReviewDialog(parent=main_win, result_data=sample_result)
        self.assertEqual(review_dlg.scale_factor, 1.5)
        self.assertEqual(review_dlg.width(), int(960 * 1.5))
        self.assertEqual(review_dlg.height(), int(700 * 1.5))
        # 驗證字型縮放
        self.assertEqual(review_dlg.card_list_widget.font().pointSize(), int(9 * 1.5))
        self.assertEqual(review_dlg.txt_title.font().pointSize(), int(10 * 1.5))
        self.assertEqual(review_dlg.editor.font().pointSize(), int(10 * 1.5))
        self.assertEqual(review_dlg.btn_import_all.font().pointSize(), int(9 * 1.5))
        review_dlg.close()
        main_win.close()

    def test_ai_scope_content_extraction_tree(self):
        """測試 AIScopeDialog 對於多層樹狀目錄（卷-章-幕）內文提取與字數統計之正確性。"""
        from views.dialogs.ai_scope_dialog import AIScopeDialog
        from views.main_window import MainWindow
        from controllers.main_controller import MainController
        from PyQt6.QtWidgets import QTreeWidgetItem
        from PyQt6.QtCore import Qt

        main_win = MainWindow()
        mc = MainController(main_win)
        main_win.tree_widget.clear()

        # 構建多層結構：第一卷 -> 序章 -> 幕1 / 幕2
        vol_item = mc.tree.create_item("第一卷", is_folder=True)
        main_win.tree_widget.addTopLevelItem(vol_item)

        ch1_item = mc.tree.create_item("序章-太形無形", is_folder=False, content="")
        vol_item.addChild(ch1_item)

        scene1 = mc.tree.create_item("第一幕-劍意破曉", is_scene=True, content="莫庸在碎星庭中握緊道劍，劍身流轉著青色微光。")
        scene2 = mc.tree.create_item("第二幕-仙魔交感", is_scene=True, content="越無憂的身影自虛空中浮現，眼神中滿是決絕。")
        ch1_item.addChild(scene1)
        ch1_item.addChild(scene2)

        # 1. 測試全書全文模式
        scope_dlg = AIScopeDialog(parent=main_win, current_item=scene1)
        scope_dlg.radio_all.setChecked(True)
        all_data = scope_dlg.get_scope_content()
        self.assertEqual(all_data["chapter_count"], 2)
        self.assertIn("莫庸在碎星庭中握緊道劍", all_data["text_content"])
        self.assertIn("越無憂的身影自虛空中浮現", all_data["text_content"])
        self.assertIn("2 個章節", scope_dlg.lbl_stats.text())

        # 2. 測試當前編輯章節模式（選取序章，應自動彙整其下 2 幕）
        scope_dlg.current_item = ch1_item
        scope_dlg.radio_current.setChecked(True)
        curr_data = scope_dlg.get_scope_content()
        self.assertEqual(curr_data["chapter_count"], 2)
        self.assertIn("第一幕-劍意破曉", curr_data["text_content"])
        self.assertIn("第二幕-仙魔交感", curr_data["text_content"])

        # 3. 測試自訂勾選模式（取消勾選第二幕）
        scope_dlg.radio_custom.setChecked(True)
        # 找到第二幕的 item 並取消勾選
        dest_scene2 = scope_dlg.item_map.get(mc.tree.get_item_id(scene2))
        self.assertIsNotNone(dest_scene2)
        dest_scene2.setCheckState(0, Qt.CheckState.Unchecked)
        scope_dlg.update_statistics()

        custom_data = scope_dlg.get_scope_content()
        self.assertEqual(custom_data["chapter_count"], 1)
        self.assertIn("莫庸在碎星庭中握緊道劍", custom_data["text_content"])
        self.assertNotIn("越無憂的身影自虛空中浮現", custom_data["text_content"])
        self.assertIn("1 個章節", scope_dlg.lbl_stats.text())

        scope_dlg.close()
        main_win.close()

    def test_latex_and_tag_cleaning(self):
        """測試 LaTeX 關係指令與重複標籤的清理與富文本渲染。"""
        sample_with_latex = """
===CHARACTER_START===
【角色姓名】解璃 (Jie Li)
【標籤】#AI角色 #人物設定 #解璃 (Jie Li)
【外觀年齡】二十出頭
【外觀特徵】清冷、溫和、剛健的劍修之姿。
【人物側寫】**（核心：包容下的堅韌）** 他是太形劍宗的頂點代表。
【已知行動】面對毒襲時祭出最強絕技。
【人事物關聯】**太形劍宗（領袖）** $\\leftrightarrow$ **紋面男子（哲學挑戰者）** $\\rightarrow$ **越無憂（救贖/錨點）**
===CHARACTER_END===
"""
        parsed = AIService.parse_character_extraction_result(sample_with_latex)
        self.assertEqual(len(parsed["characters"]), 1)
        c = parsed["characters"][0]
        
        # 1. 驗證 LaTeX 箭頭已轉為 Unicode
        self.assertNotIn("$\\leftrightarrow$", c["relations"])
        self.assertNotIn("$\\rightarrow$", c["relations"])
        self.assertIn("⟷", c["relations"])
        self.assertIn("➔", c["relations"])
        
        # 2. 驗證富文本 Markdown 轉 HTML 時無殘留指令
        html = markdown_to_html(c["content"])
        self.assertNotIn("$\\leftrightarrow$", html)
        self.assertNotIn("###", html)
        self.assertIn("⟷", html)
        self.assertIn("<strong>", html)
        # 確保【標籤】未重複出現兩次
        self.assertEqual(html.count("【標籤】"), 1)


if __name__ == "__main__":
    unittest.main()
