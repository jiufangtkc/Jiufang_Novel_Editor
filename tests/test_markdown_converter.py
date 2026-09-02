import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from utils.markdown_converter import MarkdownConverter


def test_parse_inline_tokens_plain():
    tokens = MarkdownConverter.parse_inline_tokens("這是一段純文字。")
    assert len(tokens) == 1
    assert tokens[0]["text"] == "這是一段純文字。"
    assert not tokens[0]["bold"]
    assert not tokens[0]["italic"]


def test_parse_inline_tokens_mixed():
    text = "主角說道：**「別過來！」**他心中*暗自震驚*，甚至~~有些猶豫~~與`代碼`。"
    tokens = MarkdownConverter.parse_inline_tokens(text)
    
    # 驗證 tokens 解析
    bold_tokens = [t for t in tokens if t["bold"] and not t["italic"]]
    assert len(bold_tokens) == 1
    assert bold_tokens[0]["text"] == "「別過來！」"

    italic_tokens = [t for t in tokens if t["italic"] and not t["bold"]]
    assert len(italic_tokens) == 1
    assert italic_tokens[0]["text"] == "暗自震驚"

    strike_tokens = [t for t in tokens if t["strike"]]
    assert len(strike_tokens) == 1
    assert strike_tokens[0]["text"] == "有些猶豫"

    code_tokens = [t for t in tokens if t["code"]]
    assert len(code_tokens) == 1
    assert code_tokens[0]["text"] == "代碼"


def test_to_plain_text():
    md = "# 第一章 風起\n\n這是**重點**，他*輕聲說*。\n---\n> 這是一段信件。"
    plain = MarkdownConverter.to_plain_text(md, auto_indent=True)
    lines = plain.split('\n')
    
    assert lines[0] == "第一章 風起"
    assert lines[1] == ""
    assert "這是重點，他輕聲說。" in lines[2]
    assert lines[2].startswith("　　")
    assert lines[3] == "――――――――――――――――――――"
    assert "這是一段信件。" in lines[4]


def test_to_html_paragraphs():
    md = "# 標題\n**粗體**與*斜體*\n---\n> 引用內容"
    html_p = MarkdownConverter.to_html_paragraphs(md)
    
    assert html_p[0] == "<h1>標題</h1>"
    assert html_p[1] == "<p><strong>粗體</strong>與<em>斜體</em></p>"
    assert html_p[2] == "<hr/>"
    assert html_p[3] == "<blockquote><p>引用內容</p></blockquote>"


def test_render_to_docx():
    from docx import Document
    doc = Document()
    md = "# 第一章 試煉\n\n這是一個**關鍵線索**與*低語*。\n\n---\n> 來自遠方的信。"
    MarkdownConverter.render_to_docx(md, doc, "Iansui")
    
    # 檢查 paragraphs 數量
    assert len(doc.paragraphs) >= 4
    # 檢查第一段標題
    assert doc.paragraphs[0].text == "第一章 試煉"
    assert doc.paragraphs[0].runs[0].bold is True
    # 檢查第二段內文 runs
    p2 = doc.paragraphs[2]  # 空行在 idx 1
    bold_runs = [r for r in p2.runs if r.bold]
    assert len(bold_runs) == 1
    assert bold_runs[0].text == "關鍵線索"

