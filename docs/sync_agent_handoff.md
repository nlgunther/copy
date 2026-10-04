# sync-agent / copy package — session handoff

Written because the device link to C:\Users\nlgun's computer dropped mid-session.
A new Cowork session linked to that computer should read this first, then
replace it with a proper `KT.md` at `C:\Users\nlgun\personal\nlgcode\copy\KT.md` (the existing KT.md there is stale — see below).

## Goal

Replace the first part of `oldcode\copyindate091926_newmachine_one_run_path.py` (the ODT content-merge workflow, up through the `for fn,d in combdict.items()` block) with a CLI tool in the `copy` package (`sync_agent`), faithfully, before
moving on to the mirror/copy half of that script.

Immediate concrete task Ken wants to run once this works: content-sync `D:\PortFiles\NLGFiles\NLGMassFiles` → `C:\Users\nlgun\PortFiles\NLGFiles\NLGMassFiles` using the similarity metric to update individual dated records. **This is not
yet possible with the package as it exists** — see "Directory mode is missing"
below.

## Repo state (as last read, before disconnect)

Path: `C:\Users\nlgun\personal\nlgcode\copy`

- Tracked in git (`git log`: d1a3158 → 227d871 → f93bb97 → 3663cfd on `main`,
  pushed to `origin/main`): `.gitignore`, `KT.md`, `README.md`, `docs/API.md`, `docs/CHEATSHEET.md`, `docs/README.md`, `oldcode/copyindate_ed.py`, `oldcode/nlgutls.py`, `oldcode/proc_docs.py`, `oldcode/similarity.py`, `pyproject.toml`, `setup.cfg`, `tests/test_sync.py`.
- **`sync_agent/` at the project root (the actual package code) is untracked** (`git status` showed `?? sync_agent/`; `git ls-files sync_agent` was empty).
  So is `oldcode/copyindate091926_newmachine_one_run_path.py`.
- `sync_agent_source/` has no `.py` files at all anymore — only `pyproject.zip`, `.mypy_cache`, `.pytest_cache`, and `sync_agent.egg-info`. Commit `227d871` deleted the old `sync_agent_source/sync_agent/*.py` when the package moved to
  the project root; nothing replaced it there.
- First action in the new session: confirm this is all still true
  (`git status --short`, `git ls-files sync_agent`), then `git add sync_agent` and commit it as a baseline *before* making any further changes, so the
  current (buggy, incomplete) behavior has a checkpoint.

## KT.md and docs are aspirational, not descriptive

`KT.md`, `docs/API.md`, and `docs/CHEATSHEET.md` describe a `src/sync_agent/` layout with `normalize()`, `merge()`, `sync_files()`, `sync_directory()`,
legacy archiving, a 54-test suite, `MANIFEST.txt`, `verify_install.py`. None of
this exists in the working tree, in `pyproject.zip`, or anywhere in git
history (`git log --all -S"sync_directory"` / `-S"def merge"` found nothing
beyond the docs commit itself). Treat every claim in the current `KT.md` and `docs/` as a design target to implement, not as a description of working code.

The three CLI syntaxes in the docs vs. code also disagree:

- Actual code / `CHEATSHEET.md`: positional `SRC TGT` with `--startdate`.
- `docs/README.md` / `API.md`: `content merge --src/--tgt` with `--cutoff`, `--shallow`, `--keep`.
  Decision pending with Ken: standardize on positional (matches existing code).

## What actually exists today (`sync_agent/`, 4 files, ~160 lines + 10 tests)

- `cli.py` — argparse, `content` and `mirror` subcommands, positional `src tgt`, `--threshold`, `--dry-run`, `--exclude` (nargs, mirror only), `--startdate MM-DD-YYYY`.
- `similarity.py` — `SimilarityEngine` class (cosine similarity over
  lowercased token sets). Functionally fine but structured as a
  single-method stateless class, which the `ken-code-quality` skill flags as
  an anti-pattern; should become a module-level function.
- `content_engine.py` — `SegmentedODFHandler.parse_to_dict` / `.save_combined`. Parses/writes the `<M/D/YYYY>` tagged-paragraph ODT
  format. `parse_to_dict` catches *all* exceptions and returns `{}` on
  failure — see bug below.
- `sync_managers.py` — `ContentAwareSync.sync(source, target)` and `SimpleMirrorSync.sync_tree(src_root, tgt_root)`.
- `tests/test_sync.py` — 10 tests, covering similarity math, tag extraction, `--startdate` behavior for both syncers, and mirror's 30-second mtime
  tolerance. Does not cover directory mode, legacy archiving, or merge
  correctness beyond startdate gating (because those features don't exist).

## Known bugs / gaps, ranked by what blocks Ken's immediate task

1. **No directory mode at all — this is what blocks the D:→C: task.** `ContentAwareSync.sync()` takes two single `.odt` file paths. There is no
   equivalent of the old script's folder listing, common/unique filename
   split, `.odt`-with-digits-or-"copy" exclusion filter, or copying of
   source-only files. To do Ken's actual task today you'd have to call `sync-agent content <file> <file>` once per shared filename by hand, and
   separately copy over D:-only files yourself.

2. **Merge direction is backwards relative to source of truth / the old
   script.** `sync()` uses `target` as the base dict and appends dissimilar `source` segments onto it. The old notebook script (and the docs) make **source** authoritative: on a near-duplicate (similarity ≥ threshold),
   the source version should win, not the target's. As written, for Ken's
   D:→C: direction, a C:-side near-duplicate would be kept over the D:-side
   one — the opposite of what he wants if D: is meant to be authoritative. **Fix this before running anything for real.**

3. **Corrupted/malformed target file silently treated as empty.** `parse_to_dict`'s bare `except Exception: return {}` means an unreadable
   target file looks like a new/empty file, and the merge will overwrite it
   with source-only content instead of skipping it and reporting a problem
   (which is what the old script did via its `problems` list).

4. **No legacy/backup archiving before overwrite.** The old script's `SAVE_LEGACY` behavior (move existing target to `tgt/legacy/<stem>_YYYY_MM_DD.odt` before writing the merged result) isn't
   implemented. `save_combined` writes straight over the target, and isn't
   atomic (no temp-file + `os.replace`).

5. **Similarity compares raw tokens, not normalized ones.** The old code
   lowercased and stripped punctuation before tokenizing
   (`convert_tkn`/`convert`); the current `sync()` just does `s_seg.split()` / `t_seg.split()` on raw text, so e.g. `"world,"` vs `"world"` lowers the score. Minor but worth fixing alongside the
   similarity-engine rewrite.

6. **Mirror mode is also partial** relative to the old script's second half:
   CLI has no `--shallow`/`--keep`/`--cutoff` wiring (though `SimpleMirrorSync.__init__` accepts `shallow_list`), no `.eml`/`venv` skip, no future-timestamp guard, no `copied_*.txt`/`problems_*.txt` reports. Lower priority than the content-merge gaps above since Ken's
   immediate ask is content-sync.

## `similarity.py` replacement — agreed direction (Ken confirmed interest)

The cosine-over-token-sets metric itself is fine and already stdlib-only;
keep the math (|A∩B| / sqrt(|A|·|B|)) — don't switch to `difflib` or similar,
since that's a different (order-sensitive) metric and would silently change
what 0.95 means. What should change:

- Tokenize each story once as `frozenset(re.findall(r'\w+', s.lower()))` (normalize-then-split, matching old `convert_tkn` semantics) instead of
  the old script's per-pair numpy/itertools cartesian-product rebuild.
- Drop numpy entirely; use a plain nested loop or generator with a cheap
  size-ratio bound (`sqrt(min(|A|,|B|)/max(|A|,|B|))`) to skip pairs that
  can't reach threshold before computing the intersection.
- Replace the old SHA-256-hash-based near-duplicate detection with a `set` of normalized strings — Python's string hashing already gives
  the same dedup power for free.
- Refactor `SimilarityEngine` (class) → module-level `similarity()` function
  per `ken-code-quality` (single-method stateless class = navigation hell). `sync_agent/` currently still has the class form; `docs/API.md` already
  documents the module-level-function form, so the docs are ahead of the
  code here specifically.

## Combination/merge semantics (for the new directory-mode `sync_files`)

Source is the base; nothing is written until the merge for a file pair fully
succeeds (no partial overwrite).

- Dates present only in target: added as-is.
- Dates in both: every source story for that date is kept verbatim. A target
  story for that date is dropped if it exactly matches (after
  normalization) or is similarity ≥ threshold against *any* source story for
  that date; otherwise it's appended after the source stories.
- Known residual data-loss modes to flag to Ken, not yet resolved:
  - A deliberately-edited target story that happens to score ≥ threshold
    against a source story is dropped.
  - Two near-duplicate target-only stories can both survive (new stories are
    only compared against source, not against each other) — old script has
    this same gap; open question whether to fix it or keep parity.
  - Anything in the target ODT that isn't a tagged story (preamble text,
    styles, tables, images) is discarded on rewrite — both old and new code
    do this; it's inherent to the flat-paragraph round-trip format, not a
    regression.

## Proposed CLI surface for directory-mode content sync (not yet implemented)

Positional, matching existing `cli.py` style:

```
sync-agent content SRC TGT [options]
```

New/changed flags beyond what exists today:

- `--reverse` — swap source/target (replaces old `FROM_USB` flag).
- `--file NAME` (repeatable) — limit to named files instead of all common
  files.
- `--include-all` — disable the digits-or-"copy" filename exclusion filter.
- `--no-copy-unique` — don't copy source-only files to target.
- `--legacy` / `--no-legacy` (default: **on**, reversing the old script's
  default-off `SAVE_LEGACY`) — archive target file before overwrite.
- `--legacy-dir NAME` (default `legacy`).
- `-v/--verbose`, `-q/--quiet`.
- Keep existing `--threshold`, `--dry-run`, `--startdate`.
- `SRC`/`TGT` can be a directory (new) or a single `.odt` (existing
  behavior, preserved).

Open decisions Ken hasn't confirmed yet:

1. Legacy archiving on by default — proposed yes, pending confirmation.
2. Whether to also dedupe new target-only stories against each other
   (residual data-loss mode above) — leaning toward leaving old-script
   parity (no) unless Ken wants it fixed.

## Immediate next steps once reconnected

1. Verify repo state matches this doc (`git status --short`, `git ls-files sync_agent`, `git log --oneline`).
2. Commit untracked `sync_agent/` as a baseline before further edits.
3. Get Ken's answer on the two open decisions above (legacy-default,
   new-vs-new dedup).
4. Fix `ContentAwareSync.sync()` merge direction (source-authoritative) and `parse_to_dict`'s silent-failure-on-corrupt-file behavior — do this before
   running anything against Ken's real D:/C: folders, since the current
   direction bug would let a C:-side near-duplicate silently win over D:.
5. Implement directory mode (listing, common/unique split, unique-file copy,
   per-file merge loop, legacy archiving) — this is what Ken is actually
   blocked on.
6. Refactor `similarity.py` per the agreed plan above.
7. Replace stale `KT.md` in the repo with the current state (this doc is the
   source for that).
8. Only then run the real D:\PortFiles\NLGFiles\NLGMassFiles →
   C:\Users\nlgun\PortFiles\NLGFiles\NLGMassFiles sync Ken is waiting on —
   with `--dry-run` first.
