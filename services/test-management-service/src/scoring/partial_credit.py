def score_jaccard(correct: list, submitted: list) -> float:
    c = {str(v) for v in correct}
    s = {str(v) for v in submitted}
    union = c | s
    if not union:
        return 0.0
    return len(c & s) / len(union)
