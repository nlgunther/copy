# sync-agent API Reference

## Module: `sync_agent.similarity`

### `similarity(tokens_a, tokens_b) → float`

Cosine similarity over token sets.

**Parameters:**
- `tokens_a` (list[str]): Tokens from the first string.
- `tokens_b` (list[str]): Tokens from the second string.

**Returns:**
float in [0.0, 1.0]. 1.0 means identical token sets; 0.0 means no overlap
or either input is empty.

**Notes:**
Comparison is case-insensitive. Token order is ignored — this is set-based,
not sequence-based. Two identical long strings return 1.0; two strings sharing
half their (unique) vocabulary return 0.5.

**Example:**
```python
from sync_agent.similarity import similarity

similarity("hello world".split(), "hello world".split())  # -> 1.0
similarity("hello world".split(), "hello there".split())  # -> 0.5
similarity(["a", "b", "c"], ["d", "e", "f"])              # -> 0.0
similarity([], ["a", "b"])                                 # -> 0.0
```

---

## Module: `sync_agent.content_engine`

### `normalize(text) → str`

Lowercase and strip punctuation from a string for similarity comparison.

**Parameters:**
- `text` (str): Raw segment text.

**Returns:**
str: Lowercased text with punctuation removed.

**Example:**
```python
from sync_agent.content_engine import normalize

normalize("Hello, World!")  # -> "hello world"
normalize("It's a test.")   # -> "its a test"
```

---

### Class: `SegmentedODFHandler`

Parse and write `.odt` files structured as date-tagged segments.

The expected `.odt` format is alternating date-tag paragraphs and content
paragraphs:

```
<M/D/YYYY>
Story or journal entry text...

<M/D/YYYY>
Another entry...
```

Paragraphs not matching the tag pattern are concatenated into the preceding
date's segment.

#### Class attributes

- `TAG_REGEX` (re.Pattern): Compiled pattern matching `<M/D/YYYY>` tags
  (e.g. `<1/15/2024>`).

#### `parse(path) → dict[date, list[str]]`

Read an `.odt` file and return its segments indexed by date.

**Parameters:**
- `path` (str): Path to the `.odt` file. A missing file returns `{}`.

**Returns:**
dict mapping `datetime.date` → list of segment strings for that date.
Returns `{}` if the file does not exist or contains no tagged segments.

**Raises:**
- No exceptions are raised for missing files (returns `{}`).
- May raise `odf`-library errors for malformed `.odt` content.

**Example:**
```python
from sync_agent.content_engine import SegmentedODFHandler

handler = SegmentedODFHandler()
data = handler.parse("diary.odt")
# {datetime.date(2024, 1, 15): ["Story text here..."], ...}
```

#### `save(data, path)`

Write a date-indexed segment dict back to an `.odt` file.

**Parameters:**
- `data` (dict[date, list[str]]): Segments to write, as returned by `parse`.
- `path` (str): Destination path. Overwrites if it exists.

**Returns:** None

**Example:**
```python
handler.save(data, "output.odt")
```

---

## Module: `sync_agent.sync_managers`

### Class: `ContentAwareSync`

Merge segmented `.odt` files, or directories of them.

Source is authoritative: when src and tgt have similar stories for the same
date, the source version is kept. Target-only stories that are genuinely new
(similarity below threshold against all src stories for that date) are appended.

#### `__init__(threshold=0.95, dry_run=False)`

**Parameters:**
- `threshold` (float): Cosine-similarity cutoff. Segments at or above this
  value are considered duplicates. Default: `0.95`.
- `dry_run` (bool): If True, log actions but write nothing. Default: `False`.

#### `merge(src_data, tgt_data) → dict[date, list[str]]`

Merge two parsed segment dicts into one.

Source segments are kept as-is. For each date, target segments that are
genuinely different from all source segments for that date are appended.
Dates present only in target are added wholesale.

**Parameters:**
- `src_data` (dict[date, list[str]]): Authoritative segments (from source).
- `tgt_data` (dict[date, list[str]]): Candidate segments (from target).

**Returns:**
dict[date, list[str]]: Union of both, with source taking precedence for
near-duplicate entries.

**Example:**
```python
from datetime import date
from sync_agent.sync_managers import ContentAwareSync

syncer = ContentAwareSync(threshold=0.95)
d1 = date(2024, 1, 1)
d2 = date(2024, 1, 2)

merged = syncer.merge(
    src_data={d1: ["Source story A"]},
    tgt_data={d1: ["Target story B"], d2: ["Target only story"]},
)
# {d1: ["Source story A", "Target story B"], d2: ["Target only story"]}
# (assuming A and B are dissimilar)
```

#### `sync_files(src_path, tgt_path) → int`

Merge src into tgt (single file pair).

The target file is overwritten in place with the merged result. For safe
archiving before overwrite, use `sync_directory` instead.

**Parameters:**
- `src_path` (str): Source `.odt` file path.
- `tgt_path` (str): Target `.odt` file path. May be missing (treated as empty).

**Returns:**
int: Number of segments added to the target. A missing target counts as
gaining all segments from source.

**Example:**
```python
syncer = ContentAwareSync()
added = syncer.sync_files("~/journal/diary.odt", "~/backup/diary.odt")
print(f"{added} new segments written")
```

#### `sync_directory(src_dir, tgt_dir) → int`

Merge all `.odt` files from src_dir into tgt_dir.

**Workflow:**
1. Files only in source are copied directly to `tgt_dir`.
2. For files in both: the existing target copy is moved to
   `tgt_dir/legacy/<stem>_YYYY_MM_DD.odt` before the merged result is written.
   This prevents data loss on a failed merge.

Numbered and "copy" `.odt` files are excluded from discovery (e.g.
`diary_2024_01_01.odt` is skipped).

**Parameters:**
- `src_dir` (str): Source directory path.
- `tgt_dir` (str): Target directory path.

**Returns:**
int: Number of files created or changed.

**Example:**
```python
syncer = ContentAwareSync(dry_run=True)
changed = syncer.sync_directory("~/journal/", "~/backup/journal/")
print(f"Would change {changed} file(s)")
```

---

### Class: `SimpleMirrorSync`

Copy newer files from a source tree to a target tree.

#### `__init__(exclude_list=None, shallow_list=None, keep_list=None, cutoff=None, dry_run=False)`

**Parameters:**
- `exclude_list` (list[str] | None): Directory names to skip entirely.
- `shallow_list` (list[str] | None): Regex patterns matched against directory
  names. Matching directories are copied top-level only (no recursion).
- `keep_list` (list[str] | None): Regex patterns matched against the full path.
  A directory is exempt from shallow restriction if its path matches any entry
  here, even if its name matches `shallow_list`.
- `cutoff` (datetime.datetime | None): Files with mtime before this datetime
  are not copied.
- `dry_run` (bool): If True, log actions but write nothing. Default: `False`.

#### `sync_tree(src_root, tgt_root) → tuple[list[str], list[str]]`

Copy newer files from src_root to tgt_root.

Files are copied if: they are newer than their counterpart in tgt, or no
counterpart exists. `.eml` files and paths containing `venv` are always skipped.
Files with mtime after run-start are skipped (future-timestamp guard).

After a non-dry run, writes `copied_YYYY_MM_DD.txt` and
`problems_YYYY_MM_DD.txt` to `tgt_root` if there is anything to report.

**Parameters:**
- `src_root` (str): Source directory root.
- `tgt_root` (str): Target directory root.

**Returns:**
tuple[list[str], list[str]]: `(copied, problems)` where each entry is a
string of the form `"source: X; target: Y"`.

**Example:**
```python
from datetime import datetime
from sync_agent.sync_managers import SimpleMirrorSync

mirror = SimpleMirrorSync(
    exclude_list=["node_modules", ".git"],
    cutoff=datetime(2024, 1, 1),
)
copied, problems = mirror.sync_tree("~/Documents/", "/mnt/backup/Documents/")
print(f"Copied {len(copied)} file(s); {len(problems)} problem(s)")
```

---

## Workflows

### Workflow 1: Consolidating a journal split across two machines

You maintain a diary on a laptop and a desktop. Entries exist on both,
sometimes overlapping. You want a single backup copy with everything and no
duplicates.

```python
from sync_agent.sync_managers import ContentAwareSync

syncer = ContentAwareSync(threshold=0.95)

# Step 1: dry run to see what would be added
added = ContentAwareSync(dry_run=True).sync_directory(
    "/laptop/journal/",
    "/backup/journal/",
)
print(f"Would add entries from {added} file(s)")

# Step 2: run for real
syncer.sync_directory("/laptop/journal/", "/backup/journal/")

# The backup/journal/ folder now contains the union of both.
# Previous target files are preserved in backup/journal/legacy/.
```

### Workflow 2: Nightly mirror of Documents to an external drive

You want a nightly backup of your Documents folder, skipping build artifacts
and only copying files created in the last year.

```python
from datetime import datetime
from sync_agent.sync_managers import SimpleMirrorSync

mirror = SimpleMirrorSync(
    exclude_list=["node_modules", "__pycache__", ".git", "venv"],
    shallow_list=["archive"],          # Don't recurse into archive folders
    keep_list=["projects/important"],  # But do recurse here even if named archive
    cutoff=datetime(2024, 1, 1),
    dry_run=False,
)

copied, problems = mirror.sync_tree(
    "C:/Users/Ken/Documents/",
    "E:/Backup/Documents/",
)

if problems:
    print(f"WARNING: {len(problems)} file(s) failed to copy")
    for p in problems:
        print(" ", p)
else:
    print(f"Done. {len(copied)} file(s) updated.")
```

Or equivalently from the CLI:

```bash
sync-agent mirror \
    --src "C:/Users/Ken/Documents/" \
    --tgt "E:/Backup/Documents/" \
    --exclude node_modules --exclude __pycache__ --exclude .git \
    --shallow archive \
    --keep "projects/important" \
    --cutoff 2024-01-01
```

### Workflow 3: Merging a single file pair with a custom threshold

You have two versions of the same file and want to keep both when entries
differ by more than a few words, but deduplicate near-identical entries.
The default 0.95 threshold is too strict — you want entries that are 80%
similar to count as duplicates.

```python
from sync_agent.sync_managers import ContentAwareSync

# Lower threshold catches more near-duplicates
syncer = ContentAwareSync(threshold=0.80)
added = syncer.sync_files(
    src_path="/travel/2023_Italy.odt",
    tgt_path="/backup/2023_Italy.odt",
)
print(f"Net new segments written to backup: {added}")
```

### Workflow 4: Inspecting merged data before saving

You want to check the merged dict programmatically before committing it to disk.

```python
from sync_agent.content_engine import SegmentedODFHandler
from sync_agent.sync_managers import ContentAwareSync

handler = SegmentedODFHandler()
syncer = ContentAwareSync(threshold=0.95)

src_data = handler.parse("/laptop/diary.odt")
tgt_data = handler.parse("/backup/diary.odt")

merged = syncer.merge(src_data, tgt_data)

# Inspect before writing
for dt, segs in sorted(merged.items()):
    print(f"{dt}: {len(segs)} segment(s)")

# Write when satisfied
handler.save(merged, "/backup/diary.odt")
```
