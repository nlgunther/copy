import math

class SimilarityEngine:
    @staticmethod
    def norm(v):
        return math.sqrt(sum(x**2 for x in v))

    def similarity(self, list_a, list_b):
        set_a, set_b = set(map(str.lower, list_a)), set(map(str.lower, list_b))
        intersection = set_a & set_b
        if not set_a or not set_b or not intersection:
            return 0.0
        return len(intersection) / (self.norm([1]*len(set_a)) * self.norm([1]*len(set_b)))
