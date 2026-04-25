import pytest
from sync_agent.similarity import SimilarityEngine
from sync_agent.content_engine import SegmentedODFHandler

def test_similarity_math():
    engine = SimilarityEngine()
    # Applied probability: 1 matching token / sqrt(2*2) = 0.5
    assert engine.similarity(["python", "math"], ["python", "law"]) == pytest.approx(0.5)

def test_tag_extraction():
    handler = SegmentedODFHandler()
    # Test regex for your specific tag format
    sample = "<12/25/2025>Family trip to Madrid."
    import re
    tags = re.findall(handler.TAG_REGEX, sample)
    assert len(tags) == 1
    assert tags[0] == "<12/25/2025>"