import datetime
import os
import re
import shutil

from loguru import logger

from .comparison import LegacyRecordComparator, RecordComparator
from .content_engine import SegmentedODFHandler

# Files matching this pattern are excluded from directory discovery:
# date-stamped copies (digits in name) and explicit "copy" files.
_ODT_SKIP = re.compile(r'(?i)\d+|copy')

# Paths matching this pattern are skipped during mirror sync.
# .eml files are transient mail; venv trees are large and ephemeral.
_MIRROR_SKIP = re.compile(r'\.eml$|venv', re.IGNORECASE)


def _is_odt_candidate(filename: str) -> bool:
    return filename.endswith('.odt') and not _ODT_SKIP.search(filename)


class ContentAwareSync:
    """Merge segmented .odt files, or directories of them.

    Source is authoritative: when src and tgt have similar stories for the
    same date, the source version is kept. Target-only stories that are
    genuinely new (similarity below threshold against all src stories) are
    appended.
    """

    def __init__(
        self,
        threshold: float = 0.95,
        dry_run: bool = False,
        comparator: RecordComparator | None = None,
    ):
        self.threshold = threshold
        self.dry_run = dry_run
        self._handler = SegmentedODFHandler()
        self._comparator = comparator or LegacyRecordComparator(threshold=threshold)

    def _is_new(self, candidate: str, existing: list) -> bool:
        """True if candidate is not a duplicate of any existing segment."""
        return not any(
            self._comparator.compare(candidate, s).is_duplicate for s in existing
        )

    def merge(self, src_data: dict, tgt_data: dict) -> dict:
        """Merge tgt_data into src_data, returning the combined dict.

        Source segments are kept as-is. For each date, target segments that
        are genuinely different from all source segments are appended.
        Dates present only in target are added wholesale.

        Example:
            merge({d1: ["A"]}, {d1: ["B"], d2: ["C"]})
            # -> {d1: ["A", "B"], d2: ["C"]}  (if A and B are dissimilar)
        """
        merged = {dt: list(segs) for dt, segs in src_data.items()}
        for dt, segs in tgt_data.items():
            if dt not in merged:
                merged[dt] = list(segs)
            else:
                for seg in segs:
                    if self._is_new(seg, merged[dt]):
                        merged[dt].append(seg)
        return merged

    def sync_files(self, src_path: str, tgt_path: str) -> int:
        """Merge src into tgt (single file pair).

        The target file is overwritten in place with the merged result.
        For safe archiving before overwrite, use sync_directory instead.

        Returns the number of segments new to tgt in the merged result.
        A missing tgt counts as gaining everything from src.
        """
        logger.info("Merging: {} -> {}", src_path, tgt_path)
        src_data = self._handler.parse(src_path)
        tgt_data = self._handler.parse(tgt_path)
        merged = self.merge(src_data, tgt_data)

        # Count segments in merged not in tgt: net gain for the target file.
        # Using tgt as the baseline handles the case where tgt is empty or
        # missing: merged will contain src content, entirely new from tgt's view.
        added = sum(
            len(merged.get(dt, [])) - len(tgt_data.get(dt, []))
            for dt in merged
        )
        logger.info("Segments to add: {}", added)
        if not self.dry_run and added > 0:
            self._handler.save(merged, tgt_path)
        return added

    def sync_directory(self, src_dir: str, tgt_dir: str) -> int:
        """Merge all .odt files from src_dir into tgt_dir.

        Workflow:
        1. Files only in source are copied directly to tgt_dir.
        2. For files in both: the existing target copy is moved to
           tgt_dir/legacy/<stem>_YYYY_MM_DD.odt before the merged result
           is written to tgt_dir. This prevents data loss on a failed merge.

        Numbered and "copy" .odt files (e.g. diary_2024_01_01.odt) are
        excluded from both source and target discovery to avoid processing
        already-archived files.

        Returns the number of files created or changed.
        """
        src_files = {f for f in os.listdir(src_dir) if _is_odt_candidate(f)}
        tgt_files = {f for f in os.listdir(tgt_dir) if _is_odt_candidate(f)}
        common = src_files & tgt_files
        unique_to_src = src_files - tgt_files

        changed = 0
        today = datetime.date.today().strftime("%Y_%m_%d")
        legacy_dir = os.path.join(tgt_dir, "legacy")

        for fn in sorted(unique_to_src):
            logger.info("Copying unique source file: {}", fn)
            if not self.dry_run:
                shutil.copy2(os.path.join(src_dir, fn), os.path.join(tgt_dir, fn))
            changed += 1

        if common and not self.dry_run:
            os.makedirs(legacy_dir, exist_ok=True)

        for fn in sorted(common):
            src_path = os.path.join(src_dir, fn)
            tgt_path = os.path.join(tgt_dir, fn)
            stem, ext = os.path.splitext(fn)
            archived = f"{stem}_{today}{ext}"

            src_data = self._handler.parse(src_path)
            tgt_data = self._handler.parse(tgt_path)
            merged = self.merge(src_data, tgt_data)
            added = sum(
                len(merged.get(dt, [])) - len(src_data.get(dt, []))
                for dt in merged
            )
            logger.info("{}: {} segment(s) from target to add", fn, added)

            if self.dry_run:
                logger.info("[dry-run] Would archive {} -> legacy/{}", fn, archived)
                logger.info("[dry-run] Would write merged file to {}", tgt_path)
            else:
                try:
                    os.rename(tgt_path, os.path.join(legacy_dir, archived))
                except (FileExistsError, FileNotFoundError) as e:
                    logger.warning("Could not archive {}: {}", fn, e)
                self._handler.save(merged, tgt_path)

            if added > 0:
                changed += 1

        return changed


class SimpleMirrorSync:
    """Copy newer files from a source tree to a target tree.

    Honoured behaviours from the original notebook:

    - shallow_list: directories whose names match are copied top-level only
      (no recursion into subdirectories).
    - keep_list: directories exempt from the shallow restriction even when
      their name appears in shallow_list (matched against the full path).
    - exclude_list: directories skipped entirely.
    - cutoff: files older than this datetime are not copied.
    - Future-timestamp guard: files with mtime after the run start are skipped
      (handles clock-skew artifacts on external drives).
    - .eml files and paths containing "venv" are always skipped.
    """

    def __init__(
        self,
        exclude_list: list | None = None,
        shallow_list: list | None = None,
        keep_list: list | None = None,
        cutoff: datetime.datetime | None = None,
        dry_run: bool = False,
    ):
        self.exclude = set(exclude_list or [])
        self.shallow = list(shallow_list or [])
        self.keep = list(keep_list or [])
        self.cutoff = cutoff
        self.dry_run = dry_run
        self._now = datetime.datetime.now()

    def _mtime(self, path: str) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(os.path.getmtime(path))

    def _should_copy(self, src: str, tgt: str) -> bool:
        """True if src should be copied to tgt.

        Returns False for: non-files, .eml/venv paths, future-timestamped
        files, files older than the cutoff, and files where tgt is already
        up to date.
        """
        if not os.path.isfile(src):
            logger.warning("Not a file: {}", src)
            return False
        if _MIRROR_SKIP.search(src):
            return False
        mtime = self._mtime(src)
        if mtime > self._now + datetime.timedelta(seconds=1):
            # Files timestamped more than 1 s in the future are clock-skew artifacts.
            # A 1 s tolerance avoids false positives from sub-millisecond jitter
            # between the filesystem clock and datetime.now() on Windows.
            return False
        if self.cutoff and mtime < self.cutoff:
            return False
        return not os.path.isfile(tgt) or mtime > self._mtime(tgt)

    def _is_shallow(self, dir_name: str, root: str) -> bool:
        """True if this directory should be copied shallowly (no recursion).

        A directory is shallow if its name matches shallow_list AND its full
        path does not match keep_list.
        """
        in_shallow = any(re.search(r'(?i)' + p, dir_name) for p in self.shallow)
        in_keep = any(re.search(r'(?i)' + p, root) for p in self.keep)
        return in_shallow and not in_keep

    def sync_tree(self, src_root: str, tgt_root: str) -> tuple:
        """Copy newer files from src_root to tgt_root.

        Writes copied_YYYY_MM_DD.txt and problems_YYYY_MM_DD.txt to tgt_root
        after a non-dry run if there is anything to report.

        Returns (copied, problems) as lists of 'source: X; target: Y' strings.
        """
        # Snapshot 'now' once per run so future-timestamp detection is consistent.
        self._now = datetime.datetime.now()
        copied, problems = [], []
        today = datetime.date.today().strftime("%Y_%m_%d")

        for root, dirs, files in os.walk(src_root):
            dirs[:] = [d for d in dirs if d not in self.exclude]

            curdir = os.path.basename(root)
            if self._is_shallow(curdir, root):
                logger.debug("Shallow copy only: {}", root)
                dirs[:] = []

            rel = os.path.relpath(root, src_root)
            dest_dir = os.path.join(tgt_root, rel)
            if not self.dry_run and not os.path.exists(dest_dir):
                os.makedirs(dest_dir)

            for filename in files:
                src_f = os.path.join(root, filename)
                tgt_f = os.path.join(dest_dir, filename)
                if not self._should_copy(src_f, tgt_f):
                    continue
                logger.info("Copy: {}", src_f)
                if not self.dry_run:
                    try:
                        shutil.copy2(src_f, tgt_f)
                        copied.append(f"source: {src_f}; target: {tgt_f}")
                    except Exception as e:
                        logger.error("Failed to copy {}: {}", src_f, e)
                        problems.append(f"source: {src_f}; target: {tgt_f}")

        if not self.dry_run:
            for label, entries in [("copied", copied), ("problems", problems)]:
                if entries:
                    log_path = os.path.join(tgt_root, f"{label}_{today}.txt")
                    with open(log_path, "w") as f:
                        f.write("\n".join(entries) + "\n")
                    logger.info("Wrote {} to {}", label, log_path)

        logger.info(
            "Mirror done. Copied: {}, Problems: {}", len(copied), len(problems)
        )
        return copied, problems
