import re
import os
import datetime
import pytest
from sync_agent.similarity import SimilarityEngine
from sync_agent.content_engine import SegmentedODFHandler
from sync_agent.sync_managers import ContentAwareSync, SimpleMirrorSync


def test_similarity_math():
    engine = SimilarityEngine()
    assert engine.similarity(["python", "math"], ["python", "law"]) == pytest.approx(0.5)


def test_tag_extraction():
    handler = SegmentedODFHandler()
    sample = "<12/25/2025>Family trip to Madrid."
    tags = re.findall(handler.TAG_REGEX, sample)
    assert len(tags) == 1
    assert tags[0] == "<12/25/2025>"


# --- startdate: ContentAwareSync ---

def test_content_startdate_skips_old_file(tmp_path):
    src = tmp_path / "old.odt"
    src.touch()
    tgt = tmp_path / "tgt.odt"
    old_mtime = datetime.datetime(2019, 6, 1).timestamp()
    os.utime(src, (old_mtime, old_mtime))
    syncer = ContentAwareSync(startdate=datetime.datetime(2020, 1, 1))
    result = syncer.sync(str(src), str(tgt))
    assert result == 0
    assert not tgt.exists()


def test_content_startdate_allows_new_file(tmp_path):
    src = tmp_path / "new.odt"
    src.touch()
    tgt = tmp_path / "tgt.odt"
    new_mtime = datetime.datetime(2021, 3, 15).timestamp()
    os.utime(src, (new_mtime, new_mtime))
    syncer = ContentAwareSync(startdate=datetime.datetime(2020, 1, 1))
    result = syncer.sync(str(src), str(tgt))
    assert result == 0  # no ODF content, but not blocked by startdate


def test_content_no_startdate_always_runs(tmp_path):
    src = tmp_path / "any.odt"
    src.touch()
    tgt = tmp_path / "tgt.odt"
    old_mtime = datetime.datetime(2015, 1, 1).timestamp()
    os.utime(src, (old_mtime, old_mtime))
    syncer = ContentAwareSync()
    result = syncer.sync(str(src), str(tgt))
    assert result == 0  # no ODF content, but not blocked


# --- startdate: SimpleMirrorSync ---

def test_mirror_startdate_skips_old_file(tmp_path):
    src_dir = tmp_path / "src"
    tgt_dir = tmp_path / "tgt"
    src_dir.mkdir()
    tgt_dir.mkdir()
    f = src_dir / "old.txt"
    f.write_text("hello")
    old_mtime = datetime.datetime(2018, 5, 1).timestamp()
    os.utime(f, (old_mtime, old_mtime))
    syncer = SimpleMirrorSync(startdate=datetime.datetime(2020, 1, 1))
    syncer.sync_tree(str(src_dir), str(tgt_dir))
    assert not (tgt_dir / "old.txt").exists()


def test_mirror_startdate_copies_new_file(tmp_path):
    src_dir = tmp_path / "src"
    tgt_dir = tmp_path / "tgt"
    src_dir.mkdir()
    tgt_dir.mkdir()
    f = src_dir / "new.txt"
    f.write_text("hello")
    new_mtime = datetime.datetime(2022, 8, 10).timestamp()
    os.utime(f, (new_mtime, new_mtime))
    syncer = SimpleMirrorSync(startdate=datetime.datetime(2020, 1, 1))
    syncer.sync_tree(str(src_dir), str(tgt_dir))
    assert (tgt_dir / "new.txt").exists()


def test_mirror_no_startdate_copies_old_file(tmp_path):
    src_dir = tmp_path / "src"
    tgt_dir = tmp_path / "tgt"
    src_dir.mkdir()
    tgt_dir.mkdir()
    f = src_dir / "old.txt"
    f.write_text("hello")
    old_mtime = datetime.datetime(2010, 1, 1).timestamp()
    os.utime(f, (old_mtime, old_mtime))
    syncer = SimpleMirrorSync()
    syncer.sync_tree(str(src_dir), str(tgt_dir))
    assert (tgt_dir / "old.txt").exists()


# --- 30-second mtime gap: SimpleMirrorSync ---

def test_mirror_skips_when_timestamps_nearly_equal(tmp_path):
    src_dir = tmp_path / "src"
    tgt_dir = tmp_path / "tgt"
    src_dir.mkdir()
    tgt_dir.mkdir()
    src_f = src_dir / "file.txt"
    tgt_f = tgt_dir / "file.txt"
    src_f.write_text("v1")
    tgt_f.write_text("v1")
    base = datetime.datetime(2023, 1, 1).timestamp()
    os.utime(src_f, (base + 10, base + 10))
    os.utime(tgt_f, (base, base))
    syncer = SimpleMirrorSync()
    syncer.sync_tree(str(src_dir), str(tgt_dir))
    assert tgt_f.read_text() == "v1"


def test_mirror_copies_when_source_clearly_newer(tmp_path):
    src_dir = tmp_path / "src"
    tgt_dir = tmp_path / "tgt"
    src_dir.mkdir()
    tgt_dir.mkdir()
    src_f = src_dir / "file.txt"
    tgt_f = tgt_dir / "file.txt"
    src_f.write_text("v2")
    tgt_f.write_text("v1")
    base = datetime.datetime(2023, 1, 1).timestamp()
    os.utime(src_f, (base + 60, base + 60))
    os.utime(tgt_f, (base, base))
    syncer = SimpleMirrorSync()
    syncer.sync_tree(str(src_dir), str(tgt_dir))
    assert tgt_f.read_text() == "v2"
