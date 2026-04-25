import os
import shutil
import datetime
from loguru import logger
from .similarity import SimilarityEngine
from .content_engine import SegmentedODFHandler

class BaseSync:
    @staticmethod
    def get_mtime(path):
        return datetime.datetime.fromtimestamp(os.path.getmtime(path))

class ContentAwareSync(BaseSync):
    def __init__(self, threshold=0.95, dry_run=False):
        self.threshold = threshold
        self.dry_run = dry_run
        self.handler = SegmentedODFHandler()
        self.sim = SimilarityEngine()

    def sync(self, source, target):
        logger.info(f"Syncing content: {source} -> {target} (Dry Run: {self.dry_run})")
        src_data = self.handler.parse_to_dict(source)
        tgt_data = self.handler.parse_to_dict(target)
        
        changes = 0
        for dt, segments in src_data.items():
            if dt not in tgt_data:
                tgt_data[dt] = segments
                changes += len(segments)
            else:
                for s_seg in segments:
                    if all(self.sim.similarity(s_seg.split(), t_seg.split()) < self.threshold for t_seg in tgt_data[dt]):
                        tgt_data[dt].append(s_seg)
                        changes += 1
        
        if not self.dry_run and changes > 0:
            self.handler.save_combined(tgt_data, target)
        return changes

class SimpleMirrorSync(BaseSync):
    def __init__(self, exclude_list=None, shallow_list=None, dry_run=False):
        self.exclude = exclude_list or []
        self.shallow = shallow_list or []
        self.dry_run = dry_run

    def sync_tree(self, src_root, tgt_root):
        for root, dirs, files in os.walk(src_root):
            dirs[:] = [d for d in dirs if d not in self.exclude]
            rel_path = os.path.relpath(root, src_root)
            dest_dir = os.path.join(tgt_root, rel_path)
            
            if not self.dry_run and not os.path.exists(dest_dir):
                os.makedirs(dest_dir)

            for f in files:
                src_f, tgt_f = os.path.join(root, f), os.path.join(dest_dir, f)
                if not os.path.exists(tgt_f) or self.get_mtime(src_f) > self.get_mtime(tgt_f):
                    logger.info(f"Copy target: {tgt_f}")
                    if not self.dry_run:
                        shutil.copy2(src_f, tgt_f)
