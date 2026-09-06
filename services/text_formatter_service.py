import re
from typing import Dict, Any


class TextFormatterService:
    """提供小說文本排版處理服務，包含標點轉換、段首縮排處理與空行增刪。

    本服務為無狀態純函式集合，便於獨立測試與跨模組重複使用。
    """

    # 半形標點替換字典（基本標點）
    PUNCTUATION_MAP = {
        ',': '，',
        '?': '？',
        '!': '！',
        ':': '：',
        ';': '；',
        '(': '（',
        ')': '）',
        '~': '～',
    }

    @classmethod
    def convert_halfwidth_punctuation(cls, text: str) -> str:
        """將半形標點符號轉換為中文全形標點符號。

        智慧保護數字小數點（如 3.14），其餘半形句號轉為全形句號。
        """
        if not text:
            return ""

        # 1. 替換基本標點
        for half, full in cls.PUNCTUATION_MAP.items():
            text = text.replace(half, full)

        # 2. 智慧替換英文句號（排除小數點：前後為數字的情況）
        # 先將數字小數點保護為臨時標記
        placeholder = "__DECIMAL_POINT_PLACEHOLDER__"
        text = re.sub(r'(?<=\d)\.(?=\d)', placeholder, text)
        # 替換一般句號為全形句號
        text = text.replace('.', '。')
        # 還原小數點
        text = text.replace(placeholder, '.')

        return text

    @classmethod
    def indent_paragraphs(cls, text: str, spaces: int = 2) -> str:
        """段首自動增加全形空格縮排。

        清除行首原本混雜的半形或全形空白後，統一在非空行首補上指定數量的全形空格。
        空行則完全清空空白。
        """
        if not text:
            return ""

        indent_str = "\u3000" * spaces
        lines = text.splitlines()
        result_lines = []

        for line in lines:
            stripped = line.strip(" \t\u3000")
            if stripped:
                result_lines.append(f"{indent_str}{stripped}")
            else:
                result_lines.append("")

        # 保持原文字末尾是否換行
        trailing_newline = "\n" if text.endswith("\n") else ""
        return "\n".join(result_lines) + trailing_newline

    @classmethod
    def remove_indentation(cls, text: str) -> str:
        """清除所有段首空白（可逆操作），使所有段落齊頭靠左。"""
        if not text:
            return ""

        lines = text.splitlines()
        result_lines = []

        for line in lines:
            # 僅去除行首空白，保留行末及行內內容
            lstripped = line.lstrip(" \t\u3000")
            if lstripped:
                result_lines.append(lstripped)
            else:
                result_lines.append("")

        trailing_newline = "\n" if text.endswith("\n") else ""
        return "\n".join(result_lines) + trailing_newline

    @classmethod
    def compact_empty_lines(cls, text: str) -> str:
        """刪除多餘空行，將連續 2 行以上的空白行壓縮為僅保留 1 行空行。"""
        if not text:
            return ""

        # 先將每行僅有空白字符的行淨化為純空行
        lines = [line if line.strip(" \t\u3000") else "" for line in text.splitlines()]
        cleaned_text = "\n".join(lines)

        # 將 3 個以上連續換行壓縮為 2 個換行（即段落間最多 1 個空行）
        compacted = re.sub(r'\n{3,}', '\n\n', cleaned_text)
        if text.endswith("\n") and not compacted.endswith("\n"):
            compacted += "\n"
        return compacted

    @classmethod
    def remove_all_empty_lines(cls, text: str) -> str:
        """移除所有空行，段落之間無空行。"""
        if not text:
            return ""

        lines = text.splitlines()
        result_lines = [line for line in lines if line.strip(" \t\u3000")]
        trailing_newline = "\n" if text.endswith("\n") else ""
        return "\n".join(result_lines) + trailing_newline

    @classmethod
    def add_empty_lines(cls, text: str) -> str:
        """自動在每個段落之間增加一行空行（網路小說排版常用）。

        若原先已有空行則不重複增加，維持各段落間恰好有 1 行空行。
        """
        if not text:
            return ""

        lines = text.splitlines()
        non_empty_lines = [line for line in lines if line.strip(" \t\u3000")]
        trailing_newline = "\n" if text.endswith("\n") else ""
        return "\n\n".join(non_empty_lines) + trailing_newline

    @classmethod
    def format_text(cls, text: str, options: Dict[str, Any]) -> str:
        """根據傳入的設定選項，循序套用排版規則。

        options 範例：
        {
            'convert_punctuation': True,
            'indent_mode': 'indent' | 'remove' | 'none',
            'empty_line_mode': 'compact' | 'remove_all' | 'add' | 'none',
        }
        """
        if not text:
            return ""

        result = text

        # 1. 標點轉換
        if options.get('convert_punctuation', False):
            result = cls.convert_halfwidth_punctuation(result)

        # 2. 段首縮排處理
        indent_mode = options.get('indent_mode', 'none')
        if indent_mode == 'indent':
            result = cls.indent_paragraphs(result, spaces=2)
        elif indent_mode == 'remove':
            result = cls.remove_indentation(result)

        # 3. 空行增刪處理
        empty_line_mode = options.get('empty_line_mode', 'none')
        if empty_line_mode == 'compact':
            result = cls.compact_empty_lines(result)
        elif empty_line_mode == 'remove_all':
            result = cls.remove_all_empty_lines(result)
        elif empty_line_mode == 'add':
            result = cls.add_empty_lines(result)

        return result
