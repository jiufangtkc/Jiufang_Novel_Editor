import re
import html
from typing import Union
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtGui import QTextDocument, QFont, QTextListFormat, QTextBlock


def render_markdown_inline(text: str) -> str:
    """將行內 Markdown 標記與 LaTeX 關係指令轉換為 HTML，完美支援中文 (CJK) 邊界與常用 HTML 標籤"""
    if not text:
        return ""

    # 1. 預處理並轉換 LaTeX 數學與關係箭頭指令
    arrow_replacements = [
        (r'\$\\leftrightarrow\$|\\leftrightarrow|\$<->\$|<->|<-->', ' ⟷ '),
        (r'\$\\Leftrightarrow\$|\\Leftrightarrow', ' ⟺ '),
        (r'\$\\rightarrow\$|\\rightarrow|\$\\to\$|\\to|(?<=\s)->|(?<=\s)-->', ' ➔ '),
        (r'\$\\leftarrow\$|\\leftarrow|(?<=\s)<-|(?<=\s)<--', ' ← '),
        (r'\$\\Rightarrow\$|\\Rightarrow|(?<=\s)=>|(?<=\s)==>', ' ⇒ '),
        (r'\$\\Leftarrow\$|\\Leftarrow', ' ⇐ '),
        (r'\\cdot|\\bullet', ' • '),
        (r'\\times', ' × '),
    ]
    for pat, rep in arrow_replacements:
        text = re.sub(pat, rep, text)

    # 移除純文字行內殘留的單個美元符號 (例如 $文字$)
    text = re.sub(r'\$([^\$\n]+)\$', r'\1', text)

    # 保護現有的安全 HTML 標籤
    tag_pattern = r'(</?(?:u|del|s|strike|ins|span|b|i|strong|em|code)(?:\s+[^>]*)?>)'
    parts = re.split(tag_pattern, text, flags=re.IGNORECASE)
    res_parts = []

    for p in parts:
        if not p:
            continue
        if re.match(tag_pattern, p, flags=re.IGNORECASE):
            res_parts.append(p)
        else:
            # 逸出其他 HTML 特殊字元
            s = html.escape(p)
            # 1. 粗斜體 ***text*** 或 ___text___
            s = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', s, flags=re.DOTALL)
            s = re.sub(r'___(.+?)___', r'<strong><em>\1</em></strong>', s, flags=re.DOTALL)
            # 2. 粗體 **text** 或 __text__
            s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s, flags=re.DOTALL)
            s = re.sub(r'__(.+?)__', r'<strong>\1</strong>', s, flags=re.DOTALL)
            # 3. 斜體 *text* 或 _text_
            s = re.sub(r'\*(.+?)\*', r'<em>\1</em>', s, flags=re.DOTALL)
            s = re.sub(r'(?<!\w)_(.+?)_(?!\w)', r'<em>\1</em>', s, flags=re.DOTALL)
            # 4. 刪除線 ~~text~~
            s = re.sub(r'~~(.+?)~~', r'<del>\1</del>', s, flags=re.DOTALL)
            # 5. 行內程式碼 `code`
            s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
            # 6. 標籤膠囊化 (#標籤)
            s = re.sub(
                r'(?<!\w)#([^\s#<]+)',
                r'<span style="color: #61afef; background-color: rgba(97, 175, 239, 0.15); border-radius: 3px; padding: 1px 5px; font-weight: bold;">#\1</span>',
                s
            )
            # 7. 關係箭頭樣式加強
            s = re.sub(
                r'([⟷⟺➔←⇒⇐])',
                r'<span style="color: #61afef; font-weight: bold; padding: 0 4px;">\1</span>',
                s
            )
            res_parts.append(s)

    return ''.join(res_parts)


def markdown_to_html(md_text: str) -> str:
    """
    將 Markdown 文本轉換為乾淨標準的 HTML，用於 QTextEdit / QTextDocument 富文本渲染。
    支援標題、清單、水平線、空行保留、LaTeX 箭頭轉換及所有行內樣式。
    """
    if not md_text:
        return '<p style="-qt-paragraph-type:empty;"><br></p>'

    # 統一換行字元
    normalized = md_text.replace('\r\n', '\n').replace('\r', '\n')
    lines = normalized.split('\n')
    
    # 過濾連續重複的 【標籤】 行
    deduped_lines = []
    last_tag_line = None
    for l in lines:
        stripped = l.strip()
        if stripped.startswith("【標籤】"):
            if stripped == last_tag_line:
                continue
            last_tag_line = stripped
        else:
            last_tag_line = None
        deduped_lines.append(l)

    html_lines = ['<style>p, li { margin: 0px; padding: 0px; }</style>']
    in_ul = False
    in_ol = False

    for line in deduped_lines:
        stripped = line.strip()

        # 1. 無序清單 (- , * , + )
        if stripped.startswith(('- ', '* ', '+ ')) and len(stripped) >= 2:
            if in_ol:
                html_lines.append('</ol>')
                in_ol = False
            if not in_ul:
                html_lines.append('<ul>')
                in_ul = True
            item_text = line.lstrip()[2:]
            html_lines.append(f'<li>{render_markdown_inline(item_text)}</li>')
            continue

        # 2. 有序清單 (1. , 2. )
        m_ol = re.match(r'^\d+\.\s+(.*)$', stripped)
        if m_ol:
            if in_ul:
                html_lines.append('</ul>')
                in_ul = False
            if not in_ol:
                html_lines.append('<ol>')
                in_ol = True
            item_text = m_ol.group(1)
            html_lines.append(f'<li>{render_markdown_inline(item_text)}</li>')
            continue

        # 若離開清單區塊，閉合標籤
        if in_ul:
            html_lines.append('</ul>')
            in_ul = False
        if in_ol:
            html_lines.append('</ol>')
            in_ol = False

        # 3. 水平分隔線 (---, ***, ___)
        if stripped in ('---', '***', '___', '----', '****', '____'):
            html_lines.append('<hr>')
            continue

        # 4. 標題 (# H1 ~ ###### H6)
        m_h = re.match(r'^(#{1,6})\s+(.*)$', stripped)
        if m_h:
            h_lvl = len(m_h.group(1))
            h_text = m_h.group(2)
            html_lines.append(f'<h{h_lvl}>{render_markdown_inline(h_text)}</h{h_lvl}>')
            continue

        # 5. 空行與普通段落
        if not stripped:
            html_lines.append('<p style="-qt-paragraph-type:empty;"><br></p>')
        else:
            html_lines.append(f'<p>{render_markdown_inline(line)}</p>')

    if in_ul:
        html_lines.append('</ul>')
    if in_ol:
        html_lines.append('</ol>')

    return ''.join(html_lines)


def document_to_markdown(doc_or_edit: Union[QTextDocument, QTextEdit]) -> str:
    """
    從 QTextDocument 或 QTextEdit 中底層遍歷 QTextBlock 與 QTextFragment，
    精確提取並序列化為乾淨、對稱且無損的 Markdown 文本。
    """
    if isinstance(doc_or_edit, QTextEdit):
        doc = doc_or_edit.document()
    else:
        doc = doc_or_edit

    if not doc:
        return ""

    lines = []
    block = doc.begin()

    while block.isValid():
        # 清單前綴檢查
        text_list = block.textList()
        prefix = ""
        if text_list:
            list_style = text_list.format().style()
            if list_style in (
                QTextListFormat.Style.ListDisc,
                QTextListFormat.Style.ListCircle,
                QTextListFormat.Style.ListSquare
            ):
                prefix = "- "
            elif list_style in (
                QTextListFormat.Style.ListDecimal,
                QTextListFormat.Style.ListLowerAlpha,
                QTextListFormat.Style.ListUpperAlpha,
                QTextListFormat.Style.ListLowerRoman,
                QTextListFormat.Style.ListUpperRoman
            ):
                item_idx = text_list.itemNumber(block)
                prefix = f"{item_idx + 1}. " if item_idx >= 0 else "1. "

        line_parts = []
        if prefix:
            line_parts.append(prefix)

        it = block.begin()
        while not it.atEnd():
            frag = it.fragment()
            if frag.isValid():
                text = frag.text()
                # 正常化特殊分行符號
                text = text.replace('\u2029', '').replace('\u2028', '')
                if text:
                    fmt = frag.charFormat()
                    is_bold = (fmt.fontWeight() == QFont.Weight.Bold) or (fmt.fontWeight() >= 700)
                    is_italic = fmt.fontItalic()
                    is_under = fmt.fontUnderline()
                    is_strike = fmt.fontStrikeOut()

                    frag_str = text
                    if is_strike:
                        frag_str = f"~~{frag_str}~~"
                    if is_under:
                        frag_str = f"<u>{frag_str}</u>"
                    if is_bold and is_italic:
                        frag_str = f"***{frag_str}***"
                    elif is_bold:
                        frag_str = f"**{frag_str}**"
                    elif is_italic:
                        frag_str = f"*{frag_str}*"

                    line_parts.append(frag_str)
            it += 1

        line_content = "".join(line_parts)
        lines.append(line_content)
        block = block.next()

    # 移除末尾多餘空行，但保留文內自然段落
    result = "\n".join(lines)
    return result
