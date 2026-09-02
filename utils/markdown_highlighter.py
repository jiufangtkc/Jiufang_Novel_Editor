import re
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PyQt6.QtCore import Qt


class MarkdownHighlighter(QSyntaxHighlighter):
    """
    即時 Markdown 語法高亮器。
    支援標題 (# ~ ######)、粗體 (**或__)、斜體 (*或_)、刪除線 (~~)、
    清單 (- 或 1.)、引言 (>)、行內代碼 (`)、代碼區塊、水平分隔線 (---)、
    以及小說常用標籤與角色欄位標記（例如 【外貌特徵】、#標籤）。
    """

    def __init__(self, parent=None, is_dark_theme=True):
        super().__init__(parent)
        self.is_dark_theme = is_dark_theme
        self.highlighting_rules = []
        self._init_formats()
        self._build_rules()

    def set_dark_theme(self, is_dark: bool):
        self.is_dark_theme = is_dark
        self._init_formats()
        self._build_rules()
        self.rehighlight()

    def _init_formats(self):
        if self.is_dark_theme:
            h1_color = QColor("#4fc1ff")
            h2_color = QColor("#61afef")
            h3_color = QColor("#98c379")
            h4_color = QColor("#e5c07b")
            bold_color = QColor("#e5c07b")
            italic_color = QColor("#d19a66")
            strike_color = QColor("#7f848e")
            list_color = QColor("#56b6c2")
            quote_color = QColor("#7f848e")
            code_color = QColor("#e06c75")
            code_bg = QColor("#282c34")
            tag_color = QColor("#c678dd")
            field_color = QColor("#56b6c2")
            hr_color = QColor("#5c6370")
            arrow_color = QColor("#61afef")
            muted_color = QColor("#4b5263")
        else:
            h1_color = QColor("#0066cc")
            h2_color = QColor("#007acc")
            h3_color = QColor("#22863a")
            h4_color = QColor("#b08800")
            bold_color = QColor("#b08800")
            italic_color = QColor("#d73a49")
            strike_color = QColor("#959da5")
            list_color = QColor("#005cc5")
            quote_color = QColor("#6a737d")
            code_color = QColor("#d73a49")
            code_bg = QColor("#f6f8fa")
            tag_color = QColor("#6f42c1")
            field_color = QColor("#005cc5")
            hr_color = QColor("#d1d5da")
            arrow_color = QColor("#007acc")
            muted_color = QColor("#c0c6d0")

        # 語法標記淡化格式 (用於 **、*、~~ 等符號，達成視覺減噪)
        self.fmt_muted = QTextCharFormat()
        self.fmt_muted.setForeground(muted_color)
        self.fmt_muted.setFontWeight(QFont.Weight.Normal)

        # 關係箭頭格式 (⟷, ➔, ↔ 等)
        self.fmt_arrow = QTextCharFormat()
        self.fmt_arrow.setForeground(arrow_color)
        self.fmt_arrow.setFontWeight(QFont.Weight.Bold)

        # 標題格式 (H1 ~ H4)
        self.fmt_h1 = QTextCharFormat()
        self.fmt_h1.setForeground(h1_color)
        self.fmt_h1.setFontWeight(QFont.Weight.Bold)

        self.fmt_h2 = QTextCharFormat()
        self.fmt_h2.setForeground(h2_color)
        self.fmt_h2.setFontWeight(QFont.Weight.Bold)

        self.fmt_h3 = QTextCharFormat()
        self.fmt_h3.setForeground(h3_color)
        self.fmt_h3.setFontWeight(QFont.Weight.Bold)

        self.fmt_h4 = QTextCharFormat()
        self.fmt_h4.setForeground(h4_color)
        self.fmt_h4.setFontWeight(QFont.Weight.Bold)

        # 粗體格式
        self.fmt_bold = QTextCharFormat()
        self.fmt_bold.setForeground(bold_color)
        self.fmt_bold.setFontWeight(QFont.Weight.Bold)

        # 斜體格式
        self.fmt_italic = QTextCharFormat()
        self.fmt_italic.setForeground(italic_color)
        self.fmt_italic.setFontItalic(True)

        # 刪除線
        self.fmt_strike = QTextCharFormat()
        self.fmt_strike.setForeground(strike_color)
        self.fmt_strike.setFontStrikeOut(True)

        # 清單項目格式
        self.fmt_list = QTextCharFormat()
        self.fmt_list.setForeground(list_color)
        self.fmt_list.setFontWeight(QFont.Weight.Bold)

        # 引言格式
        self.fmt_quote = QTextCharFormat()
        self.fmt_quote.setForeground(quote_color)
        self.fmt_quote.setFontItalic(True)

        # 行內代碼
        self.fmt_code = QTextCharFormat()
        self.fmt_code.setForeground(code_color)
        self.fmt_code.setBackground(code_bg)
        self.fmt_code.setFontFamilies(["Consolas", "Courier New", "monospace"])

        # 標籤 (#標籤)
        self.fmt_tag = QTextCharFormat()
        self.fmt_tag.setForeground(tag_color)
        self.fmt_tag.setFontWeight(QFont.Weight.Bold)

        # 方括號欄位標題 (【外貌特徵】、【人物側寫】等)
        self.fmt_field = QTextCharFormat()
        self.fmt_field.setForeground(field_color)
        self.fmt_field.setFontWeight(QFont.Weight.Bold)

        # 分隔線
        self.fmt_hr = QTextCharFormat()
        self.fmt_hr.setForeground(hr_color)

    def _build_rules(self):
        self.highlighting_rules = [
            # 1. 標題
            (re.compile(r"^#\s+[^\n]*"), self.fmt_h1),
            (re.compile(r"^##\s+[^\n]*"), self.fmt_h2),
            (re.compile(r"^###\s+[^\n]*"), self.fmt_h3),
            (re.compile(r"^####{1,3}\s+[^\n]*"), self.fmt_h4),

            # 2. 分隔線 (--- 或 ***)
            (re.compile(r"^\s*(?:---|\*\*\*|___)\s*$"), self.fmt_hr),

            # 3. 欄位標籤與特殊括號標籤 (如 【外貌特徵】、【標籤】)
            (re.compile(r"【[^】]+】"), self.fmt_field),

            # 4. Hash 標籤 (#AI角色, #設定)
            (re.compile(r"(?<!\w)#[^\s#]+"), self.fmt_tag),

            # 5. 引言 (> text)
            (re.compile(r"^\s*>[^\n]*"), self.fmt_quote),

            # 6. 清單開頭符號
            (re.compile(r"^\s*(?:[-*+]|\d+\.)\s"), self.fmt_list),

            # 7. 行內粗斜體 (***text***)
            (re.compile(r"\*\*\*[^*\n]+\*\*\*"), self.fmt_bold),

            # 8. 行內粗體 (**text** 或 __text__)
            (re.compile(r"\*\*[^*\n]+\*\*"), self.fmt_bold),
            (re.compile(r"__[^_\n]+__"), self.fmt_bold),

            # 9. 行內斜體 (*text* 或 _text_)
            (re.compile(r"(?<!\*)\*[^*\n]+\*(?!\*)"), self.fmt_italic),
            (re.compile(r"(?<!\w)_[^_\n]+_(?!\w)"), self.fmt_italic),

            # 10. 刪除線 (~~text~~)
            (re.compile(r"~~[^~\n]+~~"), self.fmt_strike),

            # 11. 行內代碼 (`code`)
            (re.compile(r"`[^`\n]+`"), self.fmt_code),

            # 12. 關係箭頭與 LaTeX 指令 (⟷, ➔, $\leftrightarrow$, \leftrightarrow 等)
            (re.compile(r"[⟷⟺➔←⇒⇐↔⇄]|(?:\$\\?[a-zA-Z]+\$)|(?:\\[a-zA-Z]+)"), self.fmt_arrow),
        ]

    def highlightBlock(self, text: str):
        # 先套用基礎格式
        for pattern, fmt in self.highlighting_rules:
            for match in pattern.finditer(text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, fmt)

        # 視覺減噪處理：淡化語法符號 (**、*、~~、`、#、$)
        symbol_patterns = [
            re.compile(r"\*\*|__"),      # 粗體符號
            re.compile(r"(?<!\*)\*(?!\*)|(?<!\w)_(?!\w)"),  # 斜體符號
            re.compile(r"~~"),            # 刪除線符號
            re.compile(r"`"),             # 代碼符號
            re.compile(r"^#{1,6}\s"),     # 標題前綴
            re.compile(r"^>\s*"),         # 引言前綴
            re.compile(r"\$"),            # 數學符號標記
        ]
        for pat in symbol_patterns:
            for match in pat.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), self.fmt_muted)

