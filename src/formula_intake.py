"""Intake gate for formula recommendation requests."""

import re


RECOMMENDATION_PATTERNS = [
    r"\bwhat formula\b",
    r"\bwhich formula\b",
    r"\brecommend\b",
    r"\bsuggest\b",
    r"\bprescrib",
    r"\btreat(?:ment)?\b",
    r"\bfor my\b",
    r"\bi have\b",
    r"用什么方",
    r"什么方",
    r"推荐",
    r"建议",
    r"开方",
    r"治疗",
    r"治",
]

FORMULA_DISCUSSION_PATTERNS = [
    r"\bwhat is\b",
    r"\btell me about\b",
    r"\bcomposition\b",
    r"\bingredient",
    r"\bdosage\b",
    r"是什么",
    r"组成",
    r"剂量",
    r"条文",
]

DETAIL_CATEGORIES = {
    "chief_complaint": [
        r"pain", r"ache", r"cough", r"喘", r"痛", r"咳", r"吐", r"泻", r"利", r"汗", r"渴", r"烦", r"cold", r"chill", r"fever", r"热", r"寒",
    ],
    "duration_onset": [
        r"\bday", r"\bdays", r"\bweek", r"\bweeks", r"\bhour", r"\bhours", r"\bmonth", r"\bmonths", r"天", r"日", r"周", r"月", r"多久", r"开始",
    ],
    "temperature_sweating": [
        r"fever", r"chill", r"sweat", r"aversion", r"hot", r"cold", r"发热", r"恶寒", r"恶风", r"汗", r"怕冷", r"怕风",
    ],
    "digestion_elimination": [
        r"stool", r"bowel", r"diarrhea", r"constipat", r"urine", r"appetite", r"nausea", r"vomit", r"便", r"大便", r"小便", r"尿", r"食欲", r"呕",
    ],
    "thirst_fluids": [
        r"thirst", r"drink", r"dry mouth", r"phlegm", r"mucus", r"渴", r"口干", r"饮", r"痰",
    ],
    "pulse_tongue": [
        r"pulse", r"tongue", r"脉", r"舌",
    ],
    "safety_context": [
        r"pregnan", r"medication", r"medicine", r"diagnos", r"doctor", r"blood pressure", r"heart", r"kidney", r"liver", r"怀孕", r"药", r"西药", r"诊断", r"医生", r"血压", r"心", r"肾", r"肝",
    ],
}


def wants_formula_recommendation(query):
    text = query.lower()
    if any(re.search(pattern, text) for pattern in FORMULA_DISCUSSION_PATTERNS):
        return False
    has_formula_language = any(term in text for term in ["formula", "prescription", "方", "汤", "丸", "散"])
    has_recommendation_language = any(re.search(pattern, text) for pattern in RECOMMENDATION_PATTERNS)
    return has_recommendation_language and (has_formula_language or any(term in text for term in ["treat", "治疗", "治"]))


def _recent_user_text(query, conversation_history):
    user_parts = []
    for msg in (conversation_history or [])[-8:]:
        if msg.get("role") == "user":
            user_parts.append(str(msg.get("content", "")))
    user_parts.append(query)
    return "\n".join(user_parts).lower()


def formula_intake_detail_count(query, conversation_history=None):
    text = _recent_user_text(query, conversation_history)
    return sum(
        1
        for patterns in DETAIL_CATEGORIES.values()
        if any(re.search(pattern, text) for pattern in patterns)
    )


def needs_formula_followup(query, conversation_history=None, min_categories=4):
    if not wants_formula_recommendation(query):
        return False
    return formula_intake_detail_count(query, conversation_history) < min_categories


def formula_followup_response(query):
    chinese = re.search(r"[\u4e00-\u9fff]", query or "") is not None
    if chinese:
        return (
            "在建议方剂前，我需要先补齐辨证信息。请回答这些问题：\n\n"
            "1. 主要症状是什么，持续多久了？\n"
            "2. 有无发热、恶寒/恶风、出汗？\n"
            "3. 口渴、饮水、食欲、大便、小便如何？\n"
            "4. 舌象和脉象如何？\n"
            "5. 是否怀孕、正在服药，或有心肝肾等重大病史？"
        )

    return (
        "Before suggesting a formula, I need a few pattern details first:\n\n"
        "1. What are the main symptoms, and how long have they been present?\n"
        "2. Any fever, chills/aversion to wind, or sweating?\n"
        "3. How are thirst, fluid intake, appetite, stool, and urination?\n"
        "4. What are the tongue and pulse findings, if known?\n"
        "5. Any pregnancy, current medications, or major heart, liver, or kidney history?"
    )
