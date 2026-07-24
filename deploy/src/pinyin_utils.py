"""Lightweight pinyin matching helpers for local search.

This avoids a runtime dependency while covering the Shanghan formula and herb
vocabulary used by the app.
"""

import re
import unicodedata


PINYIN_BY_CHAR = {
    "一": "yi", "七": "qi", "三": "san", "上": "shang", "下": "xia", "不": "bu",
    "两": "liang", "个": "ge", "中": "zhong", "丸": "wan", "丹": "dan", "为": "wei",
    "乌": "wu", "二": "er", "五": "wu", "人": "ren", "仁": "ren", "代": "dai",
    "以": "yi", "仲": "zhong", "伤": "shang", "佐": "zuo", "余": "yu", "作": "zuo",
    "使": "shi", "依": "yi", "党": "dang", "入": "ru", "八": "ba", "六": "liu",
    "内": "nei", "冬": "dong", "分": "fen", "切": "qie", "别": "bie", "制": "zhi",
    "剂": "ji", "前": "qian", "加": "jia", "匕": "bi", "十": "shi", "升": "sheng",
    "半": "ban", "即": "ji", "厚": "hou", "厥": "jue", "去": "qu", "参": "shen",
    "又": "you", "及": "ji", "古": "gu", "可": "ke", "右": "you", "叶": "ye",
    "各": "ge", "合": "he", "君": "jun", "吴": "wu", "味": "wei", "商": "shang",
    "四": "si", "地": "di", "增": "zeng", "壳": "qiao", "处": "chu", "夏": "xia",
    "大": "da", "太": "tai", "头": "tou", "好": "hao", "如": "ru", "妇": "fu",
    "姜": "jiang", "婢": "bi", "子": "zi", "字": "zi", "宋": "song", "完": "wan",
    "实": "shi", "寒": "han", "导": "dao", "小": "xiao", "少": "shao", "尖": "jian",
    "尺": "chi", "尿": "niao", "山": "shan", "川": "chuan", "巴": "ba", "干": "gan",
    "建": "jian", "强": "qiang", "归": "gui", "当": "dang", "录": "lu", "心": "xin",
    "戟": "ji", "承": "cheng", "把": "ba", "抵": "di", "按": "an", "挺": "ting",
    "据": "ju", "擘": "bo", "散": "san", "文": "wen", "斤": "jin", "方": "fang",
    "施": "shi", "旋": "xuan", "无": "wu", "旦": "dan", "明": "ming", "是": "shi",
    "景": "jing", "有": "you", "末": "mo", "本": "ben", "术": "zhu", "朴": "po",
    "杏": "xing", "枚": "mei", "枝": "zhi", "枣": "zao", "枳": "zhi", "柏": "bai",
    "柴": "chai", "栀": "zhi", "栝": "gua", "核": "he", "根": "gen", "桂": "gui",
    "桃": "tao", "桑": "sang", "桔": "jie", "梅": "mei", "梓": "zi", "梗": "geng",
    "椒": "jiao", "此": "ci", "武": "wu", "母": "mu", "气": "qi", "水": "shui",
    "汁": "zhi", "汗": "han", "汤": "tang", "治": "zhi", "注": "zhu", "泻": "xie",
    "泽": "ze", "洗": "xi", "海": "hai", "浸": "jin", "涪": "fu", "清": "qing",
    "滑": "hua", "漆": "qi", "灰": "hui", "炙": "zhi", "炮": "pao", "烧": "shao",
    "热": "re", "煎": "jian", "熟": "shu", "熬": "ao", "牡": "mu", "物": "wu",
    "猪": "zhu", "玄": "xuan", "理": "li", "瓜": "gua", "甘": "gan", "生": "sheng",
    "用": "yong", "病": "bing", "白": "bai", "百": "bai", "皮": "pi", "着": "zhuo",
    "知": "zhi", "石": "shi", "研": "yan", "破": "po", "硝": "xiao", "碎": "sui",
    "禹": "yu", "秦": "qin", "竹": "zhu", "等": "deng", "米": "mi", "类": "lei",
    "粒": "li", "粮": "liang", "粳": "jing", "细": "xi", "经": "jing", "编": "bian",
    "翁": "weng", "翅": "chi", "翘": "qiao", "者": "zhe", "肤": "fu", "胃": "wei",
    "胆": "dan", "胡": "hu", "胶": "jiao", "胸": "xiong", "脂": "zhi", "脉": "mai",
    "腥": "xing", "膏": "gao", "臣": "chen", "节": "jie", "芍": "shao", "芎": "xiong",
    "芒": "mang", "芩": "qin", "芫": "yuan", "花": "hua", "苈": "li", "苓": "ling",
    "苦": "ku", "茎": "jing", "茯": "fu", "茱": "zhu", "茵": "yin", "草": "cao",
    "药": "yao", "萎": "wei", "萸": "yu", "葛": "ge", "葱": "cong", "葶": "ting",
    "蒂": "di", "蒌": "lou", "蕤": "rui", "藻": "zao", "虎": "hu", "虚": "xu",
    "虫": "chong", "虻": "meng", "蛎": "li", "蛤": "ge", "蛭": "zhi", "蛸": "xiao",
    "蜀": "shu", "蜜": "mi", "螵": "piao", "表": "biao", "裈": "kun", "覆": "fu",
    "论": "lun", "证": "zheng", "详": "xiang", "调": "tiao", "豆": "dou", "豉": "chi",
    "贝": "bei", "赤": "chi", "赭": "zhe", "越": "yue", "足": "zu", "辛": "xin",
    "辨": "bian", "近": "jin", "连": "lian", "逆": "ni", "通": "tong", "遂": "sui",
    "遗": "yi", "酒": "jiu", "里": "li", "重": "chong", "量": "liang", "钱": "qian",
    "铅": "qian", "铢": "zhu", "门": "men", "阙": "que", "阳": "yang", "阴": "yin",
    "阿": "e", "附": "fu", "陆": "lu", "陈": "chen", "陷": "xian", "青": "qing",
    "饴": "yi", "香": "xiang", "骨": "gu", "鸡": "ji", "麦": "mai", "麻": "ma",
    "黄": "huang", "黑": "hei", "龙": "long",
}


def normalize_pinyin(value):
    """Lowercase, strip tone marks, and remove non-alphanumerics."""
    if value is None:
        return ""
    decomposed = unicodedata.normalize("NFKD", str(value))
    ascii_text = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", ascii_text.lower())


def chinese_to_pinyin(value):
    syllables = []
    for ch in str(value or ""):
        py = PINYIN_BY_CHAR.get(ch)
        if py:
            syllables.append(py)
    return " ".join(syllables)


def pinyin_candidates(value):
    candidates = []
    raw = str(value or "")
    if raw:
        candidates.append(raw)
    generated = chinese_to_pinyin(raw)
    if generated:
        candidates.append(generated)
    return candidates


def pinyin_matches(query, *values):
    normalized_query = normalize_pinyin(query)
    if not normalized_query:
        return False
    for value in values:
        for candidate in pinyin_candidates(value):
            if normalized_query in normalize_pinyin(candidate):
                return True
    return False


def looks_like_pinyin_query(query):
    decomposed = unicodedata.normalize("NFKD", str(query or ""))
    plain = "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower()
    tokens = re.findall(r"[a-z]+", plain)
    if len(tokens) < 2:
        return False
    known = set(PINYIN_BY_CHAR.values())
    return all(token in known for token in tokens)
