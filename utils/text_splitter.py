import re
from typing import List

def chunk_text_with_overlap(text: str, chunk_size: int = 1500, overlap_size: int = 200) -> List[str]:
    """
    將長文本切分為多個段落 (chunks)，並保留部分重疊 (overlap)，
    優先依據章節標題或明顯的場景分隔符切分。
    
    :param text: 原始文本
    :param chunk_size: 每個 chunk 的期望最大字數
    :param overlap_size: 相鄰 chunk 的重疊字數
    :return: chunk 字串列表
    """
    if not text:
        return []
        
    if len(text) <= chunk_size:
        return [text]
        
    chunks = []
    
    # 嘗試以常見的章節或場景分隔符切分 (如：第x章、※※※、多重空行)
    # 這裡我們使用多重空行或 markdown 的分隔符作為優先切分點
    paragraphs = re.split(r'\n\s*\n+', text)
    
    current_chunk = ""
    
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
            
        # 若單一段落已經超過 chunk_size，退化為字元級別的切分
        if len(p) > chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
                
            # 字元級別切分
            idx = 0
            while idx < len(p):
                end_idx = min(idx + chunk_size, len(p))
                chunks.append(p[idx:end_idx].strip())
                if end_idx >= len(p):
                    break
                idx = end_idx - overlap_size
            continue
            
        if len(current_chunk) + len(p) + 2 <= chunk_size:
            current_chunk += ("\n\n" + p) if current_chunk else p
        else:
            chunks.append(current_chunk.strip())
            # 取上一個 chunk 的最後幾個字元作為 overlap
            overlap_text = current_chunk[-overlap_size:] if len(current_chunk) > overlap_size else current_chunk
            # 尋找 overlap_text 裡的第一個換行符號，避免從句子中間截斷
            newline_idx = overlap_text.find('\n')
            if newline_idx != -1 and newline_idx < len(overlap_text) - 1:
                overlap_text = overlap_text[newline_idx+1:]
                
            current_chunk = overlap_text.strip() + "\n\n" + p if overlap_text.strip() else p
            
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return chunks
