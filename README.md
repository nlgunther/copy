# sync-agent

A command-line tool for two tasks:

1. **Content-aware merge** of segmented `.odt` journal/notes files — finds entries unique to each copy and combines them without creating duplicates.
2. **Mirror sync** of a directory tree — copies files that are newer in the source, with fine-grained control over which directories to recurse into.

---

## Background and file format

The content sync was designed for `.odt` files that use inline date tags as section headers:

```
<1/15/2024>Went to the farmer's market.
<1/15/2024>Finished reading the novel.
<1/16/2024>Rainy day. Stayed in and coded.
```

Each paragraph begins with a `<M/D/YYYY>` tag. Multiple paragraphs may share the same date. `sync-agent content` reads both copies of a file, finds entries unique to each, and writes a merged file to the target path — archiving the original target first.

---

## Installation

```bash
pip install -e .           # development install from the repo root
pip install sync-agent     # once published to PyPI
```

**Dependencies:** `odfpy`, `python-dateutil`, `loguru`, `pywin32` (Windows only).

---

## Usage

### `content` — merge segmented .odt files

```bash
# Merge two directories of .odt files
sync-agent content ~/notes/ D:/backup/notes/

# Merge a single file pair
sync-agent content diary.odt D:/backup/diary.odt

# Preview changes without writing anything
sync-agent content diary.odt D:/backup/diary.odt --dry-run

# Lower the dedup threshold (more aggressively merge similar-sounding entries)
sync-agent content diary.odt D:/backup/diary.odt --threshold 0.85
```

**Directory mode:** When `src` is a directory, every `.odt` file in `src` that has a counterpart in `tgt` is merged. Files present only in `src` are copied directly. Numbered and "copy" files (e.g. `diary_2024_01_01.odt`, `notes_copy.odt`) are excluded from discovery to avoid re-processing already-archived files.

Before overwriting any target file, the original is moved to `tgt/legacy/<stem>_YYYY_MM_DD.odt`. This means a failed or unwanted merge can always be rolled back by hand.

**Merge semantics:** Source is authoritative. When source and target have similar entries for the same date, the source version is kept. Target entries that are genuinely new (cosine similarity below `--threshold` against every source entry for that date) are appended. The merged result is saved to the target path.

**Single-file mode:** When `src` is a file path, `sync_files` merges directly into `tgt`. No legacy archive is created in this mode — use directory mode if you want archiving.

### `mirror` — copy newer files between directory trees

```bash
# Basic mirror
sync-agent mirror ~/Documents D:/Documents

# Skip venv directories and copy only the top level of Downloads
sync-agent mirror ~/Documents D:/Documents \
    --exclude venv .git \
    --shallow Downloads .ipynb_checkpoints NLGMassFiles

# Allow full recursion into Kindle even though Downloads is shallow
sync-agent mirror ~/Documents D:/Documents \
    --shallow Downloads \
    --keep Kindle

# Only copy files modified since 2020
sync-agent mirror ~/Documents D:/Documents --cutoff 2020-01-01

# Preview without writing
sync-agent mirror ~/Documents D:/Documents --dry-run
```

**A file is copied when:**
- It does not exist in the target, or
- Its modification time is newer than the target copy.

**A file is skipped when:**
- Its path matches `.eml` or `venv` (always).
- Its modification time is in the future — clock-skew artifact protection.
- Its modification time is before `--cutoff` (if given).
- Its directory is in `--exclude`.
- Its directory name matches `--shallow` and the full path does not match `--keep`.

**Shallow list:** For directories matching `--shallow`, only the top-level files are copied. Subdirectories are not traversed. This is useful for large, partially-relevant trees like `Downloads`. The `--keep` flag exempts specific subtrees from this restriction (e.g. `--keep Kindle` allows full recursion inside any directory whose full path contains "Kindle").

**Log files:** After a non-dry run, `copied_YYYY_MM_DD.txt` and `problems_YYYY_MM_DD.txt` are written to `tgt` if there is anything to report.

---

## CLI reference

```
sync-agent content <src> <tgt> [--threshold T] [--dry-run]
sync-agent mirror  <src> <tgt> [--exclude DIR ...] [--shallow DIR ...]
                               [--keep DIR ...] [--cutoff YYYY-MM-DD]
                               [--dry-run]
```

| Flag | Default | Description |
|---|---|---|
| `--threshold` | `0.95` | Cosine-similarity cutoff for content deduplication |
| `--dry-run` | off | Report changes without writing any files |
| `--exclude` | (none) | Directory names to skip entirely during mirror |
| `--shallow` | (none) | Directory names to copy top-level only |
| `--keep` | (none) | Directory names exempt from `--shallow` |
| `--cutoff` | (none) | Skip files older than this date (YYYY-MM-DD) |

---

## Architecture

```
sync_agent/
    similarity.py       — SimilarityEngine: cosine similarity over token sets
    content_engine.py   — SegmentedODFHandler: parse/save .odt files
                          normalize(): text preprocessing for similarity
    sync_managers.py    — ContentAwareSync: merge logic (files + directories)
                          SimpleMirrorSync: file tree mirroring
    cli.py              — argparse entry point wiring the above together
```

The modules have a strict dependency order: `similarity` and `content_engine` are self-contained; `sync_managers` imports from both; `cli` imports only from `sync_managers`.

### Similarity algorithm

Cosine similarity over token sets. Both token lists are lowercased and de-duplicated before comparison, so word order and repetition do not affect the score. A score of 1.0 means identical vocabulary; 0.0 means no shared words.

```
similarity(A, B) = |A ∩ B| / (sqrt(|A|) * sqrt(|B|))
```

The `normalize()` function strips leading date tags and non-word characters before tokenising, so minor punctuation differences between otherwise identical entries do not inflate the apparent distance.

### Content merge algorithm

```
merged = copy of src_data
for each date in tgt_data:
    if date not in merged:
        merged[date] = tgt segments          # wholesale add
    else:
        for each tgt segment:
            if similarity(tgt_seg, every src_seg) < threshold:
                merged[date].append(tgt_seg) # genuinely new
save merged to tgt_path
```

This is a one-way operation (src → tgt). For bidirectional sync, run the tool twice with src and tgt swapped.

---

## Running tests

```bash
pytest tests/ -q
```

The test suite covers: similarity math, `normalize`, ODF parse/save round-trips, merge semantics, `sync_files`, `sync_directory` (archive + filter), and `SimpleMirrorSync` (timestamp logic, exclusion, shallow list, dry-run, log files).

---

## Known limitations

- **One-way per run.** `content` and `mirror` both copy from src to tgt. Run twice (swapping src and tgt) for a full bidirectional sync.
- **`.odt` format only** for content-aware merge. Plain text or other formats are not parsed.
- **Single-level archive.** `sync_directory` archives to `legacy/` in the flat target directory. If the same filename is merged twice in one calendar day, the second archive will fail silently (the first archived file already has today's date stamp) and the merge will still proceed.
- **Shallow list uses regex matching**, so `--shallow Download` would also match a directory called `MyDownloads`. Use precise names to avoid surprises.
