import math


def similarity(tokens_a: list, tokens_b: list) -> float:
    """Cosine similarity over token sets.

    Tokens are lowercased and de-duplicated before comparison, so word order
    and repetition don't affect the score.

    Example:
        similarity("hello world".split(), "hello there".split())
        # -> 0.5  (1 shared token / sqrt(2) / sqrt(2))
    """
    set_a = set(map(str.lower, tokens_a))
    set_b = set(map(str.lower, tokens_b))
    common = len(set_a & set_b)
    if not set_a or not set_b or not common:
        return 0.0
    return common / (math.sqrt(len(set_a)) * math.sqrt(len(set_b)))
