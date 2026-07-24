#!/usr/bin/env python3
"""Parse textbook.txt to extract Fuling (涪陵古本) articles with Song (宋本) equivalents.

Usage:
    python tools/ingest_fuling_articles.py --db       # Load into database
    python tools/ingest_fuling_articles.py --json     # Export to JSON
    python tools/ingest_fuling_articles.py --db --clear  # Clear and reload
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

TEXTBOOK_CANDIDATES = [
    os.path.join(ROOT_DIR, 'textbook.txt'),
    os.path.join(os.path.dirname(ROOT_DIR), 'textbook.txt'),
]


def resolve_textbook_path(path=None):
    if path:
        resolved = os.path.abspath(path)
        if os.path.isfile(resolved):
            return resolved
        raise FileNotFoundError(f"textbook.txt not found at {resolved}")

    for candidate in TEXTBOOK_CANDIDATES:
        if os.path.isfile(candidate):
            return candidate

    searched = ", ".join(TEXTBOOK_CANDIDATES)
    raise FileNotFoundError(f"textbook.txt not found. Searched: {searched}")

# Song article channel mapping (from ingest_shl_articles.py)
SONG_CHANNEL_MAP = {}
_ARTICLE_CHANNELS = [
    (1, 30, "tai_yang"), (31, 127, "tai_yang"),
    (128, 178, "yang_ming"), (179, 262, "shao_yang"),
    (263, 272, "shao_yang"), (273, 312, "tai_yin"),
    (313, 357, "shao_yin"), (358, 381, "jue_yin"),
    (382, 391, "huo_luan"),
]
for start, end, ch in _ARTICLE_CHANNELS:
    for n in range(start, end + 1):
        SONG_CHANNEL_MAP[n] = ch


def parse_textbook(textbook_path):
    """Parse textbook.txt and return list of Fuling article dicts."""
    with open(textbook_path, 'r', encoding='utf-8') as f:
        text = f.read()

    entries = []
    # Pattern: a LINE 原文 marker, then 涪陵古本 line, then optional 宋本 line
    # Handle multi-line fuling text (some span multiple lines before 宋本)
    
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        # Look for 涪陵古本 N:. The newest textbook starts line 1 as
        # a bare "1:" before switching to explicit 涪陵古本 labels.
        m = re.match(r'\s*(?:涪陵古本\s*)?(\d+)\s*:\s*(.*)', line)
        if m:
            fuling_num = int(m.group(1))
            fuling_text = m.group(2).strip()
            
            # Check for continued Fuling text on next lines (before 宋本 line)
            j = i + 1
            song_article_num = None
            song_text = None
            
            while j < len(lines):
                next_line = lines[j].strip()
                # Check if this is a 宋本 line
                sm = re.match(r'[（(]\s*宋本\s*(\d+|)\s*[）)]\s*(.*)', next_line)
                if sm:
                    song_ref = sm.group(1).strip()
                    song_text = sm.group(2).strip()
                    if song_ref and song_ref != '0':
                        song_article_num = int(song_ref)
                        # If song text is empty or just punctuation, mark as "无此条"
                        if not song_text or song_text in ('。', '）', '）'):
                            song_text = None
                    else:
                        song_text = None  # "无此条"
                    break
                # If we hit another 涪陵古本 or FORMULA or commentary marker, stop
                elif re.match(r'\s*(?:涪陵古本\s*)?\d+\s*:', next_line) or next_line.startswith('FORMULA') or next_line.startswith('【COMMENTARY'):
                    break
                else:
                    # It could be continuation of Fuling text
                    if next_line and not next_line.startswith('•') and not next_line.startswith('	•'):
                        fuling_text += ' ' + next_line
                j += 1
            
            fuling_text = re.sub(r'\s+', ' ', fuling_text).strip()
            
            # Determine channel
            channel = ''
            if song_article_num and song_article_num in SONG_CHANNEL_MAP:
                channel = SONG_CHANNEL_MAP[song_article_num]
            
            entries.append({
                'fuling_article_num': fuling_num,
                'fuling_zh': fuling_text,
                'song_article_num': song_article_num,
                'song_zh': song_text,
                'channel': channel,
            })
            
            i = j
        else:
            i += 1

    return entries


def export_json(entries, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Ingest Fuling articles from textbook.txt")
    parser.add_argument('--db', action='store_true', help='Load into database')
    parser.add_argument('--json', action='store_true', help='Export to JSON')
    parser.add_argument('--clear', action='store_true', help='Clear existing Fuling articles from DB before loading')
    parser.add_argument('--stats', action='store_true', help='Show parsing statistics')
    parser.add_argument('--textbook', help='Path to textbook.txt')
    args = parser.parse_args()

    if not any([args.db, args.json, args.stats]):
        args.stats = True
        args.json = True

    textbook_path = resolve_textbook_path(args.textbook)
    print(f"Parsing {textbook_path}...")
    entries = parse_textbook(textbook_path)
    print(f"Found {len(entries)} Fuling articles\n")

    # Stats
    with_song = sum(1 for e in entries if e['song_article_num'])
    without_song = sum(1 for e in entries if not e['song_article_num'])
    with_channel = sum(1 for e in entries if e['channel'])
    
    if args.stats:
        print(f"  With Song equivalent: {with_song}")
        print(f"  Without Song equivalent: {without_song}")
        print(f"  With channel: {with_channel}")
        print()

    if args.json:
        out_dir = os.path.join(SRC_DIR, 'data')
        json_path = os.path.join(out_dir, 'fuling_articles.json')
        export_json(entries, json_path)
        print(f"JSON: {json_path}")

    if args.db:
        import database as db
        db.init_db()
        if args.clear:
            db.clear_fuling_articles()
            print("Fuling articles table cleared")

        for e in entries:
            db.save_fuling_article(
                e['fuling_article_num'],
                e['fuling_zh'],
                e['song_article_num'],
                e['song_zh'],
                e['channel'],
            )
        print(f"DB:  {db.fuling_article_count()} Fuling articles loaded into {db.DB_PATH}")

    # Sample output
    print("\nSample entries:")
    for e in entries[:3]:
        print(f"  涪陵古本 {e['fuling_article_num']}: {e['fuling_zh'][:60]}...")
        if e['song_article_num']:
            print(f"    → 宋本 {e['song_article_num']}: {e['song_zh'][:60] if e['song_zh'] else '(none)'}")
        else:
            print(f"    → 宋本: 无此条")
    print()

    print("Done.")


if __name__ == '__main__':
    main()
