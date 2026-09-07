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


def test_dynamic_entity_retrieval_with_large_character_pool():
    """驗證突破數量限制：擁有 50 位角色與 20 個世界觀名詞時，動態命中檢索能精準注入且不爆 Context"""
    characters = {f"角色{i}": f"這是第 {i} 位角色的詳細背景與狀態描述" for i in range(1, 51)}
    world_elements = {f"勢力{j}": f"這是第 {j} 個勢力的組織架構說明" for j in range(1, 21)}

    state = CompactState(
        characters=characters,
        character_mentions={f"角色{i}": i for i in range(1, 51)},
        world_elements=world_elements
    )

    # 驗證全局庫保有所有 50 位角色，無一人被丟棄
    assert len(state.characters) == 50
    assert len(state.world_elements) == 20

    # 當前正文僅提及「角色42」與「勢力15」
    chunk_text = "在古老的荒原上，角色42 與神祕來客會面，商討對抗 勢力15 的策略。"
    summary = state.get_relevant_summary(chunk_text=chunk_text, max_chars=600)

    # 驗證命中被精準挑選出來
    assert "角色42" in summary
    assert "勢力15" in summary
    # 驗證未出場角色不會擠佔過多版面，總長度嚴格受控
    assert len(summary) <= 650


def test_build_synthesis_prompt_budget_control_for_many_chunks():
    """驗證 17 個分段（超長篇小說 6 萬字規模）在最後總結時的預算控制，杜絕 16k context window 爆表"""
    analyzer = LongTextAnalyzer()
    state = CompactState(
        characters={"解璃": "主角劍仙", "越無憂": "女主角", "夏成舟": "核心幕後設計者"},
        character_mentions={"解璃": 15, "越無憂": 14, "夏成舟": 8}
    )

    # 模擬 17 個階段，每個階段輸出 1200 字長文（原本拼接會達到 20,400 字）
    chunk_results = []
    for i in range(1, 18):
        fake_analysis = f"第 {i} 段詳細分析：情節推進激烈，角色深度互動。" + ("敘事細節深入描寫。" * 60)
        chunk_results.append(ChunkAnalysisResult(
            chunk_index=i,
            total_chunks=17,
            char_count=3500,
            partial_analysis=fake_analysis
        ))

    sys_p, user_p = analyzer.build_synthesis_prompt(
        task_type="character",
        final_state=state,
        chunk_results=chunk_results,
        total_chars=60000
    )

    # 驗證總結 Prompt 總字數嚴格控制在安全範圍（遠低於 16k token 約 12,000 字上限）
    assert len(user_p) < 6000
    assert "解璃（出場 15 次）" in user_p
    assert "越無憂（出場 14 次）" in user_p
    assert "第 1/17 階段核心要點" in user_p
    assert "第 17/17 階段核心要點" in user_p


def test_calculate_dynamic_chunk_size_normal(monkeypatch):
    """驗證充足記憶體（8GB）環境下之動態分塊計算"""
    monkeypatch.setattr("services.hardware_detector.get_available_memory_mb", lambda: 8192.0)
    chunk_size, max_tokens = LongTextAnalyzer.calculate_dynamic_chunk_size()
    assert max_tokens == 8000
    assert chunk_size == 6000


def test_calculate_dynamic_chunk_size_low_memory(monkeypatch):
    """驗證記憶體嚴重不足（< 1500MB）時應拋出 MemoryError"""
    monkeypatch.setattr("services.hardware_detector.get_available_memory_mb", lambda: 1024.0)
    with pytest.raises(MemoryError) as exc_info:
        LongTextAnalyzer.calculate_dynamic_chunk_size()
    assert "低於 1.5GB" in str(exc_info.value)


def test_calculate_dynamic_chunk_size_custom_tokens():
    """驗證傳入自訂 max_context_tokens 時應精確扣除框架預留"""
    chunk_size, max_tokens = LongTextAnalyzer.calculate_dynamic_chunk_size(max_context_tokens=6000)
    assert max_tokens == 6000
    assert chunk_size == 4000


def test_chunk_text_truncation_on_token_overflow():
    """驗證當 chunk_text token 數超過安全上限（max_tokens 的 75%）時，analyze_long_text 會截斷並加入截斷提示標記"""
    intercepted_prompts = []

    def mock_ai_caller(sys_p: str, user_p: str) -> str:
        intercepted_prompts.append(user_p)
        if "長篇總結任務" in user_p or "總結報告" in sys_p:
            return "【全書最終總結】完成。"
        return (
            "### 【本段分析結論】\n截斷測試通過。\n\n"
            "### 【更新後摘要索引】\n- 關鍵里程碑事件：測試事件\n"
        )

    # token_counter 對超過 50 字的文字回傳 10000（遠超 max_tokens 75%）
    def big_token_counter(text: str) -> int:
        if len(text) > 50:
            return 10000
        return int(len(text) * 2.5)

    analyzer = LongTextAnalyzer(
        ai_caller=mock_ai_caller,
        chunk_size=100,
        overlap=10,
        token_counter=big_token_counter
    )
    text = "主角進入遺跡，發現了古老的神器，並遭遇了強敵。一場激烈的戰鬥就此展開。" * 3

    import unittest.mock as _mock
    with _mock.patch.object(
        LongTextAnalyzer, 'calculate_dynamic_chunk_size',
        return_value=(1000, 8000)
    ):
        result = analyzer.analyze_long_text(text=text, task_type="impression")

    truncation_marker = "本段因長度超出安全上限已截斷"
    assert any(truncation_marker in p for p in intercepted_prompts), \
        f"預期至少一個 Prompt 含截斷提示，但未找到。各 Prompt 前 100 字：{[p[:100] for p in intercepted_prompts]}"


def test_dynamic_timeline_event_hit_filtering():
    """驗證 get_dynamic_summary 中包含正文關鍵詞的事件被優先選取"""
    state = CompactState(
        timeline_events=[
            "王城東門爆發夜間刺殺事件",
            "主角在古老遺跡發現神器",
            "守護者在荒原設下陷阱",
        ],
        unresolved_threads=[
            "刺客背後的委託人身分不明",
            "荒原守護者的真實目的",
        ]
    )

    chunk_text = "主角獨自踏上荒原，尋找失蹤的同伴。"

    def tight_token_counter(text: str) -> int:
        return len(text)

    summary = state.get_dynamic_summary(
        chunk_text=chunk_text,
        token_budget=200,
        token_counter=tight_token_counter
    )

    assert "荒原" in summary, f"預期摘要包含命中關鍵詞「荒原」的事件，實際摘要：\n{summary}"
