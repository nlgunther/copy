# sync-agent Cheatsheet

## Common Operations

### Mirror — basic
```bash
sync-agent mirror "C:\Users\Ken\PortFiles" "D:\PortFiles"
```

### Mirror — exclude a folder
```bash
sync-agent mirror "C:\Users\Ken\PortFiles" "D:\PortFiles" --exclude NLGMassFiles
```

### Mirror — skip files older than a date
```bash
sync-agent mirror "C:\Users\Ken\PortFiles" "D:\PortFiles" --startdate 01-01-2020
```

### Mirror — combine exclude and startdate
```bash
sync-agent mirror "C:\Users\Ken\PortFiles" "D:\PortFiles" --exclude NLGMassFiles --startdate 01-01-2020
```

### Content sync — single ODF file pair
```bash
sync-agent content "C:\Source\diary.odt" "D:\Backup\diary.odt"
```

### Content sync — skip file if older than a date
```bash
sync-agent content "C:\Source\diary.odt" "D:\Backup\diary.odt" --startdate 01-01-2020
```

### Dry run (preview only, no writes)
```bash
sync-agent mirror "C:\Users\Ken\PortFiles" "D:\PortFiles" --dry-run
sync-agent content "C:\Source\diary.odt" "D:\Backup\diary.odt" --dry-run
```

### Typical two-command workflow (mirror everything, content-sync one folder)
```bash
sync-agent mirror "C:\Users\Ken\PortFiles" "D:\PortFiles" --exclude NLGMassFiles --startdate 01-01-2020
sync-agent content "C:\Users\Ken\PortFiles\NLGFiles\NLGMassFiles" "D:\PortFiles\NLGFiles\NLGMassFiles" --startdate 01-01-2020
```

---

## `mirror` Parameters

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `src` | path | required | Source directory root |
| `tgt` | path | required | Target directory root |
| `--exclude` | name (repeatable) | none | Directory names to skip entirely |
| `--startdate` | `MM-DD-YYYY` | none | Skip source files with mtime before this date |
| `--dry-run` | flag | off | Log what would change; write nothing |

A file is copied only if it is new to the target **or** its source mtime is more
than 30 seconds ahead of the target's mtime.

---

## `content` Parameters

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `src` | path | required | Source `.odt` file |
| `tgt` | path | required | Target `.odt` file |
| `--threshold` | float | `0.95` | Cosine-similarity cutoff for deduplication |
| `--startdate` | `MM-DD-YYYY` | none | Skip if source file mtime is before this date |
| `--dry-run` | flag | off | Log what would change; write nothing |

---

## Common Gotchas

**`--exclude` matches on folder name, not path** — `--exclude NLGMassFiles`
skips any directory named `NLGMassFiles` anywhere in the tree.

**`--startdate` applies to the source file's last-modified timestamp** — it does
not filter by content dates inside the ODF file.

**Mirror does not delete** — files removed from the source are never removed
from the target. Mirror is additive only.

**30-second mtime tolerance** — mirror skips a file if the source is fewer than
30 seconds newer than the target, to avoid re-copying files with near-identical
timestamps (e.g. from a previous copy operation).
