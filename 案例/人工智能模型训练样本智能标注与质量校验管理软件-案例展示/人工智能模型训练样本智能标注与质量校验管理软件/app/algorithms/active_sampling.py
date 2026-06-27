def rank_samples(samples: list[dict]) -> list[dict]:
    def score(s: dict) -> float:
        risk = 0
        risk += 35 if s.get('is_low_confidence') else 0
        risk += 30 if '质检异常' in (s.get('status') or '') else 0
        risk += 20 * int(s.get('rework_count') or 0)
        risk += 25 if s.get('is_duplicate') else 0
        risk += 40 if s.get('is_ground_truth') else 0
        risk += 10 if '低置信' in (s.get('risk_tags') or '') else 0
        return risk
    return sorted(samples, key=score, reverse=True)
