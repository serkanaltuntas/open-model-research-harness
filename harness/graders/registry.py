from collections.abc import Callable

from harness.graders.base import Grader
from harness.graders.exact_match import ExactMatchGrader
from harness.graders.rubric import RubricGrader
from harness.graders.rule_based import RuleBasedGrader
from harness.graders.unit_test import UnitTestGrader


class UnsupportedGraderError(ValueError):
    """Raised when a grader name is not registered."""


GRADER_FACTORIES: dict[str, Callable[[], Grader]] = {
    "unit_test": UnitTestGrader,
    "exact_match": ExactMatchGrader,
    "rule_based": RuleBasedGrader,
    "rubric": RubricGrader,
}


def get_grader(name: str) -> Grader:
    normalized_name = name.strip()

    try:
        factory = GRADER_FACTORIES[normalized_name]
    except KeyError as error:
        supported_names = ", ".join(sorted(GRADER_FACTORIES))
        raise UnsupportedGraderError(
            f"Unsupported grader {name!r}. Supported graders: {supported_names}."
        ) from error

    return factory()
