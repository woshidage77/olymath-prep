from collections import defaultdict
from collections import Counter
from typing import Any

from .curriculum import build_curriculum_catalog
from .models import CurriculumCatalog, Cube, ProblemSummary, ProjectionCell, ViewName
from .question_bank import ALL_PROBLEMS


class ProblemNotFoundError(LookupError):
    def __init__(self, problem_id: str) -> None:
        super().__init__(f"unknown demo problem: {problem_id}")
        self.problem_id = problem_id


def get_problem_source(problem_id: str) -> dict[str, Any]:
    for problem in ALL_PROBLEMS:
        if problem["id"] == problem_id:
            return problem
    raise ProblemNotFoundError(problem_id)


def problem_summary(source: dict[str, Any]) -> ProblemSummary:
    return ProblemSummary(**{
        field: source[field]
        for field in ProblemSummary.model_fields
    })


def list_demo_problems(
    *, grade: int | None = None, topic: str | None = None
) -> list[ProblemSummary]:
    problems = [
        problem_summary(source)
        for source in ALL_PROBLEMS
        if (grade is None or source["grade"] == grade)
        and (topic is None or source["topic"] == topic)
    ]
    difficulty_order = {"基础": 0, "进阶": 1, "挑战": 2}
    return sorted(
        problems,
        key=lambda problem: (
            0 if problem.is_featured else 1,
            difficulty_order.get(problem.difficulty, 9),
            problem.title,
            problem.id,
        ),
    )


def get_curriculum(grade: int) -> CurriculumCatalog:
    counts = Counter(source["topic"] for source in ALL_PROBLEMS if source["grade"] == grade)
    return build_curriculum_catalog(grade, counts)


def project_cubes(cubes: list[Cube], view: ViewName) -> list[ProjectionCell]:
    """Project integer cube coordinates into a normalized 2D teaching grid."""
    visible: dict[tuple[int, int], int] = defaultdict(int)
    for cube in cubes:
        if view is ViewName.FRONT:
            key = (cube.x, cube.y)
        elif view is ViewName.LEFT:
            key = (cube.z, cube.y)
        else:
            key = (cube.x, cube.z)
        visible[key] += 1

    if not visible:
        return []

    min_col = min(col for col, _ in visible)
    max_level = max(level for _, level in visible)
    return [
        ProjectionCell(col=col - min_col, row=max_level - level, depth=depth)
        for (col, level), depth in sorted(visible.items())
    ]
