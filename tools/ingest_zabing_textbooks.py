#!/usr/bin/env python3
"""Extract Zabing textbook .docx files into normalized text and SQLite rows."""

import argparse
import os
import re
import sys

from docx import Document

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(TOOLS_DIR)
SRC_DIR = os.path.join(ROOT_DIR, "src")
sys.path.insert(0, SRC_DIR)

DEFAULT_DOCX = [
    os.path.join(ROOT_DIR, "textbook2ndpart_Reedited_Zabing_toCh25.docx"),
    os.path.join(ROOT_DIR, "textbook3rdpart_Reedited_Zabing_toCh40End.docx"),
]
OUT_TXT = os.path.join(ROOT_DIR, "textbook_zabing.txt")


def _paragraphs(path):
    doc = Document(path)
    return [re.sub(r"\s+", " ", p.text).strip() for p in doc.paragraphs if p.text.strip()]


def _is_chapter(line):
    return bool(re.match(r"^辨.+篇第[一二三四五六七八九十百千万]+$", line))


def _is_entry_start(line):
    return bool(re.match(r"^涪陵古本\s*\d{1,2}\.\d{1,3}\.\s*【原文】", line))


def _is_formula_start(line):
    return bool(re.match(r"^\{\s*\d+\s*\}\s*.+", line))


def _clean(line):
    return re.sub(r"\s+", " ", line or "").strip()


def parse_docx(path):
    paras = _paragraphs(path)
    entries = []
    formulas = []
    items = []
    chapter_title = ""
    order = 0
    i = 0
    while i < len(paras):
        line = paras[i]
        if _is_chapter(line):
            chapter_title = line
            i += 1
            continue

        entry_match = re.match(r"^涪陵古本\s*(\d{1,2}\.\d{1,3})\.\s*【原文】", line)
        if entry_match:
            fuling_ref = entry_match.group(1)
            i += 1
            fuling_parts = []
            while i < len(paras) and not paras[i].startswith("（金匮"):
                if _is_entry_start(paras[i]) or _is_chapter(paras[i]):
                    break
                fuling_parts.append(paras[i])
                i += 1

            comparison_ref = None
            comparison_text = None
            if i < len(paras) and paras[i].startswith("（金匮"):
                jin_match = re.match(r"^（金匮\s*([\d.]+)?）\s*(.*)$", paras[i])
                if jin_match:
                    comparison_ref = (jin_match.group(1) or "").strip() or None
                    comparison_parts = [jin_match.group(2).strip()]
                else:
                    comparison_parts = [paras[i]]
                i += 1
                while i < len(paras):
                    next_line = paras[i]
                    if _is_entry_start(next_line) or _is_chapter(next_line) or _is_formula_start(next_line):
                        break
                    if next_line.startswith("（金匮"):
                        break
                    comparison_parts.append(next_line)
                    i += 1
                comparison_text = _clean(" ".join(part for part in comparison_parts if part))

            entry = {
                "entry_key": f"zabing_{fuling_ref}",
                "fuling_ref": fuling_ref,
                "fuling_zh": _clean(" ".join(fuling_parts)),
                "comparison_ref": comparison_ref,
                "comparison_zh": comparison_text,
                "comparison_book": "金匮",
                "chapter_title": chapter_title,
                "source_path": os.path.basename(path),
                "order": order,
            }
            entries.append(entry)
            items.append(("entry", entry))
            order += 1
            continue

        formula_match = re.match(r"^\{\s*(\d+)\s*\}\s*(.+)$", line)
        if formula_match:
            number = formula_match.group(1)
            title = formula_match.group(2).strip()
            i += 1
            block = []
            while i < len(paras):
                next_line = paras[i]
                if _is_entry_start(next_line) or _is_chapter(next_line) or _is_formula_start(next_line):
                    break
                block.append(next_line)
                i += 1
            formula = {
                "number": number,
                "title": title,
                "lines": block,
                "chapter_title": chapter_title,
                "source_path": os.path.basename(path),
                "order": order,
            }
            formulas.append(formula)
            items.append(("formula", formula))
            order += 1
            continue

        i += 1
    return entries, formulas, items


def write_normalized_text(items, path=OUT_TXT):
    lines = []
    current_chapter = None
    for kind, item in items:
        chapter = item.get("chapter_title") or ""
        if chapter and chapter != current_chapter:
            lines.extend(["", chapter])
            current_chapter = chapter
        if kind == "entry":
            lines.append(f"涪陵古本 {item['fuling_ref']}: {item['fuling_zh']}")
            if item.get("comparison_ref"):
                lines.append(f"（金匮 {item['comparison_ref']}）{item.get('comparison_zh') or ''}")
            else:
                lines.append("（金匮）无此条。")
        else:
            lines.append(f"FORMULA 方 {{ {item['number']} }} {item['title']}")
            lines.extend(item["lines"])

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(line for line in lines if line is not None).strip() + "\n")


def main():
    parser = argparse.ArgumentParser(description="Ingest Zabing .docx textbook files")
    parser.add_argument("docx", nargs="*", default=DEFAULT_DOCX)
    parser.add_argument("--txt", action="store_true", help="Write normalized textbook_zabing.txt")
    parser.add_argument("--db", action="store_true", help="Load entries into SQLite")
    parser.add_argument("--clear", action="store_true", help="Clear Zabing rows before DB load")
    args = parser.parse_args()

    entries = []
    formulas = []
    items = []
    for path in args.docx:
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        parsed_entries, parsed_formulas, parsed_items = parse_docx(path)
        entries.extend(parsed_entries)
        formulas.extend(parsed_formulas)
        items.extend(parsed_items)
        print(f"{os.path.basename(path)}: {len(parsed_entries)} entries, {len(parsed_formulas)} formulas")

    if args.txt or not args.db:
        write_normalized_text(items)
        print(f"TXT: {OUT_TXT}")

    if args.db:
        import database as db
        db.init_db()
        if args.clear:
            db.clear_zabing_articles()
        for entry in entries:
            db.save_zabing_article(
                entry["entry_key"],
                entry["fuling_ref"],
                entry["fuling_zh"],
                entry["comparison_ref"],
                entry["comparison_zh"],
                entry["comparison_book"],
                entry["chapter_title"],
                entry["source_path"],
            )
        print(f"DB: {db.zabing_article_count()} Zabing entries loaded into {db.DB_PATH}")

    print(f"Total: {len(entries)} entries, {len(formulas)} formulas")


if __name__ == "__main__":
    main()
