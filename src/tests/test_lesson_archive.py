"""Safe archive import and idempotent lesson indexing tests."""

import io
import sys
import zipfile
from pathlib import Path

import pytest
from docx import Document

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import database as db
import retrieval
from tools import import_lesson_archive as importer


def docx_bytes(lines):
    document = Document()
    for line in lines:
        document.add_paragraph(line)
    stream = io.BytesIO()
    document.save(stream)
    return stream.getvalue()


def make_archive(path, members):
    with zipfile.ZipFile(path, "w") as bundle:
        for name, data in members:
            bundle.writestr(name, data)


def test_archive_inventory_imports_missing_and_resolves_lesson_94(tmp_path):
    destination = tmp_path / "lessons"
    destination.mkdir()
    (destination / "lesson2_existing.docx").write_bytes(docx_bytes(["existing"]))
    archive = tmp_path / "drive.zip"
    make_archive(archive, [
        ("lesson2_download.docx", docx_bytes(["replacement"])),
        ("lesson25_regular.docx", docx_bytes(["第二十五讲", "regular"])),
        ("lesson25_宜忌忌水.docx", docx_bytes(["第九十四课", "宜忌篇，忌水第十四 宜水第十五"])),
    ])
    plan = importer.plan_import(archive, destination)
    assert [(number, output) for number, _source, output, _data in plan] == [
        (25, "lesson25_regular.docx"), (94, "lesson94_宜忌忌水.docx")]
    importer.import_archive(archive, destination)
    assert (destination / "lesson2_existing.docx").read_bytes() == docx_bytes(["existing"])
    assert (destination / "lesson94_宜忌忌水.docx").exists()


def test_archive_rejects_nested_and_duplicate_resolved_members(tmp_path):
    nested = tmp_path / "nested.zip"
    make_archive(nested, [("folder/lesson20.docx", docx_bytes(["lesson"]))])
    with pytest.raises(ValueError, match="nested"):
        importer.plan_import(nested, tmp_path / "out")
    duplicate = tmp_path / "duplicate.zip"
    make_archive(duplicate, [("lesson20_a.docx", docx_bytes(["a"])), ("lesson20_b.docx", docx_bytes(["b"]))])
    with pytest.raises(ValueError, match="Duplicate resolved"):
        importer.plan_import(duplicate, tmp_path / "out")


def test_lesson_save_is_idempotent_and_preserves_versions(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_connection", None)
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "lessons.db"))
    db.init_db()
    db.save_lesson("lesson0025", "Original", "lectures", "original", "first.docx", "old")
    db.save_lesson("lesson0025", "Original", "lectures", "original", "second.docx", "new")
    db.save_lesson("lesson0025", "Labeled", "lectures", "labeled", "labeled.docx", "labeled")
    rows = db.get_connection().execute("SELECT subcategory, source_path, content FROM lessons ORDER BY subcategory").fetchall()
    assert [tuple(row) for row in rows] == [
        ("labeled", "labeled.docx", "labeled"),
        ("original", "second.docx", "new"),
    ]
    exact = retrieval.search_lectures("lecture 25")
    assert len(exact) == 1 and exact[0]["content"] == "new"
    db.close_db()
