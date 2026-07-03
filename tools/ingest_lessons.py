#!/usr/bin/env python3
"""Ingest .docx lesson files into .txt, .json, and/or the SQLite database.

Usage:
    python tools/ingest_lessons.py                     # Preview only
    python tools/ingest_lessons.py --txt               # Export to .txt
    python tools/ingest_lessons.py --json              # Export to .json
    python tools/ingest_lessons.py --db                # Load into database
    python tools/ingest_lessons.py --all               # Do all of the above
    python tools/ingest_lessons.py --clear-db          # Clear existing lessons
"""

import argparse
import json
import os
import re
import sys

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(TOOLS_DIR)
SRC_DIR = os.path.join(ROOT_DIR, 'src')
sys.path.insert(0, SRC_DIR)

try:
    from docx import Document
except ImportError:
    print("python-docx not installed. Run: pip install python-docx")
    sys.exit(1)


LESSONS_DIR = os.path.join(ROOT_DIR, 'lessons')
OUTPUT_DIR = os.path.join(SRC_DIR, 'data', 'lessons')


def discover_files():
    files = []
    for root, _dirs, fnames in os.walk(LESSONS_DIR):
        for f in fnames:
            if not f.endswith('.docx') or f.startswith('~$'):
                continue
            path = os.path.join(root, f)
            rel = os.path.relpath(path, LESSONS_DIR)
            parts = rel.split(os.sep)
            subcategory = parts[0]   # original / labeled
            category = parts[1]      # lectures / summaries / additional
            lesson_id = os.path.splitext(parts[-1])[0]
            files.append((path, lesson_id, category, subcategory))
    files.sort(key=lambda x: (x[3], x[2], x[1]))
    return files


def clean_lesson_id(lesson_id):
    """Normalize lesson_id: lesson1_lecturebyDrMa_1to9 -> lesson001"""
    m = re.match(r'.*?(lesson\d+)', lesson_id, re.IGNORECASE)
    if m:
        num = re.sub(r'\D', '', m.group(1))
        return f"lesson{int(num):04d}"
    return lesson_id


def extract_text(docx_path):
    doc = Document(docx_path)
    paras = []
    for p in doc.paragraphs:
        text = p.text.strip()
        if text:
            paras.append(text)
    return '\n'.join(paras)


def make_title(lesson_id, category, subcategory):
    label = "Labeled" if subcategory == "labeled" else "Original"
    return f"[{label}] [{category.capitalize()}] {lesson_id}"


def export_txt(text, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


def export_json(entries, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Ingest .docx lesson files")
    parser.add_argument('--txt', action='store_true', help='Export to .txt')
    parser.add_argument('--json', action='store_true', help='Export to .json')
    parser.add_argument('--db', action='store_true', help='Load into database')
    parser.add_argument('--all', action='store_true', help='Do --txt --json --db')
    parser.add_argument('--clear-db', action='store_true', help='Clear existing lessons from DB before loading')
    args = parser.parse_args()

    if not any([args.txt, args.json, args.db, args.all]):
        args.all = True

    if args.all:
        args.txt = args.json = args.db = True

    if args.db:
        import database as db
        db.init_db()
        if args.clear_db:
            db.clear_lessons()
            print("Lessons table cleared\n")

    files = discover_files()
    print(f"Found {len(files)} .docx files\n")

    entries = []
    db_module = None
    if args.db:
        import database as db_module

    for path, lesson_id, category, subcategory in files:
        text = extract_text(path)
        normalized_id = clean_lesson_id(lesson_id)
        title = make_title(normalized_id, category, subcategory)
        rel_path = os.path.relpath(path, ROOT_DIR)
        wc = len(text.split())

        entry = {
            "lesson_id": normalized_id,
            "title": title,
            "category": category,
            "subcategory": subcategory,
            "source_path": rel_path,
            "content": text,
            "word_count": wc
        }
        entries.append(entry)

        print(f"  {normalized_id:14s}  {category:12s}  {subcategory:10s}  {wc:5d} words  {os.path.basename(path)}")

        if args.txt:
            txt_dir = os.path.join(OUTPUT_DIR, subcategory, category)
            txt_name = f"{normalized_id}.txt"
            export_txt(text, os.path.join(txt_dir, txt_name))

        if db_module:
            db_module.save_lesson(normalized_id, title, category, subcategory, rel_path, text)

    if args.json:
        json_path = os.path.join(OUTPUT_DIR, 'lessons.json')
        export_json(entries, json_path)
        print(f"\nJSON: {json_path}  ({len(entries)} entries)")

    if args.txt:
        print(f"\nTXT: {OUTPUT_DIR}/{{labeled,original}}/{{lectures,summaries,additional}}/")

    if db_module:
        print(f"\nDB:  {db_module.lesson_count()} lessons loaded into {db_module.DB_PATH}")

    print("\nDone.")


if __name__ == '__main__':
    main()
