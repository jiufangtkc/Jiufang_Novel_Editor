import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.models import CompactState, ChunkAnalysisResult, LongTextAnalysisResult
from services.long_text_analyzer import LongTextAnalyzer


def test_split_into_chunks_short_text():
    analyzer = LongTextAnalyzer(chunk_size=1000, overlap=100)
    text = "這是一篇短篇故事，只有兩百字。" * 10
    chunks = analyzer.split_into_chunks(text)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_split_into_chunks_long_text_with_overlap():
    analyzer = LongTextAnalyzer(chunk_size=200, overlap=50)
    paragraph = "這是第一段落的內容，敘述主角進入森林深處發現古代遺跡。\n\n"
    paragraph2 = "這是第二段落的內容，主角在遺跡內部遇到了神秘守護者並爆發戰鬥。\n\n"
    paragraph3 = "這是第三段落的內容，守護者戰敗後揭示了封印千年的世界真相。\n\n"
    paragraph4 = "這是第四段落的內容，主角帶著真相回到王城，開始策劃未來的對策。\n\n"
    long_text = paragraph * 3 + paragraph2 * 3 + paragraph3 * 3 + paragraph4 * 3

    chunks = analyzer.split_into_chunks(long_text)
    assert len(chunks) > 1
    # 驗證後續區塊是否包含上文銜接提示或重疊
    for chunk in chunks[1:]:
        assert "【接續上文片段】" in chunk or len(chunk) > 0


def test_build_chunk_prompt():
    analyzer = LongTextAnalyzer()
    state = CompactState(
        characters={"林克": "勇者，持有退魔之劍"},
        world_elements={"海拉魯王國": "古老的王國"},
        timeline_events=["甦醒於復甦神廟"],
        unresolved_threads=["災厄加儂的封印正在減弱"]
    )
    chunk_text = "林克穿過平原，前往海拉魯城堡。"
    sys_p, user_p = analyzer.build_chunk_prompt(
        task_type="character",
        chunk_text=chunk_text,
        chunk_index=2,
        total_chunks=5,
        state=state
    )

    assert "第 2 / 5 段" in user_p
    assert "林克：勇者，持有退魔之劍" in user_p
    assert "海拉魯王國：古老的王國" in user_p
    assert "【本段分析結論】" in user_p
    assert "【更新後摘要索引】" in user_p


def test_parse_chunk_response_standard():
    analyzer = LongTextAnalyzer()
    initial_state = CompactState(characters={"主角": "探索中"})

    llm_output = """
### 【本段分析結論】
本段情節推進明快，主角與反派首次交鋒，展現了高超的戰鬥技巧與堅毅性格。

### 【更新後摘要索引】
- 人物狀態更新：[主角：擊退刺客，受輕傷]、[刺客首領：重傷逃逸]
- 世界觀設定增量：[暗影教團：潛伏於王城的神秘暗殺組織]
- 關鍵里程碑事件：王城東門爆發夜間刺殺事件
- 當前未解懸念：刺客背後的委託人身分不明
- 結尾場景與局勢：主角在東門衛所接受包紮，局勢緊張
"""

    analysis, updated_state = analyzer.parse_chunk_response(llm_output, initial_state)

    assert "主角與反派首次交鋒" in analysis
    assert "主角" in updated_state.characters
    assert "擊退刺客" in updated_state.characters["主角"]
    assert "刺客首領" in updated_state.characters
    assert "暗影教團" in updated_state.world_elements
    assert any("王城東門爆發" in evt for evt in updated_state.timeline_events)
    assert any("刺客背後" in th for th in updated_state.unresolved_threads)
    assert "東門衛所" in updated_state.current_scene_context


def test_parse_chunk_response_fallback():
    analyzer = LongTextAnalyzer()
    initial_state = CompactState()

    # 模擬 9B 小模型未按 Markdown 標題輸出的純文字
    llm_output = "這是一段沒有遵循標準格式的分析內容。主角在此段落中獲得了神器。"

    analysis, updated_state = analyzer.parse_chunk_response(llm_output, initial_state)
    assert "這是一段沒有遵循標準格式" in analysis


def test_full_pipeline_rolling_analysis():
    call_log = []

    def mock_ai_caller(sys_p: str, user_p: str) -> str:
        call_log.append((sys_p, user_p))
        if "長篇總結任務" in user_p or "總結報告" in sys_p:
            return "【全書最終總結報告】\n這是一部宏大的奇幻史詩，架構嚴密。"
        return (
            "### 【本段分析結論】\n本段分析完成。\n\n"
            "### 【更新後摘要索引】\n- 人物狀態更新：[角色A：狀態良好]\n- 關鍵里程碑事件：事件A發生\n"
        )

    analyzer = LongTextAnalyzer(ai_caller=mock_ai_caller, chunk_size=100, overlap=20)
    text = "段落一內容描述故事開端。\n\n" * 10 + "段落二內容描述衝突爆發。\n\n" * 10

    progress_records = []
    def on_progress(cur, tot, msg):
        progress_records.append((cur, tot, msg))

    result = analyzer.analyze_long_text(
        text=text,
        task_type="impression",
        progress_callback=on_progress
    )

    assert isinstance(result, LongTextAnalysisResult)
    assert result.total_chunks > 1
    assert "全書最終總結報告" in result.final_synthesis
    assert len(progress_records) > 0
    # 驗證總呼叫次數 = total_chunks + 1 (最終全域整合)
    assert len(call_log) == result.total_chunks + 1


def test_cancellation():
    def mock_ai_caller(sys_p: str, user_p: str) -> str:
        return "### 【本段分析結論】\nOK"

    analyzer = LongTextAnalyzer(ai_caller=mock_ai_caller, chunk_size=50, overlap=10)
    text = "一段很長很長的測試文字。" * 20

    with pytest.raises(InterruptedError):
        analyzer.analyze_long_text(
            text=text,
            task_type="impression",
            is_cancelled_callback=lambda: True
        )
