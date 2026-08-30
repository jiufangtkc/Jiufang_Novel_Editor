import os
import json
import re
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional

@dataclass
class LintIssue:
    line_number: int           # 1-indexed 行號
    start_pos: int             # 全文字元起始索引
    end_pos: int               # 全文字元結束索引
    issue_type: str            # "redundant_phrase" | "high_density_particle" | "passive_voice" | "duplicate_words"
    issue_type_name: str       # 中文分類名稱
    target_text: str           # 觸發警告的文字或片語
    message: str               # 說明訊息
    suggestion: str            # 修改建議

class LintService:
    """繁體中文小說贅詞與文風檢查引擎服務。"""

    DEFAULT_SETTINGS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lint_settings.json")

    # 預設公文冗詞贅字片語庫
    DEFAULT_REDUNDANT_PHRASES = [
        "進行了一個", "進行了一次", "進行了一項", "進行了",
        "作了一個", "做了一個", "做出了", "做出一項",
        "基本上來說", "基本上", "從某種程度來說", "不可否認的是",
        "在某種意義上", "在...的情況下", "在...的基礎上",
        "顯而易見的是", "毫無疑問地", "總而言之", "換句話說",
        "在一定程度上", "有鑑於此", "毋庸置疑"
    ]

    # 常見被動語句標記詞
    DEFAULT_PASSIVE_WORDS = [
        "被", "受到", "遭到", "予以", "加以"
    ]

    # 高頻虛詞清單
    PARTICLES = ["了", "的", "是", "有", "就", "著", "得", "地"]

    # 重複詞排除白名單（常用代詞、常用成語或副詞）
    DUPLICATE_IGNORE_SET = {
        "我們", "你們", "他們", "她們", "它們", "大家", "自己", "什麼",
        "怎麼", "這裡", "那裡", "這個", "那個", "這些", "那些", "如果",
        "因為", "所以", "雖然", "但是", "而且", "然後", "或者", "以及",
        "突然", "立刻", "馬上", "漸漸", "慢慢", "輕輕", "默默", "靜靜",
        "哈哈", "嘿嘿", "呵呵", "嘻嘻", "喃喃", "微微", "悄悄"
    }

    @staticmethod
    def get_default_settings() -> dict:
        return {
            "enabled": True,
            "rules": {
                "redundant_phrase": True,
                "high_density_particle": True,
                "passive_voice": True,
                "duplicate_words": True
            },
            "particle_density_threshold": 3,   # 單句中同虛詞出現 3 次以上
            "whitelist": [],                   # 使用者自訂忽略白名單
            "custom_redundant_words": []       # 使用者自訂贅詞片語庫
        }

    @classmethod
    def load_settings(cls, path: Optional[str] = None) -> dict:
        settings_path = path or cls.DEFAULT_SETTINGS_PATH
        if not os.path.exists(settings_path):
            defaults = cls.get_default_settings()
            cls.save_settings(defaults, settings_path)
            return defaults
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            defaults = cls.get_default_settings()
            # 合併預設值防呆
            if "enabled" not in data:
                data["enabled"] = defaults["enabled"]
            if "rules" not in data:
                data["rules"] = defaults["rules"]
            else:
                for k, v in defaults["rules"].items():
                    if k not in data["rules"]:
                        data["rules"][k] = v
            if "whitelist" not in data:
                data["whitelist"] = []
            if "custom_redundant_words" not in data:
                data["custom_redundant_words"] = []
            if "particle_density_threshold" not in data:
                data["particle_density_threshold"] = 3
            return data
        except Exception:
            return cls.get_default_settings()

    @classmethod
    def save_settings(cls, settings: dict, path: Optional[str] = None):
        settings_path = path or cls.DEFAULT_SETTINGS_PATH
        try:
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"儲存 Lint 設定失敗: {e}")

    @classmethod
    def check_text(cls, text: str, settings: Optional[dict] = None) -> List[LintIssue]:
        """對純文字進行多維度文風與贅詞檢查。"""
        if not text:
            return []

        settings = settings or cls.load_settings()
        if not settings.get("enabled", True):
            return []

        rules = settings.get("rules", {})
        whitelist: Set[str] = set(settings.get("whitelist", []))
        custom_words: List[str] = settings.get("custom_redundant_words", [])
        particle_thresh: int = settings.get("particle_density_threshold", 3)

        issues: List[LintIssue] = []

        # 建立行號查詢表（累積字元數 -> 行號）
        lines = text.splitlines(keepends=True)
        line_start_offsets = []
        curr_offset = 0
        for line in lines:
            line_start_offsets.append(curr_offset)
            curr_offset += len(line)

        def get_line_number(char_pos: int) -> int:
            for idx in range(len(line_start_offsets) - 1, -1, -1):
                if char_pos >= line_start_offsets[idx]:
                    return idx + 1
            return 1

        # 1. 規則一：公文與冗贅片語檢查
        if rules.get("redundant_phrase", True):
            all_redundant = cls.DEFAULT_REDUNDANT_PHRASES + custom_words
            for phrase in all_redundant:
                if not phrase or phrase in whitelist:
                    continue
                # 搜尋所有出現位置
                start = 0
                while True:
                    idx = text.find(phrase, start)
                    if idx == -1:
                        break
                    line_num = get_line_number(idx)
                    issues.append(LintIssue(
                        line_number=line_num,
                        start_pos=idx,
                        end_pos=idx + len(phrase),
                        issue_type="redundant_phrase",
                        issue_type_name="公文/冗贅片語",
                        target_text=phrase,
                        message=f"發現可能過於冗贅或具公文風格的片語「{phrase}」",
                        suggestion="建議精簡刪除，或改以生動的主動動作描述。"
                    ))
                    start = idx + len(phrase)

        # 2. 規則二：被動語態弱動詞檢查
        if rules.get("passive_voice", True):
            for p_word in cls.DEFAULT_PASSIVE_WORDS:
                if p_word in whitelist:
                    continue
                start = 0
                while True:
                    idx = text.find(p_word, start)
                    if idx == -1:
                        break
                    # 取前後 10 字上下文輔助判斷
                    ctx_start = max(0, idx - 4)
                    ctx_end = min(len(text), idx + len(p_word) + 6)
                    snippet = text[ctx_start:ctx_end]
                    line_num = get_line_number(idx)
                    issues.append(LintIssue(
                        line_number=line_num,
                        start_pos=idx,
                        end_pos=idx + len(p_word),
                        issue_type="passive_voice",
                        issue_type_name="被動語態",
                        target_text=snippet,
                        message=f"使用了被動標記詞「{p_word}」（{snippet}）",
                        suggestion="中文小說多以主動句為主，過多被動句易減弱文字張力。"
                    ))
                    start = idx + len(p_word)

        # 3. 規則三：單句高頻虛詞密度檢查
        if rules.get("high_density_particle", True):
            # 以中英文句點、問號、驚嘆號、分號、換行分句
            sentence_splits = list(re.finditer(r'[^。！？!?;；\r\n]+', text))
            for match in sentence_splits:
                sent = match.group()
                sent_start = match.start()
                sent_len = len(sent)
                if sent_len < 10:
                    continue

                for p in cls.PARTICLES:
                    if p in whitelist:
                        continue
                    count = sent.count(p)
                    # 判斷門檻：單句內同虛詞出現 >= 門檻 且 密度 >= 8%
                    if count >= particle_thresh and (count / sent_len) >= 0.08:
                        line_num = get_line_number(sent_start)
                        issues.append(LintIssue(
                            line_number=line_num,
                            start_pos=sent_start,
                            end_pos=sent_start + sent_len,
                            issue_type="high_density_particle",
                            issue_type_name="虛詞過密",
                            target_text=f"「{p}」×{count} 次 ({sent[:25]}...)",
                            message=f"單句內虛詞「{p}」重複出現 {count} 次，密度過高",
                            suggestion=f"建議適度精簡或改寫句構，減少「{p}」字出現頻率。"
                        ))

        # 4. 規則四：相鄰重複詞彙檢查 (2~4 字中文詞在近距離重複)
        if rules.get("duplicate_words", True):
            # 取出所有連續 2~4 字的中文詞語
            zh_chunks = re.findall(r'[\u4e00-\u9fa5]{2,4}', text)
            # 建立位置索引
            checked_words = set()
            for chunk in zh_chunks:
                if chunk in cls.DUPLICATE_IGNORE_SET or chunk in whitelist or chunk in checked_words:
                    continue
                checked_words.add(chunk)

                # 尋找所有出現位置
                indices = []
                start = 0
                while True:
                    idx = text.find(chunk, start)
                    if idx == -1:
                        break
                    indices.append(idx)
                    start = idx + len(chunk)

                if len(indices) >= 2:
                    for i in range(len(indices) - 1):
                        diff = indices[i+1] - indices[i]
                        # 若兩詞相距在 35 個字元以內
                        if diff <= 35:
                            line_num = get_line_number(indices[i+1])
                            issues.append(LintIssue(
                                line_number=line_num,
                                start_pos=indices[i+1],
                                end_pos=indices[i+1] + len(chunk),
                                issue_type="duplicate_words",
                                issue_type_name="相鄰重複用詞",
                                target_text=chunk,
                                message=f"詞彙「{chunk}」在相隔僅 {diff} 字內重複出現",
                                suggestion="建議使用代名詞、同義詞替換或精簡句意，提升行文多樣性。"
                            ))

        # 依出現順序 (start_pos) 排序
        issues.sort(key=lambda x: x.start_pos)
        return issues
