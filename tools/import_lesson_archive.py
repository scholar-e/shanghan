#!/usr/bin/env python3
"""Safely import missing original lecture DOCX files from a Drive ZIP."""

import argparse
import io
import logging
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath

from docx import Document

ROOT_DIR = Path(__file__).resolve().parent.parent
DESTINATION = ROOT_DIR / "lessons" / "original" / "lectures"
logger = logging.getLogger(__name__)


def lesson_number(filename, data, duplicate_filename_numbers):
    match = re.search(r"lesson\s*(\d+)", filename, re.I)
    if not match:
        raise ValueError(f"No lesson number in {filename}")
    number = int(match[1])
    if number not in duplicate_filename_numbers:
        return number

    # The supplied archive has two files named lesson 25. One is the regular
    # lesson 25; the other explicitly identifies itself as 第九十四课 and is the
    # otherwise missing final Yiji lecture.
    text = "\n".join(p.text.strip() for p in Document(io.BytesIO(data)).paragraphs[:12] if p.text.strip())
    if "第九十四课" in text and "宜忌" in text:
        return 94
    return number


def plan_import(archive, destination=DESTINATION):
    destination = Path(destination)
    existing = {}
    for path in destination.glob("*.docx"):
        match = re.search(r"lesson\s*(\d+)", path.name, re.I)
        if match:
            existing[int(match[1])] = path

    with zipfile.ZipFile(archive) as bundle:
        members = [info for info in bundle.infolist() if info.filename.lower().endswith(".docx")]
        filename_numbers = [int(re.search(r"lesson\s*(\d+)", info.filename, re.I)[1]) for info in members]
        duplicates = {number for number in filename_numbers if filename_numbers.count(number) > 1}
        planned = []
        seen = set()
        for info in members:
            if info.is_dir() or len(PurePosixPath(info.filename).parts) != 1:
                raise ValueError(f"Unsafe or nested archive member: {info.filename}")
            data = bundle.read(info)
            number = lesson_number(info.filename, data, duplicates)
            if number in seen:
                raise ValueError(f"Duplicate resolved lesson identity: {number}")
            seen.add(number)
            if number in existing:
                logger.info("Keeping existing lesson %d: %s", number, existing[number].name)
                continue
            output_name = info.filename
            if number == 94:
                output_name = re.sub(r"lesson\s*25", "lesson94", output_name, count=1, flags=re.I)
            planned.append((number, info.filename, output_name, data))
    return sorted(planned)


def import_archive(archive, destination=DESTINATION):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    planned = plan_import(archive, destination)
    for number, source_name, output_name, data in planned:
        target = destination / output_name
        if target.exists():
            raise FileExistsError(target)
        target.write_bytes(data)
        logger.info("Imported lesson %d: %s -> %s", number, source_name, target)
    return planned


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--destination", type=Path, default=DESTINATION)
    parser.add_argument("--apply", action="store_true", help="Write planned DOCX files")
    args = parser.parse_args()
    log_dir = ROOT_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(filename)s:%(lineno)d %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(log_dir / "import_lessons.log")])
    planned = import_archive(args.archive, args.destination) if args.apply else plan_import(args.archive, args.destination)
    logger.info("%s %d missing lectures: %s", "Imported" if args.apply else "Found", len(planned),
                ", ".join(str(item[0]) for item in planned))


if __name__ == "__main__":
    main()
