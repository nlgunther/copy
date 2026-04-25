import argparse
from loguru import logger
from .sync_managers import ContentAwareSync, SimpleMirrorSync

def main():
    parser = argparse.ArgumentParser(description="SyncAgent Professional")
    parser.add_argument("command", choices=["content", "mirror"])
    parser.add_argument("src")
    parser.add_argument("tgt")
    parser.add_argument("--threshold", type=float, default=0.95)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--exclude", nargs="*", help="Folders to skip")
    
    args = parser.parse_args()
    if args.command == "content":
        syncer = ContentAwareSync(threshold=args.threshold, dry_run=args.dry_run)
        count = syncer.sync(args.src, args.tgt)
        logger.success(f"Content sync complete. Changes: {count}")
    elif args.command == "mirror":
        syncer = SimpleMirrorSync(exclude_list=args.exclude, dry_run=args.dry_run)
        syncer.sync_tree(args.src, args.tgt)
        logger.success("Mirror complete.")
