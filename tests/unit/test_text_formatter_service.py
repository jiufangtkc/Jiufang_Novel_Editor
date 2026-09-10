import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.text_formatter_service import TextFormatterService


class TestTextFormatterService:
    """文字排版服務之完整單元測試。"""

    def test_convert_halfwidth_punctuation(self):
        sample = "你好,這是一個測試.真的嗎?是的!價格:100;速度~快(包含備註)."
        expected = "你好，這是一個測試。真的嗎？是的！價格：100；速度～快（包含備註）。"
        converted = TextFormatterService.convert_halfwidth_punctuation(sample)
        assert converted == expected

    def test_convert_halfwidth_punctuation_preserve_decimal(self):
        sample = "圓周率是 3.14159, 版本號是 v1.2, 這是句尾."
        expected = "圓周率是 3.14159， 版本號是 v1.2， 這是句尾。"
        converted = TextFormatterService.convert_halfwidth_punctuation(sample)
        assert converted == expected

    def test_indent_paragraphs(self):
        sample = "第一段文字。\n第二段文字。\n\n第三段文字。"
        expected = "\u3000\u3000第一段文字。\n\u3000\u3000第二段文字。\n\n\u3000\u3000第三段文字。"
        indented = TextFormatterService.indent_paragraphs(sample, spaces=2)
        assert indented == expected

    def test_remove_indentation_is_reversible(self):
        original = "第一段文字。\n第二段文字。\n第三段文字。"
        indented = TextFormatterService.indent_paragraphs(original, spaces=2)
        restored = TextFormatterService.remove_indentation(indented)
        assert restored == original

    def test_compact_empty_lines(self):
        sample = "段落一\n\n\n\n段落二\n\n\n段落三"
        expected = "段落一\n\n段落二\n\n段落三"
        compacted = TextFormatterService.compact_empty_lines(sample)
        assert compacted == expected

    def test_remove_all_empty_lines(self):
        sample = "段落一\n\n段落二\n\n\n段落三"
        expected = "段落一\n段落二\n段落三"
        removed = TextFormatterService.remove_all_empty_lines(sample)
        assert removed == expected

    def test_add_empty_lines(self):
        sample = "段落一\n段落二\n段落三"
        expected = "段落一\n\n段落二\n\n段落三"
        added = TextFormatterService.add_empty_lines(sample)
        assert added == expected

    def test_format_text_combined(self):
        sample = "你好,世界.  \n\n\n下雨了!快跑.\n這是結尾~"
        options = {
            'convert_punctuation': True,
            'indent_mode': 'indent',
            'empty_line_mode': 'compact',
        }
        result = TextFormatterService.format_text(sample, options)
        expected = "\u3000\u3000你好，世界。\n\n\u3000\u3000下雨了！快跑。\n\u3000\u3000這是結尾～"
        assert result == expected
