import argparse
import datetime
import os

from loguru import logger

from .sync_managers import ContentAwareSync, SimpleMirrorSync

_EPILOG = """
examples:
  # merge two directories of .odt files (archives originals to legacy/)
  sync-agent content ~/notes/  D:/backup/notes/

  # merge a single file pair, preview only
  sync-agent content diary.odt D:/backup/diary.odt --dry-run

  # lower the dedup threshold (more aggressive merging)
  sync-agent content diary.odt backup/diary.odt --threshold 0.85

  # mirror a directory tree, skip venv and copy only top level of Downloads
  sync-agent mirror ~/Documents D:/Documents --shallow Downloads --exclude venv

  # mirror with a cutoff date and preview
  sync-agent mirror ~/Documents D:/Documents --cutoff 2020-01-01 --dry-run

  # allow full recursion into Kindle even though it matches --shallow
  sync-agent mirror ~/Documents D:/Documents --shallow Downloads --keep Kindle
"""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sync-agent",
        description="Merge segmented .odt files or mirror directory trees.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_EPILOG,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    cp = sub.add_parser(
        "content",
        help="Merge segmented .odt files (single pair or full directory)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    cp.add_argument("src", help="Source .odt file, or directory of .odt files")
    cp.add_argument("tgt", help="Target .odt file, or directory")
    cp.add_argument(
        "--threshold",
        type=float,
        default=0.95,
        metavar="T",
        help="Cosine-similarity threshold for deduplication (default: 0.95). "
             "Two segments are treated as duplicates when their similarity >= T.",
    )
    cp.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing any files.",
    )

    mp = sub.add_parser(
        "mirror",
        help="Mirror a directory tree, copying newer files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mp.add_argument("src", help="Source directory")
    mp.add_argument("tgt", help="Target directory")
    mp.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        metavar="DIR",
        help="Directory names to skip entirely (e.g. --exclude venv .git).",
    )
    mp.add_argument(
        "--shallow",
        nargs="*",
        default=[],
        metavar="DIR",
        help="Directory names to copy shallowly — top level only, no subdirs "
             "(e.g. --shallow Downloads .ipynb_checkpoints NLGMassFiles).",
    )
    mp.add_argument(
        "--keep",
        nargs="*",
        default=[],
        metavar="DIR",
        help="Directory names exempt from --shallow, matched against the full "
             "path (e.g. --keep Kindle keeps full recursion inside Kindle even "
             "if Downloads is shallow).",
    )
    mp.add_argument(
        "--cutoff",
        metavar="YYYY-MM-DD",
        help="Skip files with modification time before this date.",
    )
    mp.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be copied without writing any files.",
    )

    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "content":
        syncer = ContentAwareSync(threshold=args.threshold, dry_run=args.dry_run)
        if os.path.isdir(args.src):
            count = syncer.sync_directory(args.src, args.tgt)
            logger.success("Content sync complete. Files changed: {}", count)
        else:
            count = syncer.sync_files(args.src, args.tgt)
            logger.success("Content sync complete. Segments added: {}", count)

    elif args.command == "mirror":
        cutoff = None
        if args.cutoff:
            try:
                cutoff = datetime.datetime.strptime(args.cutoff, "%Y-%m-%d")
            except ValueError:
                parser.error("--cutoff must be in YYYY-MM-DD format")
        syncer = SimpleMirrorSync(
            exclude_list=args.exclude,
            shallow_list=args.shallow,
            keep_list=args.keep,
            cutoff=cutoff,
            dry_run=args.dry_run,
        )
        syncer.sync_tree(args.src, args.tgt)
