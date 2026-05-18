# sync-agent Cheatsheet

## Common Operations

### Content-aware merge — single file pair
```bash
sync-agent content merge --src ~/journal/diary.odt --tgt ~/backup/diary.odt
```

### Content-aware merge — directory
```bash
sync-agent content merge --src ~/journal/ --tgt ~/backup/journal/
```

### Content-aware merge — lower threshold (catch near-duplicates)
```bash
sync-agent content merge --src ~/journal/ --tgt ~/backup/ --threshold 0.85
```

### Dry run (preview only, no writes)
```bash
sync-agent content merge --src ~/journal/ --tgt ~/backup/ --dry-run
sync-agent mirror --src ~/Documents/ --tgt /mnt/backup/ --dry-run
```

### Mirror with cutoff
```bash
sync-agent mirror --src ~/Documents/ --tgt /mnt/backup/ --cutoff 2024-06-01
```

### Mirror — exclude folders by name
```bash
sync-agent mirror --src ~/Projects/ --tgt /mnt/backup/ \
    --exclude node_modules --exclude .git --exclude __pycache__
```

### Mirror — shallow copy matching directories (no recursion)
```bash
# Copy top-level files in any folder named "archive", but don't recurse
sync-agent mirror --src ~/Projects/ --tgt /mnt/backup/ --shallow archive
```

### Mirror — keep recursing into specific paths even if shallow matches
```bash
# Shallow on "archive", but recurse into paths containing "important"
sync-agent mirror --src ~/Projects/ --tgt /mnt/backup/ \
    --shallow archive --keep important
```

---

## `content merge` Parameters

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `--src` | path | required | Source `.odt` file or directory |
| `--tgt` | path | required | Target `.odt` file or directory |
| `--threshold` | float | `0.95` | Similarity threshold; segments with cosine similarity ≥ threshold are treated as duplicates |
| `--dry-run` | flag | off | Log what would change; write nothing |

---

## `mirror` Parameters

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `--src` | path | required | Source directory root |
| `--tgt` | path | required | Target directory root |
| `--exclude` | name (repeatable) | none | Directory names to skip entirely |
| `--shallow` | pattern (repeatable) | none | Directory names to copy top-level only (no recursion) |
| `--keep` | pattern (repeatable) | none | Path substrings exempt from shallow restriction |
| `--cutoff` | `YYYY-MM-DD` | none | Skip files older than this date |
| `--dry-run` | flag | off | Log what would change; write nothing |

---

## Common Gotchas

**Threshold is inclusive** — a pair with similarity exactly equal to the
threshold is treated as a duplicate and the target segment is dropped.
If you want to keep slightly similar entries, lower the threshold, don't raise it.

**Directory mode ignores numbered and "copy" files** — files whose names
contain digits or the word "copy" (case-insensitive) are excluded from
discovery. This prevents re-processing already-archived ODT files like
`diary_2024_01_01.odt`.

**Legacy archives accumulate** — each directory-mode run that overwrites a
target file adds a dated copy in `tgt/legacy/`. Clean this folder periodically
if disk space matters.

**Mirror does not delete** — files removed from the source tree are never
removed from the target. Mirror is additive only.

**`.eml` files and `venv` paths are always skipped** in mirror mode, regardless
of exclude-list settings.

**Future-timestamped files are skipped** — files with mtime after run-start are
silently ignored. This handles clock-skew artifacts from external drives; check
your system clock if newly created files aren't being mirrored.

**Mirror log files** — after a non-dry-run mirror, `copied_YYYY_MM_DD.txt` and
`problems_YYYY_MM_DD.txt` are written to `tgt_root` if there is anything to
report.
