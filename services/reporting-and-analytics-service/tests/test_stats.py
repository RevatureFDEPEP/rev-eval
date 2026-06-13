"""Unit tests for the pure analytics module."""
import pytest
from src.analytics.stats import (
    completion_rate,
    effective_score,
    score_stats,
    status_breakdown,
)


@pytest.mark.parametrize(
    "submission, expected",
    [
        ({"final_score": 9, "trainer_score": 8, "ai_score": 7}, 9.0),
        ({"final_score": None, "trainer_score": 8, "ai_score": 7}, 8.0),
        ({"final_score": None, "trainer_score": None, "ai_score": 7}, 7.0),
        ({"final_score": None, "trainer_score": None, "ai_score": None}, None),
        ({}, None),
    ],
)
def test_effective_score_precedence(submission, expected):
    assert effective_score(submission) == expected


def test_score_stats_empty():
    assert score_stats([]) == {
        "count": 0,
        "min": None,
        "max": None,
        "average": None,
        "median": None,
    }


def test_score_stats_ignores_none_and_computes_odd_median():
    result = score_stats([10, None, 30, 20])
    assert result["count"] == 3
    assert result["min"] == 10.0
    assert result["max"] == 30.0
    assert result["average"] == 20.0
    assert result["median"] == 20.0


def test_score_stats_even_median_is_mean_of_middle_two():
    assert score_stats([10, 20, 30, 40])["median"] == 25.0


def test_score_stats_single_value():
    result = score_stats([42])
    assert result == {"count": 1, "min": 42.0, "max": 42.0, "average": 42.0, "median": 42.0}


def test_status_breakdown_counts_and_handles_missing():
    subs = [
        {"status": "COMPLETED"},
        {"status": "COMPLETED"},
        {"status": "ASSIGNED"},
        {},  # -> UNKNOWN
    ]
    assert status_breakdown(subs) == {"COMPLETED": 2, "ASSIGNED": 1, "UNKNOWN": 1}


def test_completion_rate():
    subs = [
        {"status": "COMPLETED"},
        {"status": "GRADED"},
        {"status": "EVALUATED"},
        {"status": "ASSIGNED"},
    ]
    assert completion_rate(subs) == 0.75


def test_completion_rate_empty_is_zero():
    assert completion_rate([]) == 0.0
