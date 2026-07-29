import pytest

from harness.graders import UnsupportedGraderError, get_grader
from harness.graders.exact_match import ExactMatchGrader
from harness.graders.rubric import RubricGrader
from harness.graders.rule_based import RuleBasedGrader
from harness.graders.unit_test import UnitTestGrader


@pytest.mark.parametrize(
    ("name", "expected_type"),
    [
        ("unit_test", UnitTestGrader),
        ("exact_match", ExactMatchGrader),
        ("rule_based", RuleBasedGrader),
        ("rubric", RubricGrader),
    ],
)
def test_get_grader_returns_registered_type(name, expected_type):
    assert isinstance(get_grader(name), expected_type)


def test_get_grader_accepts_surrounding_whitespace():
    assert isinstance(get_grader("  exact_match\n"), ExactMatchGrader)


def test_get_grader_rejects_unknown_name_and_lists_supported_names():
    with pytest.raises(UnsupportedGraderError) as exc_info:
        get_grader("unknown")

    message = str(exc_info.value)
    assert "unknown" in message
    for supported_name in ("unit_test", "exact_match", "rule_based", "rubric"):
        assert supported_name in message
