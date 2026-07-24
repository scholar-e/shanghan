import sys

sys.path.insert(0, "src")

from formula_intake import needs_formula_followup, formula_followup_response


def test_formula_recommendation_requires_followup_when_sparse():
    query = "What formula should I use for cough?"

    assert needs_formula_followup(query, []) is True
    response = formula_followup_response(query)
    assert "Before suggesting a formula" in response
    assert "tongue and pulse" in response


def test_formula_recommendation_can_proceed_after_intake_details():
    history = [
        {"role": "user", "content": "I have cough for three days with chills, no sweating, thirst, poor appetite, loose stool, pale tongue, floating pulse, no pregnancy or medications."}
    ]

    assert needs_formula_followup("Which formula would fit this pattern?", history) is False


def test_formula_information_request_is_not_blocked():
    assert needs_formula_followup("What is Gui Zhi Tang composition?", []) is False


def test_formula_extraction_ignores_blank_textbook_names():
    from chat_engine import extract_formulas_from_text

    formulas = extract_formulas_from_text("No formula is mentioned in this sentence.")

    assert formulas == []


def test_active_formulas_are_textbook_only():
    from knowledge_base import FORMULAS

    assert FORMULAS
    assert all(key.startswith("textbook_formula_") for key in FORMULAS)
    assert not any("大、小柴胡汤" in formula["names"].get("zh", "") for formula in FORMULAS.values())


def test_textbook_formula_fields_follow_source_text():
    from knowledge_base import FORMULAS

    formula = next(f for f in FORMULAS.values() if f.get("formula_number") == "27")

    assert formula["names"]["zh"] == "小柴胡汤方"
    assert formula["source_text"] == "柴胡 八两 黄芩 人参 甘草 炙 生姜 各三两 半夏 半升，洗 大枣 十二枚"
    assert formula["preparation_text"].startswith("合七味，以水一斗二升")
    assert "往来寒热" in formula["indications"]


def test_zabing_formula_fields_follow_source_text():
    from knowledge_base import FORMULAS

    formula = next(f for f in FORMULAS.values() if f.get("formula_number") == "195")

    assert formula["names"]["zh"] == "厚朴七物汤方"
    assert formula["yuanben_article_num"] == "26.9"
    assert formula["comparison_book"] == "金匮"
    assert formula["comparison_article_num"] == "10.9"
    assert formula["source_text"] == "厚朴 半斤 大黄 三两 甘草 三两 桂枝 二两 生姜 五两 枳实 五枚 大枣 十枚"
    assert formula["preparation_text"].startswith("合七味，以水一斗")
