def score_exact(correct: list, submitted: list) -> float:
    if not correct and not submitted:
        return 1.0
    if not submitted:
        return 0.0
    return 1.0 if {str(v) for v in correct} == {str(v) for v in submitted} else 0.0
