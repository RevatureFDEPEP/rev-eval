import pytest
from src.scoring import ScoreResult, score_question
from src.scoring.exact_match import score_exact
from src.scoring.partial_credit import score_jaccard


class TestExactMatch:
    @pytest.mark.parametrize(
        "correct, submitted, expected",
        [
            ([1], [1], 1.0),
            ([1], [2], 0.0),
            ([True], [True], 1.0),
            ([True], [False], 0.0),
            ([1], [], 0.0),
            ([], [], 1.0),
        ],
    )
    def test_score_exact(self, correct, submitted, expected):
        assert score_exact(correct, submitted) == expected


class TestJaccard:
    @pytest.mark.parametrize(
        "correct, submitted, expected",
        [
            ([1, 2, 3], [1, 2, 3], 1.0),
            ([1, 2, 3], [1], pytest.approx(1 / 3)),
            ([1, 2, 3], [4, 5, 6], 0.0),
            ([1, 2], [1, 2, 3, 4], 0.5),
            ([], [], 0.0),
            ([1, 2], [], 0.0),
        ],
    )
    def test_score_jaccard(self, correct, submitted, expected):
        assert score_jaccard(correct, submitted) == expected


class TestScoreDispatcher:
    @pytest.mark.parametrize(
        "qtype, correct, submitted, exp_score, exp_algo",
        [
            ("mcq", [1], [1], 1.0, "exact_match"),
            ("mcq", [1], [2], 0.0, "exact_match"),
            ("true_false", [True], [True], 1.0, "exact_match"),
            ("true_false", [True], [False], 0.0, "exact_match"),
            ("multi", [1, 2], [1, 2], 1.0, "jaccard"),
            ("multi", [1, 2, 3], [1], pytest.approx(1 / 3), "jaccard"),
            ("text", ["anything"], ["anything"], None, "none"),
            ("mcq", None, [1], None, "none"),
            ("mcq", [], [1], None, "none"),
            ("unknown", [1], [1], None, "none"),
        ],
    )
    def test_dispatch(self, qtype, correct, submitted, exp_score, exp_algo):
        result = score_question(qtype, correct, submitted)
        assert isinstance(result, ScoreResult)
        assert result.score == exp_score
        assert result.algorithm == exp_algo
