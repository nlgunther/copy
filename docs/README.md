# sync-agent

`sync-agent` merges and mirrors files between two locations. It handles two
distinct workflows:

- **Content-aware merge** — combines `.odt` diary/journal files by date,
  deduplicating entries that are textually similar (cosine similarity over
  tokens). Use this when you maintain the same journal in two places and want
  a single authoritative copy with nothing lost.
- **Mirror sync** — copies newer files from a source tree to a target tree,
  respecting exclude lists, shallow-copy rules, a cutoff date, and a
  future-timestamp guard. Use this for general file backups.

## Quick Start

```bash
pip install sync-agent

# Merge two .odt journal files
sync-agent content merge --src ~/journal/diary.odt --tgt ~/backup/diary.odt

# Merge all .odt files in a folder
sync-agent content merge --src ~/journal/ --tgt ~/backup/

# Preview without writing (dry run)
sync-agent content merge --src ~/journal/ --tgt ~/backup/ --dry-run

# Mirror a folder to a backup drive
sync-agent mirror --src ~/Documents/ --tgt /mnt/backup/Documents/

# Mirror with a cutoff (only files newer than a date)
sync-agent mirror --src ~/Documents/ --tgt /mnt/backup/Documents/ \
    --cutoff 2024-01-01

# Mirror excluding certain folders
sync-agent mirror --src ~/Documents/ --tgt /mnt/backup/ \
    --exclude node_modules --exclude __pycache__
```

## Key Features

- **Source-authoritative merge**: when source and target have similar entries
  for the same date, source wins. Genuinely new target content is appended.
- **Legacy archiving**: before overwriting any target file in directory mode,
  the current version is moved to `tgt/legacy/<stem>_YYYY_MM_DD.odt`.
- **Similarity threshold**: configurable (default 0.95). Lower it to be more
  aggressive about deduplication; raise it to keep more variants.
- **Shallow-list / keep-list / exclude-list** control which directories the
  mirror recurses into.
- **Future-timestamp guard**: files with an mtime after run-start are skipped
  to avoid clock-skew artifacts on external drives.
- **Dry-run mode** on every subcommand — see exactly what would change before
  committing.

## Installation

```bash
pip install sync-agent
```

Python 3.10+ required. On Windows, `pywin32` is installed automatically.

## CLI Reference

```
sync-agent content merge  --src PATH --tgt PATH [--threshold FLOAT] [--dry-run]
sync-agent mirror         --src PATH --tgt PATH
                          [--exclude DIR ...] [--shallow PAT ...]
                          [--keep PAT ...] [--cutoff DATE] [--dry-run]
```

Full parameter details: [CHEATSHEET.md](CHEATSHEET.md)

Full API reference: [API.md](API.md)
