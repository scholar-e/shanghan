"""Shared retrieval and source formatting for public search and AI tools.

Public search exposes textbook records only. Lecture retrieval is internal to
chat; its text is never part of the public source metadata.
"""

import re
from dataclasses import dataclass

import database as db
from knowledge_base import FORMULAS
from pinyin_utils import pinyin_matches


@dataclass(frozen=True)
class TextQuery:
    kind: str = "text"
    reference: str = ""
    edition: str = "fuling"


def parse_reference(query):
    text = str(query or "").strip()
    edition = "song" if re.search(r"宋本|宋版|\bsong(?:ben|\s+(?:edition|version))?\b", text, re.I) else "fuling"
    if re.search(r"金匮|\b(?:jingui|jin\s+gui)\b", text, re.I):
        edition = "jingui"
    yiji = re.search(r"(?<![A-Za-z0-9])YJ\s*\.?\s*(\d{1,3})(?!\d)|宜忌\s*(?:第\s*)?(\d{1,3})\s*条?", text, re.I)
    if yiji:
        return TextQuery("yiji", f"YJ.{int(next(v for v in yiji.groups() if v is not None))}")
    for kind, pattern in (
        ("formula", r"(?:方剂|方|formula)\s*#?\s*(\d{1,3})(?![\d.])"),
        ("lecture", r"(?:lecture|lesson|课(?:程)?|讲)\s*(\d{1,4})\b|第?\s*(\d{1,4})\s*[讲课]"),
    ):
        match = re.search(pattern, text, re.I)
        if match:
            return TextQuery(kind, str(int(next(v for v in match.groups() if v is not None))), edition)
    match = re.search(r"(?<![\d.])(\d{1,2})\.(\d{1,3})(?![\d.])", text)
    if not match:
        match = re.search(r"(?:chapter\s*|第?\s*)(\d{1,2})\s*(?:章|篇)?\s*(?:line|article|第)\s*(\d{1,3})\s*条?", text, re.I)
    if match:
        return TextQuery("decimal", f"{int(match[1])}.{int(match[2])}", edition)
    match = re.search(r"(?:line|article|chapter|条文)\s*#?\s*(\d{1,3})\b|第?\s*(\d{1,3})\s*(?:条文|条|章)", text, re.I)
    if not match:
        match = re.fullmatch(r"(?:(?:宋本|涪陵古本|songben|song|fuling)\s*)?(\d{1,3})", text, re.I)
    if match:
        return TextQuery("line", str(int(next(v for v in match.groups() if v is not None))), edition)
    return TextQuery(edition=edition)


def expand_formula_pinyin_query(query):
    expanded = [str(query or "")]
    for formula in FORMULAS.values():
        names = formula.get("names", {})
        title = formula.get("formula_title") or names.get("zh", "")
        if title and pinyin_matches(query, title, names.get("zh", ""), names.get("pinyin", "")):
            expanded.extend([title, title.removesuffix("方")])
    return " ".join(dict.fromkeys(expanded))


def search_formulas(query, mode="text", limit=12):
    if not str(query or "").strip():
        return []
    parsed = parse_reference(query)
    query_lower = query.lower().strip()
    formula_results = []
    for key, formula in FORMULAS.items():
        if parsed.kind in ("line", "lecture", "decimal", "yiji"):
            continue
        names = formula['names']
        matches = []
        if parsed.kind == "formula":
            if str(formula.get("formula_number")) != parsed.reference:
                continue
            matches.append("方号")
        for lang, name in names.items():
            alias = str(name).lower().strip()
            short_alias = alias.removesuffix("方")
            if alias and (query_lower in alias or (len(short_alias) >= 2 and short_alias in query_lower) or pinyin_matches(query, name)):
                label = {'zh': '中文名', 'pinyin': '拼音', 'en': '英文名'}.get(lang, lang)
                matches.append(f"名称 ({label})")
        title = formula.get('formula_title') or ''
        if title and pinyin_matches(query, title):
            matches.append("名称 (拼音)")
        if mode == 'text':
            for i, herb in enumerate(formula['composition']):
                for field in ['herb', 'pinyin', 'en']:
                    value = herb.get(field, '')
                    if query_lower in str(value).lower() or pinyin_matches(query, value):
                        label = {'herb': '中文', 'pinyin': '拼音', 'en': '英文'}.get(field, field)
                        matches.append(f"组成 {i+1} ({label}: {value})")
            if query_lower in formula['indications'].lower():
                matches.append("条文")
            if query_lower in formula['functions'].lower():
                matches.append("功能")
            if query_lower in formula['pattern'].lower():
                matches.append("证型")
        if matches:
            pattern = formula['pattern']
            if ' with ' in pattern:
                category = pattern.split(' with ')[0].strip()
            elif ' - ' in pattern:
                category = pattern.split(' - ')[0].strip()
            elif '–' in pattern:
                category = pattern.split('–')[0].strip()
            else:
                category = pattern.strip()
            formula_results.append({
                'key': key,
                'names': names,
                'composition': formula['composition'],
                'indications': formula['indications'],
                'functions': formula['functions'],
                'pattern': pattern,
                'formula_number': formula.get('formula_number'),
                'formula_title': formula.get('formula_title'),
                'yuanben_article_num': formula.get('yuanben_article_num'),
                'songben_article_num': formula.get('songben_article_num'),
                'comparison_book': formula.get('comparison_book', '宋本'),
                'comparison_article_num': formula.get('comparison_article_num') or formula.get('songben_article_num'),
                'yuanben_text': formula.get('yuanben_text', ''),
                'songben_text': formula.get('songben_text', ''),
                'source_text': formula.get('source_text', ''),
                'preparation_text': formula.get('preparation_text', ''),
                'category': category,
                'matches': matches,
            })

    return formula_results[:limit]


def search_textbook(query, search_depth="shallow", limit=None):
    """Resolve explicit references before keyword parsing can split their numbers."""
    parsed = parse_reference(query)
    if parsed.kind in ("formula", "lecture") or not str(query or "").strip():
        return []
    results = []
    yiji_scope = bool(re.search(r"宜忌|\byi\s*ji\b", query, re.I))
    if parsed.kind in ("decimal", "yiji"):
        default_limit = 20 if db.normalize_search_depth(search_depth) == "shallow" else 100
        rows = db.get_zabing_by_reference(parsed.reference, parsed.edition, limit or default_limit)
    elif yiji_scope and parsed.kind == "text":
        rows = db.search_yiji_articles(query, search_depth=search_depth, limit=limit)
    else:
        # Numbers in ordinary prose (duration, dosage, etc.) are not line IDs.
        expanded = expand_formula_pinyin_query(re.sub(r"\d+", " ", query))
        lookup = expanded
        if parsed.kind == "line":
            lookup = ("songben " if parsed.edition == "song" else "") + parsed.reference
        fuling = [] if parsed.edition == "jingui" else db.search_fuling_articles(lookup, search_depth=search_depth, limit=limit)
        for row in fuling:
            results.append({
                "fuling_article_num": row["fuling_article_num"], "fuling_zh": row["fuling_zh"],
                "songben_article_num": row["song_article_num"], "songben_zh": row["song_zh"],
                "comparison_book": "宋本", "channel": row["channel"],
            })
        rows = [] if parsed.kind == "line" else db.search_zabing_articles(expanded, search_depth=search_depth, limit=limit)
        if parsed.kind == "line" and parsed.edition == "song":
            rows = db.get_zabing_by_reference(parsed.reference, "song", limit or 100)
        elif parsed.kind == "text":
            # Guide matches compete with the other textbook records even when
            # the larger corpus fills its keyword candidate limit first.
            guide_rows = db.search_yiji_articles(expanded, search_depth=search_depth, limit=limit)
            rows = list({row["entry_key"]: row for row in rows + guide_rows}.values())
    for row in rows:
        results.append({
            "entry_key": row["entry_key"], "fuling_article_num": row["fuling_ref"],
            "fuling_zh": row["fuling_zh"], "songben_article_num": row["comparison_ref"],
            "songben_zh": row["comparison_zh"], "comparison_book": row.get("comparison_book") or "金匮",
            "chapter_title": row.get("chapter_title") or "",
            "channel": "yiji" if row["fuling_ref"].startswith("YJ.") else "zabing",
        })
    if parsed.kind == "text":
        terms = db.parse_text_query(query)
        results.sort(key=lambda row: -db._score_text_row(
            row, query, terms, ["fuling_zh", "songben_zh", "chapter_title", "channel"],
        ))
    return results[:limit] if limit is not None else results


def search_lectures(query, search_depth="shallow", limit=3):
    parsed = parse_reference(query)
    if parsed.kind == "lecture":
        row = db.get_lesson(f"lesson{int(parsed.reference):04d}")
        if not row:
            return []
        content = row.get("content") or ""
        terms = [term for term in db.parse_text_query(query)
                 if not term.isdigit() and term not in ("lecture", "lesson")]
        positions = [content.lower().find(term.lower()) for term in terms]
        positions = [position for position in positions if position >= 0]
        start = max(0, min(positions) - 2000) if positions else 0
        return [dict(row, content=content[start:start + 8000])]
    if parsed.kind in ("line", "decimal", "formula", "yiji"):
        return []
    return db.search_lessons(expand_formula_pinyin_query(query), search_depth=search_depth, limit=limit)


def textbook_source(record):
    ref = record["fuling_article_num"]
    comparison = record.get("songben_article_num")
    book = record.get("comparison_book") or "宋本"
    label_en = "Jingui" if book == "金匮" else "Songben"
    zh = f"涪陵古本第 {ref} 条" + (f"（{book}第 {comparison} 条）" if comparison else "")
    en = f"Fulingben line {ref}" + (f" ({label_en} line {comparison})" if comparison else "")
    if record.get("channel") == "yiji":
        zh = f"涪陵古本宜忌 {ref}" + (f"（{book}第 {comparison} 条）" if comparison else "")
        en = f"Fulingben Yiji {ref}" + (f" ({label_en} line {comparison})" if comparison else "")
    text = f"【{zh}】{record['fuling_zh']}"
    if record.get("chapter_title"):
        text = f"{record['chapter_title']}\n{text}"
    if comparison and record.get("songben_zh"):
        text += f"\n【{book} {comparison}】{record['songben_zh']}"
    return {"title": zh, "title_zh": zh, "title_en": en,
            "type": "yiji_article" if record.get("channel") == "yiji" else "zabing_article" if record.get("entry_key") else "fuling_article",
            "key": record.get("entry_key") or f"fuling_{ref}"}, text


def formula_source(record):
    zh = formula_source_title(record, "zh")
    return {"title": zh, "title_zh": zh, "title_en": formula_source_title(record, "en"),
            "type": "formula", "key": record["key"]}, format_formula_context(record)


def lecture_source(record):
    number = int(re.search(r"\d+", record["lesson_id"])[0])
    zh = f"马寿椿医师第 {number} 讲"
    text = (record.get("content") or record.get("preview") or "").strip()
    return {"title": zh, "title_zh": zh, "title_en": f"Dr. Ma lecture {number}",
            "type": "lecture", "key": record["lesson_id"], "hide_in_popup": True}, f"[Lecture {number}] {text}"


def format_formula_context(formula):
    names = formula['names']
    comp = formula['composition']
    herbs = ", ".join([f"{c['herb']} ({c['pinyin']}, {c['dosage']})" for c in comp])
    roles = ", ".join([f"{c['herb']} as {c['role']}" for c in comp])
    title = formula.get("formula_title") or names["zh"]
    formula_number = formula.get("formula_number")
    source_text = formula.get("source_text")
    preparation_text = formula.get("preparation_text")
    formula_label = f"方 {formula_number}: {title}" if formula_number else f"Formula: {title}"
    if source_text:
        parts = [
            formula_label,
            f"Reference: {formula_source_title(formula, 'zh')}",
            f"Use/Textbook line: {formula.get('yuanben_text') or formula.get('indications') or ''}",
            source_text,
        ]
        if preparation_text:
            parts.append(f"Preparation:\n{preparation_text}")
        return "\n".join(parts)
    return f"""{formula_label} ({names['pinyin']}, {names['en']})
Reference: {formula_source_title(formula, "zh")}
Composition: {herbs}
Roles: {roles}
Indications: {formula['indications']}
Functions: {formula['functions']}
Pattern: {formula['pattern']}"""


def formula_source_title(formula, language="zh"):
    yuanben = formula.get("yuanben_article_num")
    comparison = formula.get("comparison_article_num") or formula.get("songben_article_num")
    comparison_book = formula.get("comparison_book") or "宋本"
    formula_number = formula.get("formula_number")
    name = formula.get("formula_title") or formula.get("names", {}).get("zh") or ""
    if language == "en":
        comparison_label = "Jingui" if comparison_book == "金匮" else "Songben"
        if yuanben and comparison:
            prefix = f"Fulingben line {yuanben} ({comparison_label} line {comparison})"
        elif yuanben:
            prefix = f"Fulingben line {yuanben}"
        elif comparison:
            prefix = f"{comparison_label} line {comparison}"
        else:
            prefix = "Shang Han Za Bing Lun"
        if formula_number:
            return f"{prefix} - Formula {formula_number}: {name}"
        return f"{prefix} - {name}".rstrip(" -")
    if yuanben and comparison:
        prefix = f"涪陵古本第 {yuanben} 条（{comparison_book}第 {comparison} 条）"
    elif yuanben:
        prefix = f"涪陵古本第 {yuanben} 条"
    elif comparison:
        prefix = f"{comparison_book}第 {comparison} 条"
    else:
        prefix = "Shang Han Za Bing Lun"
    if formula_number:
        return f"{prefix} - 方 {formula_number}: {name}"
    return f"{prefix} - {name}".rstrip(" -")


def format_pattern_context(pattern, pattern_key):
    return f"""Pattern: {pattern['name']['zh']} ({pattern['name']['en']})
Location: {pattern['location']}
Characteristics: {pattern['characteristics']}
Sub-patterns: {', '.join(pattern['sub_patterns'])}"""
