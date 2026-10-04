"""Pairwise record comparison for content-aware merging.

Replicates oldcode/copyindate_ed.py's two-layer dedup: a coarse exact-match
check first (catches anything differing only by whitespace/case/
punctuation), falling back to cosine-similarity scoring only when the
coarse check doesn't resolve it. Comparator and similarity measure are
both swappable (see RecordComparator / SimilarityMeasure) for later
upgrades; this default replicates the old notebook's behavior exactly,
including its known quirks.
"""
import re
from dataclasses import dataclass
from typing import Literal, Protocol

from .content_engine import normalize
from .similarity import similarity as _cosine_similarity

DEFAULT_THRESHOLD = 0.95


def convert(s: str) -> str:
    """Strip every non-word character and lowercase. Matches old copyindate_ed.convert()."""
    return re.sub(r'\W', '', str(s).strip()).lower()


@dataclass(frozen=True)
class ComparisonResult:
    is_duplicate: bool
    method: Literal["exact", "similarity"]
    score: float


class SimilarityMeasure(Protocol):
    def score(self, tokens_a: list[str], tokens_b: list[str]) -> float: ...


class CosineTokenSimilarity:
    """Cosine similarity over lowercased token sets (sync_agent.similarity.similarity)."""

    def score(self, tokens_a: list[str], tokens_b: list[str]) -> float:
        return _cosine_similarity(tokens_a, tokens_b)


class RecordComparator(Protocol):
    def compare(self, a: str, b: str) -> ComparisonResult: ...


class LegacyRecordComparator:
    """Default comparator: replicates copyindate_ed.py's combine_file_dicts exactly."""

    def __init__(self, threshold: float = DEFAULT_THRESHOLD, similarity: SimilarityMeasure | None = None):
        self.threshold = threshold
        self.similarity = similarity or CosineTokenSimilarity()

    def compare(self, a: str, b: str) -> ComparisonResult:
        if convert(a) == convert(b):
            return ComparisonResult(is_duplicate=True, method="exact", score=1.0)
        score = self.similarity.score(normalize(a).split(), normalize(b).split())
        return ComparisonResult(is_duplicate=score >= self.threshold, method="similarity", score=score)
