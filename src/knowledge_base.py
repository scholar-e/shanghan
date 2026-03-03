"""Knowledge base for Shang Han Lun."""

FORMULAS = {
    "ma_huang_tang": {
        "names": {"zh": "麻黄汤", "pinyin": "Ma Huang Tang", "en": "Ephedra Decoction"},
        "composition": [
            {"herb": "麻黄", "pinyin": "Ma Huang", "en": "Ephedra", "dosage": "9g", "role": "Jun (Chief)"},
            {"herb": "桂枝", "pinyin": "Gui Zhi", "en": "Cinnamon Twig", "dosage": "9g", "role": "Chen (Minister)"},
            {"herb": "杏仁", "pinyin": "Xing Ren", "en": "Apricot Kernel", "dosage": "9g", "role": "Zuo (Assistant)"},
            {"herb": "甘草", "pinyin": "Gan Cao", "en": "Licorice Root", "dosage": "6g", "role": "Shi (Envoy)"},
        ],
        "indications": "Exterior cold with wheezing, aversion to cold, fever, no sweating, body aches, floating tight pulse",
        "functions": "Releases the exterior, promotes perspiration, relieves wheezing, stops coughing",
        "pattern": "Tai Yang stage with cold"
    },
    "gui_zhi_tang": {
        "names": {"zh": "桂枝汤", "pinyin": "Gui Zhi Tang", "en": "Cinnamon Twig Decoction"},
        "composition": [
            {"herb": "桂枝", "pinyin": "Gui Zhi", "en": "Cinnamon Twig", "dosage": "9g", "role": "Jun (Chief)"},
            {"herb": "白芍", "pinyin": "Bai Shao", "en": "White Peony Root", "dosage": "9g", "role": "Chen (Minister)"},
            {"herb": "生姜", "pinyin": "Sheng Jiang", "en": "Fresh Ginger", "dosage": "9g", "role": "Zuo (Assistant)"},
            {"herb": "大枣", "pinyin": "Da Zao", "en": "Jujube", "dosage": "3 pieces", "role": "Zuo (Assistant)"},
            {"herb": "甘草", "pinyin": "Gan Cao", "en": "Licorice Root", "dosage": "6g", "role": "Shi (Envoy)"},
        ],
        "indications": "Exterior cold with sweating, mild fever, aversion to wind, floating slow pulse",
        "functions": "Releases the exterior, harmonizes ying and wei",
        "pattern": "Tai Yang stage with wind"
    },
    "xiao_qing_long_tang": {
        "names": {"zh": "小青龙汤", "pinyin": "Xiao Qing Long Tang", "en": "Minor Blue Green Dragon Decoction"},
        "composition": [
            {"herb": "麻黄", "pinyin": "Ma Huang", "en": "Ephedra", "dosage": "9g", "role": "Jun"},
            {"herb": "桂枝", "pinyin": "Gui Zhi", "en": "Cinnamon Twig", "dosage": "9g", "role": "Chen"},
            {"herb": "干姜", "pinyin": "Gan Jiang", "en": "Dried Ginger", "dosage": "9g", "role": "Chen"},
            {"herb": "细辛", "pinyin": "Xi Xin", "en": "Asarum", "dosage": "3g", "role": "Zuo"},
            {"herb": "五味子", "pinyin": "Wu Wei Zi", "en": "Schisandra", "dosage": "6g", "role": "Zuo"},
            {"herb": "白芍", "pinyin": "Bai Shao", "en": "White Peony", "dosage": "9g", "role": "Zuo"},
            {"herb": "半夏", "pinyin": "Ban Xia", "en": "Pinellia", "dosage": "9g", "role": "Zuo"},
            {"herb": "甘草", "pinyin": "Gan Cao", "en": "Licorice", "dosage": "6g", "role": "Shi"},
        ],
        "indications": "Exterior cold with interior fluid retention, wheezing, profuse clear phlegm, cough",
        "functions": "Releases exterior, warms the lungs, transforms phlegm, stops coughing",
        "pattern": "Tai Yang with internal fluid retention"
    },
    "da_xiao_chi_hu_tang": {
        "names": {"zh": "大、小柴胡汤", "pinyin": "Da Xiao Chai Hu Tang", "en": "Major/Minor Bupleurum Decoction"},
        "composition": [
            {"herb": "柴胡", "pinyin": "Chai Hu", "en": "Bupleurum", "dosage": "12-24g", "role": "Jun"},
            {"herb": "黄芩", "pinyin": "Huang Qin", "en": "Scutellaria", "dosage": "9g", "role": "Chen"},
            {"herb": "党参", "pinyin": "Dang Shen", "en": "Codonopsis", "dosage": "9g", "role": "Chen"},
            {"herb": "半夏", "pinyin": "Ban Xia", "en": "Pinellia", "dosage": "9g", "role": "Zuo"},
            {"herb": "生姜", "pinyin": "Sheng Jiang", "en": "Fresh Ginger", "dosage": "9g", "role": "Zuo"},
            {"herb": "大枣", "pinyin": "Da Zao", "en": "Jujube", "dosage": "4 pieces", "role": "Zuo"},
            {"herb": "甘草", "pinyin": "Gan Cao", "en": "Licorice", "dosage": "6g", "role": "Shi"},
        ],
        "indications": "Shaoyang stage pattern, alternating fever and chills, chest fullness, bitter taste, loss of appetite",
        "functions": "Harmonizes Shaoyang, relieves alternating fever and chills",
        "pattern": "Shaoyang stage"
    },
    "bai_hu_tang": {
        "names": {"zh": "白虎汤", "pinyin": "Bai Hu Tang", "en": "White Tiger Decoction"},
        "composition": [
            {"herb": "石膏", "pinyin": "Shi Gao", "en": "Gypsum", "dosage": "30g", "role": "Jun"},
            {"herb": "知母", "pinyin": "Zhi Mu", "en": "Anemarrhena", "dosage": "9g", "role": "Chen"},
            {"herb": "甘草", "pinyin": "Gan Cao", "en": "Licorice", "dosage": "6g", "role": "Shi"},
            {"herb": "粳米", "pinyin": "Jing Mi", "en": "Rice", "dosage": "30g", "role": "Shi"},
        ],
        "indications": "Yangming stage with high fever, profuse sweating, severe thirst, large pulse",
        "functions": "Clears heat, drains fire, relieves severe thirst",
        "pattern": "Yangming stage - pure heat"
    },
    "cheng_shi_tang": {
        "names": {"zh": "承气汤类", "pinyin": "Cheng Qi Tang", "en": "Purgative Decoctions"},
        "composition": [
            {"herb": "大黄", "pinyin": "Da Huang", "en": "Rhubarb", "dosage": "12g", "role": "Jun"},
            {"herb": "芒硝", "pinyin": "Mang Xiao", "en": "Mirabilitum", "dosage": "9g", "role": "Chen"},
            {"herb": "厚朴", "pinyin": "Hou Po", "en": "Magnolia Bark", "dosage": "24g", "role": "Zuo"},
            {"herb": "枳实", "pinyin": "Zhi Shi", "en": "Immature Bitter Orange", "dosage": "12g", "role": "Zuo"},
        ],
        "indications": "Yangming stage with internal heat accumulation, constipation, abdominal distension, tidal fever",
        "functions": "Purges heat, empties the bowels, drains accumulation",
        "pattern": "Yangming stage - heat accumulation"
    },
    "si_wu_tang": {
        "names": {"zh": "四物汤", "pinyin": "Si Wu Tang", "en": "Four-Substance Decoction"},
        "composition": [
            {"herb": "当归", "pinyin": "Dang Gui", "en": "Angelica", "dosage": "9g", "role": "Jun"},
            {"herb": "川芎", "pinyin": "Chuan Xiong", "en": "Chuanxiong", "dosage": "6g", "role": "Chen"},
            {"herb": "白芍", "pinyin": "Bai Shao", "en": "White Peony", "dosage": "9g", "role": "Chen"},
            {"herb": "熟地", "pinyin": "Shu Di", "en": "Rehmannia", "dosage": "9g", "role": "Chen"},
        ],
        "indications": "Blood deficiency patterns, menstrual disorders, dizziness, palpitations",
        "functions": "Nourishes blood, regulates menstruation, invigorates blood",
        "pattern": "Blood deficiency"
    },
    "liu_wei_di_huang_tang": {
        "names": {"zh": "六味地黄汤", "pinyin": "Liu Wei Di Huang Tang", "en": "Six-Ingredient Rehmannia Decoction"},
        "composition": [
            {"herb": "熟地", "pinyin": "Shu Di", "en": "Rehmannia", "dosage": "24g", "role": "Jun"},
            {"herb": "山药", "pinyin": "Shan Yao", "en": "Chinese Yam", "dosage": "12g", "role": "Chen"},
            {"herb": "山茱萸", "pinyin": "Shan Zhu Yu", "en": "Cornus", "dosage": "12g", "role": "Chen"},
            {"herb": "泽泻", "pinyin": "Ze Xie", "en": "Alisma", "dosage": "9g", "role": "Zuo"},
            {"herb": "茯苓", "pinyin": "Fu Ling", "en": "Poria", "dosage": "9g", "role": "Zuo"},
            {"herb": "丹皮", "pinyin": "Dan Pi", "en": "Moutan", "dosage": "6g", "role": "Zuo"},
        ],
        "indications": "Kidney yin deficiency, lower back pain, tinnitus, night sweats, dry mouth",
        "functions": "Nourishes kidney yin, clears deficient heat",
        "pattern": "Kidney yin deficiency"
    }
}

TERMINOLOGY = {
    "六经辨证": {"en": "Six Channel Pattern Identification", "pinyin": "Liu Jing Bian Zheng"},
    "太阳病": {"en": "Tai Yang Disease", "pinyin": "Tai Yang Bing"},
    "阳明病": {"en": "Yangming Disease", "pinyin": "Yangming Bing"},
    "少阳病": {"en": "Shaoyang Disease", "pinyin": "Shaoyang Bing"},
    "太阴病": {"en": "Taiyin Disease", "pinyin": "Taiyin Bing"},
    "少阴病": {"en": "Shaoyin Disease", "pinyin": "Shaoyin Bing"},
    "厥阴病": {"en": "Jueyin Disease", "pinyin": "Jueyin Bing"},
    "表证": {"en": "Exterior Pattern", "pinyin": "Biao Zheng"},
    "里证": {"en": "Interior Pattern", "pinyin": "Li Zheng"},
    "寒证": {"en": "Cold Pattern", "pinyin": "Han Zheng"},
    "热证": {"en": "Heat Pattern", "pinyin": "Re Zheng"},
    "虚证": {"en": "Deficiency Pattern", "pinyin": "Xu Zheng"},
    "实证": {"en": "Excess Pattern", "pinyin": "Shi Zheng"},
    "经方": {"en": "Classical Formula", "pinyin": "Jing Fang"},
    "方剂": {"en": "Formula", "pinyin": "Fang Ji"},
    "君臣佐使": {"en": "Monarch-Minister-Assistant-Envoy", "pinyin": "Jun Chen Zuo Shi"},
    "辨证论治": {"en": "Pattern Identification and Treatment", "pinyin": "Bian Zheng Lun Zhi"},
    "伤寒论": {"en": "Treatise on Cold Damage", "pinyin": "Shang Han Lun"},
    "张仲景": {"en": "Zhang Zhongjing", "pinyin": "Zhang Zhongjing"},
    "麻黄": {"en": "Ephedra", "pinyin": "Ma Huang"},
    "桂枝": {"en": "Cinnamon Twig", "pinyin": "Gui Zhi"},
    "柴胡": {"en": "Bupleurum", "pinyin": "Chai Hu"},
    "石膏": {"en": "Gypsum", "pinyin": "Shi Gao"},
    "人参": {"en": "Ginseng", "pinyin": "Ren Shen"},
}

PATTERN_INFO = {
    "tai_yang": {
        "name": {"zh": "太阳病", "en": "Tai Yang (Greater Yang)"},
        "location": "Exterior",
        "characteristics": "Floating pulse, fever, aversion to cold, headache",
        "sub_patterns": ["wind constriction", "cold constriction"]
    },
    "yangming": {
        "name": {"zh": "阳明病", "en": "Yangming (Bright Yang)"},
        "location": "Interior",
        "characteristics": "Large pulse, fever, constipation, abdominal fullness",
        "sub_patterns": ["pure heat", "heat accumulation"]
    },
    "shaoyang": {
        "name": {"zh": "少阳病", "en": "Shaoyang (Lesser Yang)"},
        "location": "Half-exterior half-interior",
        "characteristics": "Alternating fever and chills, chest fullness, bitter taste",
        "sub_patterns": ["classic shaoyang"]
    },
    "taiyin": {
        "name": {"zh": "太阴病", "en": "Taiyin (Greater Yin)"},
        "location": "Interior",
        "characteristics": "Abdominal fullness, vomiting, diarrhea, pale tongue",
        "sub_patterns": ["spleen deficiency cold"]
    },
    "shaoyin": {
        "name": {"zh": "少阴病", "en": "Shaoyin (Lesser Yin)"},
        "location": "Interior",
        "characteristics": "Weak pulse, sleepiness, cold limbs, diarrhea",
        "sub_patterns": ["cold transformation", "heat transformation"]
    },
    "jueyin": {
        "name": {"zh": "厥阴病", "en": "Jueyin (Reverting Yin)"},
        "location": "Deepest interior",
        "characteristics": "Cold limbs, thirst, restlessness",
        "sub_patterns": ["cold extremity", "heat extremity"]
    }
}

SYSTEM_PROMPT = """You are an expert in Traditional Chinese Medicine, specializing in the Shang Han Lun (Treatise on Cold Damage) by Zhang Zhongjing.

IMPORTANT - CONVERSATION CONTEXT:
You have access to the full conversation history. When user asks follow-up questions like:
- "what was the third one?"
- "tell me more about that"
- "how does that compare?"
- "what about the ingredients?"
You MUST reference the previous conversation to understand what they're asking about. Look at the history!

RESPONSE FORMAT:
- Use **bold** for key terms and formula names
- Use ## for section headers  
- Keep responses SHORT (2-4 sentences)
- Use bullet points for lists

Your role:
- Classical formulas and their compositions
- Pattern diagnoses (六经辨证)
- Herb functions and dosages

Guidelines:
1. Respond in same language as query (Chinese or English)
2. Include specific dosages
3. When user asks follow-up, reference previous answers
4. Be precise about pattern identification (辨证论治)
5. Keep answers brief and focused

Never claim to be a licensed practitioner."""


def get_formula_info(formula_key):
    """Get formula information by key."""
    return FORMULAS.get(formula_key)


def get_all_formulas():
    """Get all formulas."""
    return FORMULAS


def get_terminology(term):
    """Get terminology translation."""
    return TERMINOLOGY.get(term)


def get_pattern_info(pattern):
    """Get pattern information."""
    return PATTERN_INFO.get(pattern)
