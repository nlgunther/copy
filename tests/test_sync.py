"""
Tests for sync_agent.

Covers: similarity, normalize, SegmentedODFHandler (parse + save),
ContentAwareSync (merge, sync_files, sync_directory), and SimpleMirrorSync
(_should_copy, sync_tree with exclude/shallow/keep/cutoff/dry-run/log).
"""
import datetime
import os
import re

import pytest
from odf import text, teletype
from odf.opendocument import OpenDocumentText

from sync_agent.content_engine import SegmentedODFHandler, normalize
from sync_agent.similarity import similarity
from sync_agent.sync_managers import ContentAwareSync, SimpleMirrorSync

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

D1 = datetime.date(2024, 1, 1)
D2 = datetime.date(2024, 6, 15)
D3 = datetime.date(2023, 12, 31)


def make_odt(path: str, entries: dict) -> None:
    """Write a minimal segmented .odt from {date: [segment, ...]}."""
    doc = OpenDocumentText()
    for dt, segments in sorted(entries.items(), reverse=True):
        tag = f"<{dt.month}/{dt.day}/{dt.year}>"
        for seg in segments:
            p = text.P()
            teletype.addTextToElement(p, f"{tag}{seg}")
            doc.text.addElement(p)
    doc.save(path)


def set_mtime(path: str, dt: datetime.datetime) -> None:
    ts = dt.timestamp()
    os.utime(path, (ts, ts))


# ---------------------------------------------------------------------------
# similarity
# ---------------------------------------------------------------------------

class TestSimilarity:
    def test_identical(self):
        assert similarity("hello world".split(), "hello world".split()) == pytest.approx(1.0)

    def test_partial_overlap(self):
        # 1 common token / sqrt(2)*sqrt(2) = 0.5
        assert similarity(["python", "math"], ["python", "law"]) == pytest.approx(0.5)

    def test_no_overlap(self):
        assert similarity(["hello"], ["world"]) == 0.0

    def test_empty_first_list(self):
        assert similarity([], ["hello"]) == 0.0

    def test_empty_second_list(self):
        assert similarity(["hello"], []) == 0.0

    def test_case_insensitive(self):
        assert similarity(["Hello"], ["hello"]) == pytest.approx(1.0)

    def test_deduplication(self):
        # Repeated tokens in one list should not boost the score.
        score_normal = similarity(["a", "b"], ["a", "c"])
        score_repeated = similarity(["a", "a", "b", "b"], ["a", "c"])
        assert score_normal == pytest.approx(score_repeated)


# ---------------------------------------------------------------------------
# normalize
# ---------------------------------------------------------------------------

class TestNormalize:
    def test_strips_date_tag(self):
        assert normalize("<1/1/2024>Hello, world!") == "hello world"

    def test_collapses_whitespace(self):
        assert normalize("  hello   world  ") == "hello world"

    def test_removes_punctuation(self):
        assert normalize("well-structured sentence.") == "well structured sentence"

    def test_lowercases(self):
        assert normalize("UPPER CASE") == "upper case"

    def test_empty_string(self):
        assert normalize("") == ""


# ---------------------------------------------------------------------------
# SegmentedODFHandler
# ---------------------------------------------------------------------------

class TestSegmentedODFHandler:
    def test_parse_roundtrip(self, tmp_path):
        h = SegmentedODFHandler()
        path = str(tmp_path / "test.odt")
        data = {D1: ["Entry one"], D2: ["Entry two", "Entry three"]}
        h.save(data, path)
        result = h.parse(path)
        assert set(result.keys()) == {D1, D2}
        assert result[D1] == ["Entry one"]
        assert set(result[D2]) == {"Entry two", "Entry three"}

    def test_parse_missing_file_returns_empty(self, tmp_path):
        h = SegmentedODFHandler()
        assert h.parse(str(tmp_path / "nope.odt")) == {}

    def test_save_skips_empty_segments(self, tmp_path):
        h = SegmentedODFHandler()
        path = str(tmp_path / "test.odt")
        h.save({D1: ["Valid entry", "", "   "]}, path)
        result = h.parse(path)
        assert result[D1] == ["Valid entry"]

    def test_parse_multiple_dates(self, tmp_path):
        h = SegmentedODFHandler()
        path = str(tmp_path / "multi.odt")
        data = {D1: ["A"], D2: ["B"], D3: ["C"]}
        h.save(data, path)
        result = h.parse(path)
        assert set(result.keys()) == {D1, D2, D3}

    def test_tag_regex_matches_slash_format(self):
        assert re.findall(SegmentedODFHandler.TAG_REGEX, "<12/25/2025>Content") == ["<12/25/2025>"]

    def test_tag_regex_no_false_positives(self):
        assert re.findall(SegmentedODFHandler.TAG_REGEX, "no tags here") == []


# ---------------------------------------------------------------------------
# ContentAwareSync.merge
# ---------------------------------------------------------------------------

class TestMerge:
    def test_target_only_date_added(self):
        s = ContentAwareSync()
        merged = s.merge({D1: ["A"]}, {D2: ["B"]})
        assert D1 in merged and D2 in merged

    def test_dissimilar_target_segment_appended(self):
        s = ContentAwareSync(threshold=0.95)
        src = {D1: ["The cat sat on the mat"]}
        tgt = {D1: ["A completely different story about rockets"]}
        merged = s.merge(src, tgt)
        assert len(merged[D1]) == 2

    def test_similar_target_segment_dropped(self):
        # Threshold 0.5: "hello world foo bar" vs "hello world foo baz" are
        # very similar (3/4 tokens shared) — tgt segment should be dropped.
        s = ContentAwareSync(threshold=0.5)
        src = {D1: ["hello world foo bar"]}
        tgt = {D1: ["hello world foo baz"]}
        merged = s.merge(src, tgt)
        assert len(merged[D1]) == 1

    def test_source_version_kept_on_conflict(self):
        # When src and tgt are similar, source wins.
        s = ContentAwareSync(threshold=0.5)
        merged = s.merge(
            {D1: ["source version of the story"]},
            {D1: ["target version of the story"]},
        )
        assert merged[D1][0] == "source version of the story"

    def test_empty_src_uses_tgt(self):
        s = ContentAwareSync()
        merged = s.merge({}, {D1: ["Only in target"]})
        assert merged[D1] == ["Only in target"]

    def test_empty_tgt_unchanged(self):
        s = ContentAwareSync()
        merged = s.merge({D1: ["Only in source"]}, {})
        assert merged[D1] == ["Only in source"]

    def test_multiple_new_tgt_segments_all_added(self):
        s = ContentAwareSync(threshold=0.95)
        src = {D1: ["Story A"]}
        tgt = {D1: ["Story B", "Story C"]}
        merged = s.merge(src, tgt)
        assert len(merged[D1]) == 3


# ---------------------------------------------------------------------------
# ContentAwareSync.sync_files
# ---------------------------------------------------------------------------

class TestSyncFiles:
    def test_writes_merged_to_target(self, tmp_path):
        h = SegmentedODFHandler()
        src = str(tmp_path / "src.odt")
        tgt = str(tmp_path / "tgt.odt")
        h.save({D1: ["Source entry"]}, src)
        h.save({D2: ["Target entry"]}, tgt)

        added = ContentAwareSync().sync_files(src, tgt)

        result = h.parse(tgt)
        assert D1 in result  # source date written to target
        assert D2 in result  # original target date preserved
        assert added == 1

    def test_returns_zero_when_no_new_segments(self, tmp_path):
        h = SegmentedODFHandler()
        src = str(tmp_path / "src.odt")
        tgt = str(tmp_path / "tgt.odt")
        h.save({D1: ["Identical entry"]}, src)
        h.save({D1: ["Identical entry"]}, tgt)

        added = ContentAwareSync().sync_files(src, tgt)
        assert added == 0

    def test_dry_run_does_not_write(self, tmp_path):
        h = SegmentedODFHandler()
        src = str(tmp_path / "src.odt")
        tgt = str(tmp_path / "tgt.odt")
        h.save({D1: ["Source only"]}, src)
        h.save({D2: ["Target only"]}, tgt)

        mtime_before = os.path.getmtime(tgt)
        ContentAwareSync(dry_run=True).sync_files(src, tgt)
        # File should not have been touched.
        assert os.path.getmtime(tgt) == mtime_before

    def test_target_created_from_source_when_missing(self, tmp_path):
        h = SegmentedODFHandler()
        src = str(tmp_path / "src.odt")
        tgt = str(tmp_path / "nonexistent.odt")
        h.save({D1: ["Entry"]}, src)

        # tgt doesn't exist — merge treats it as empty, saves src content
        ContentAwareSync().sync_files(src, tgt)
        result = h.parse(tgt)
        assert D1 in result


# ---------------------------------------------------------------------------
# ContentAwareSync.sync_directory
# ---------------------------------------------------------------------------

class TestSyncDirectory:
    def test_copies_unique_source_file(self, tmp_path):
        src = tmp_path / "src"; src.mkdir()
        tgt = tmp_path / "tgt"; tgt.mkdir()
        make_odt(str(src / "notes.odt"), {D1: ["Source only"]})

        ContentAwareSync().sync_directory(str(src), str(tgt))
        assert (tgt / "notes.odt").exists()

    def test_archives_target_before_merge(self, tmp_path):
        src = tmp_path / "src"; src.mkdir()
        tgt = tmp_path / "tgt"; tgt.mkdir()
        make_odt(str(src / "diary.odt"), {D1: ["Src entry"]})
        make_odt(str(tgt / "diary.odt"), {D2: ["Tgt entry"]})

        ContentAwareSync().sync_directory(str(src), str(tgt))

        legacy_files = list((tgt / "legacy").iterdir())
        assert len(legacy_files) == 1
        assert "diary" in legacy_files[0].name
        today = datetime.date.today().strftime("%Y_%m_%d")
        assert today in legacy_files[0].name

    def test_merged_file_contains_both_dates(self, tmp_path):
        src = tmp_path / "src"; src.mkdir()
        tgt = tmp_path / "tgt"; tgt.mkdir()
        make_odt(str(src / "diary.odt"), {D1: ["Src entry"]})
        make_odt(str(tgt / "diary.odt"), {D2: ["Tgt entry"]})

        ContentAwareSync().sync_directory(str(src), str(tgt))

        result = SegmentedODFHandler().parse(str(tgt / "diary.odt"))
        assert D1 in result
        assert D2 in result

    def test_excludes_numbered_odt_files(self, tmp_path):
        src = tmp_path / "src"; src.mkdir()
        tgt = tmp_path / "tgt"; tgt.mkdir()
        make_odt(str(src / "notes_2024_01_01.odt"), {D1: ["Dated copy"]})
        make_odt(str(src / "notes.odt"), {D1: ["Valid"]})

        ContentAwareSync().sync_directory(str(src), str(tgt))

        assert not (tgt / "notes_2024_01_01.odt").exists()
        assert (tgt / "notes.odt").exists()

    def test_excludes_copy_odt_files(self, tmp_path):
        src = tmp_path / "src"; src.mkdir()
        tgt = tmp_path / "tgt"; tgt.mkdir()
        make_odt(str(src / "notes_copy.odt"), {D1: ["Copy"]})
        make_odt(str(src / "notes.odt"), {D1: ["Original"]})

        ContentAwareSync().sync_directory(str(src), str(tgt))
        assert not (tgt / "notes_copy.odt").exists()

    def test_dry_run_copies_nothing(self, tmp_path):
        src = tmp_path / "src"; src.mkdir()
        tgt = tmp_path / "tgt"; tgt.mkdir()
        make_odt(str(src / "notes.odt"), {D1: ["Entry"]})

        ContentAwareSync(dry_run=True).sync_directory(str(src), str(tgt))
        assert not (tgt / "notes.odt").exists()

    def test_returns_changed_count(self, tmp_path):
        src = tmp_path / "src"; src.mkdir()
        tgt = tmp_path / "tgt"; tgt.mkdir()
        make_odt(str(src / "a.odt"), {D1: ["A"]})
        make_odt(str(src / "b.odt"), {D1: ["B"]})

        count = ContentAwareSync().sync_directory(str(src), str(tgt))
        assert count == 2


# ---------------------------------------------------------------------------
# SimpleMirrorSync._should_copy
# ---------------------------------------------------------------------------

class TestShouldCopy:
    def test_copies_when_target_missing(self, tmp_path):
        src = tmp_path / "a.txt"; src.write_text("x")
        assert SimpleMirrorSync()._should_copy(str(src), str(tmp_path / "b.txt"))

    def test_skips_eml_files(self, tmp_path):
        src = tmp_path / "a.eml"; src.write_text("email")
        assert not SimpleMirrorSync()._should_copy(str(src), str(tmp_path / "b.eml"))

    def test_skips_venv_paths(self, tmp_path):
        venv = tmp_path / "venv"; venv.mkdir()
        src = venv / "pyvenv.cfg"; src.write_text("cfg")
        assert not SimpleMirrorSync()._should_copy(str(src), str(tmp_path / "pyvenv.cfg"))

    def test_copies_when_source_newer(self, tmp_path):
        src = tmp_path / "src.txt"; src.write_text("new")
        tgt = tmp_path / "tgt.txt"; tgt.write_text("old")
        set_mtime(str(tgt), datetime.datetime.now() - datetime.timedelta(hours=1))
        assert SimpleMirrorSync()._should_copy(str(src), str(tgt))

    def test_skips_when_target_up_to_date(self, tmp_path):
        src = tmp_path / "src.txt"; src.write_text("old")
        tgt = tmp_path / "tgt.txt"; tgt.write_text("new")
        set_mtime(str(src), datetime.datetime.now() - datetime.timedelta(hours=1))
        assert not SimpleMirrorSync()._should_copy(str(src), str(tgt))

    def test_cutoff_skips_old_file(self, tmp_path):
        src = tmp_path / "old.txt"; src.write_text("ancient")
        set_mtime(str(src), datetime.datetime(2019, 6, 1))
        s = SimpleMirrorSync(cutoff=datetime.datetime(2020, 1, 1))
        assert not s._should_copy(str(src), str(tmp_path / "tgt.txt"))

    def test_cutoff_allows_recent_file(self, tmp_path):
        src = tmp_path / "new.txt"; src.write_text("recent")
        # mtime defaults to now, which is after any reasonable cutoff
        s = SimpleMirrorSync(cutoff=datetime.datetime(2020, 1, 1))
        assert s._should_copy(str(src), str(tmp_path / "tgt.txt"))

    def test_future_timestamp_skipped(self, tmp_path):
        src = tmp_path / "future.txt"; src.write_text("x")
        set_mtime(str(src), datetime.datetime.now() + datetime.timedelta(days=365))
        assert not SimpleMirrorSync()._should_copy(str(src), str(tmp_path / "tgt.txt"))


# ---------------------------------------------------------------------------
# SimpleMirrorSync.sync_tree
# ---------------------------------------------------------------------------

class TestSyncTree:
    def test_copies_file_to_target(self, tmp_path):
        src = tmp_path / "src"; src.mkdir()
        tgt = tmp_path / "tgt"; tgt.mkdir()
        (src / "file.txt").write_text("hello")

        SimpleMirrorSync().sync_tree(str(src), str(tgt))
        assert (tgt / "file.txt").read_text() == "hello"

    def test_preserves_subdirectory_structure(self, tmp_path):
        src = tmp_path / "src"; src.mkdir()
        tgt = tmp_path / "tgt"; tgt.mkdir()
        sub = src / "subdir"; sub.mkdir()
        (sub / "deep.txt").write_text("deep")

        SimpleMirrorSync().sync_tree(str(src), str(tgt))
        assert (tgt / "subdir" / "deep.txt").exists()

    def test_exclude_list_skips_directory(self, tmp_path):
        src = tmp_path / "src"; src.mkdir()
        tgt = tmp_path / "tgt"; tgt.mkdir()
        skip = src / "skip_me"; skip.mkdir()
        (skip / "file.txt").write_text("should not copy")

        SimpleMirrorSync(exclude_list=["skip_me"]).sync_tree(str(src), str(tgt))
        assert not (tgt / "skip_me").exists()

    def test_shallow_list_copies_top_level_only(self, tmp_path):
        src = tmp_path / "src"; src.mkdir()
        tgt = tmp_path / "tgt"; tgt.mkdir()
        dl = src / "Downloads"; dl.mkdir()
        (dl / "top.txt").write_text("top")
        deep = dl / "subdir"; deep.mkdir()
        (deep / "deep.txt").write_text("deep")

        SimpleMirrorSync(shallow_list=["Downloads"]).sync_tree(str(src), str(tgt))
        assert (tgt / "Downloads" / "top.txt").exists()
        assert not (tgt / "Downloads" / "subdir").exists()

    def test_keep_list_exempts_from_shallow(self, tmp_path):
        src = tmp_path / "src"; src.mkdir()
        tgt = tmp_path / "tgt"; tgt.mkdir()
        kindle = src / "Kindle"; kindle.mkdir()
        (kindle / "top.txt").write_text("top")
        deep = kindle / "books"; deep.mkdir()
        (deep / "book.azw").write_text("book")

        # Kindle is in both shallow and keep — keep wins, full recursion.
        SimpleMirrorSync(shallow_list=["Kindle"], keep_list=["Kindle"]).sync_tree(
            str(src), str(tgt)
        )
        assert (tgt / "Kindle" / "books" / "book.azw").exists()

    def test_dry_run_writes_nothing(self, tmp_path):
        src = tmp_path / "src"; src.mkdir()
        tgt = tmp_path / "tgt"; tgt.mkdir()
        (src / "file.txt").write_text("content")

        SimpleMirrorSync(dry_run=True).sync_tree(str(src), str(tgt))
        assert not (tgt / "file.txt").exists()

    def test_writes_copied_log(self, tmp_path):
        src = tmp_path / "src"; src.mkdir()
        tgt = tmp_path / "tgt"; tgt.mkdir()
        (src / "file.txt").write_text("content")

        SimpleMirrorSync().sync_tree(str(src), str(tgt))
        today = datetime.date.today().strftime("%Y_%m_%d")
        assert (tgt / f"copied_{today}.txt").exists()

    def test_no_log_when_nothing_copied(self, tmp_path):
        src = tmp_path / "src"; src.mkdir()
        tgt = tmp_path / "tgt"; tgt.mkdir()
        # src is empty — nothing to copy
        copied, problems = SimpleMirrorSync().sync_tree(str(src), str(tgt))
        today = datetime.date.today().strftime("%Y_%m_%d")
        assert not (tgt / f"copied_{today}.txt").exists()
        assert copied == []

    def test_returns_copied_list(self, tmp_path):
        src = tmp_path / "src"; src.mkdir()
        tgt = tmp_path / "tgt"; tgt.mkdir()
        (src / "a.txt").write_text("a")
        (src / "b.txt").write_text("b")

        copied, problems = SimpleMirrorSync().sync_tree(str(src), str(tgt))
        assert len(copied) == 2
        assert all("source:" in e and "target:" in e for e in copied)
        assert problems == []

    def test_skips_eml_in_tree(self, tmp_path):
        src = tmp_path / "src"; src.mkdir()
        tgt = tmp_path / "tgt"; tgt.mkdir()
        (src / "letter.eml").write_text("mail")
        (src / "doc.txt").write_text("doc")

        SimpleMirrorSync().sync_tree(str(src), str(tgt))
        assert not (tgt / "letter.eml").exists()
        assert (tgt / "doc.txt").exists()
