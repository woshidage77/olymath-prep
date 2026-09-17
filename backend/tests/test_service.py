import json

from fastapi.testclient import TestClient

from app.catalog import get_curriculum, get_problem_source
from app.main import app
from app.models import Cube, LessonBrief, SearchRequest, ViewName
from app.retrieval import search_question_bank
from app.service import (
    ProblemNotFoundError,
    build_lesson_plan,
    list_demo_problems,
    project_cubes,
)
from app.workflow import run_lesson_workflow, validate_output_node

client = TestClient(app)


def test_front_projection_merges_depth_without_losing_count() -> None:
    cubes = [
        Cube(x=0, y=0, z=0), Cube(x=0, y=0, z=1),
        Cube(x=1, y=1, z=0),
    ]
    cells = project_cubes(cubes, ViewName.FRONT)
    assert [cell.model_dump() for cell in cells] == [
        {"col": 0, "row": 1, "depth": 2},
        {"col": 1, "row": 0, "depth": 1},
    ]


def test_lesson_plan_uses_original_demo_data_without_page_constraints() -> None:
    plan = build_lesson_plan(LessonBrief())
    assert len(plan.stages) == 3
    assert plan.demo_mode is True
    assert plan.selected_problem.id == "cube-view-001"
    assert {stage.problem_id for stage in plan.stages} == {"cube-view-001"}
    assert [stage.phase for stage in plan.stages] == ["problem", "concept", "return"]
    assert plan.related_problems[0].problem.id == "cube-view-002"
    assert "小方块" in plan.teaching_strategy


def test_catalog_contains_broad_grade_five_question_bank() -> None:
    problems = list_demo_problems()
    assert len(problems) == 136
    assert {"cube-view-001", "cmath-g5-100"}.issubset({problem.id for problem in problems})
    assert {problem.content_kind for problem in problems} == {"原创教学题", "开放数据题"}
    assert sum(problem.source_label == "CMATH 五年级开放数据" for problem in problems) == 100
    assert len({problem.id for problem in problems}) == 136
    assert len({problem.revision_id for problem in problems}) == 136
    assert {problem.unit_id for problem in problems} == {
        f"5a-{index}" for index in range(1, 8)
    } | {f"5b-{index}" for index in range(1, 9)}


def test_curriculum_exposes_folders_and_counts_every_question() -> None:
    catalog = get_curriculum(5)
    assert catalog.available is True
    assert len(catalog.units) == 15
    assert sum(unit.problem_count for unit in catalog.units) == 136
    assert min(unit.problem_count for unit in catalog.units) >= 2
    assert get_curriculum(4).available is False


def test_selected_problem_changes_plan_without_reusing_previous_geometry() -> None:
    first = build_lesson_plan(LessonBrief(starting_problem_id="cube-view-001"))
    second = build_lesson_plan(LessonBrief(starting_problem_id="cube-view-002"))
    assert second.selected_problem.id == "cube-view-002"
    assert second.stages[0].cubes != first.stages[0].cubes
    assert second.related_problems[0].problem.id == "cube-view-003"


def test_contrast_problem_keeps_front_silhouette_but_changes_top_view() -> None:
    first = build_lesson_plan(LessonBrief(starting_problem_id="cube-view-001"))
    second = build_lesson_plan(LessonBrief(starting_problem_id="cube-view-002"))
    first_front = {(cell.col, cell.row) for cell in first.stages[0].projections[ViewName.FRONT]}
    second_front = {(cell.col, cell.row) for cell in second.stages[0].projections[ViewName.FRONT]}
    assert first_front == second_front
    assert first.stages[0].projections[ViewName.TOP] != second.stages[0].projections[ViewName.TOP]


def test_unknown_problem_fails_explicitly() -> None:
    try:
        build_lesson_plan(LessonBrief(starting_problem_id="missing-problem"))
    except ProblemNotFoundError as error:
        assert error.problem_id == "missing-problem"
    else:
        raise AssertionError("expected ProblemNotFoundError")


def test_api_rejects_blank_topic() -> None:
    response = client.post(
        "/api/demo/lesson-plan",
        json={"grade": 5, "topic": "   "},
    )
    assert response.status_code == 422


def test_api_distinguishes_health_from_lesson_generation() -> None:
    health = client.get("/api/health")
    plan = client.post("/api/demo/lesson-plan", json={
        "grade": 5,
        "topic": "观察物体",
    })
    assert health.json() == {"status": "ok", "mode": "demo"}
    assert plan.status_code == 200
    assert plan.json()["brief"]["topic"] == "观察物体"


def test_api_lists_problems_and_returns_404_for_unknown_problem() -> None:
    catalog = client.get("/api/demo/problems")
    missing = client.post("/api/demo/lesson-plan", json={
        "grade": 5,
        "topic": "观察物体",
        "starting_problem_id": "not-in-catalog",
    })
    assert catalog.status_code == 200
    assert len(catalog.json()) == 136
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "problem_not_found"


def test_langgraph_success_trace_stops_for_teacher_review() -> None:
    state = run_lesson_workflow(LessonBrief().model_dump(mode="json"))
    assert state["status"] == "waiting_teacher_review"
    assert state["trace"] == [
        "validate_brief:passed",
        "retrieve_candidate:found",
        "retrieve_context:completed",
        "propose_sequence:completed",
        "draft_teaching_notes:completed",
        "validate_output:passed",
        "await_teacher_review:pending",
    ]
    assert json.loads(json.dumps(state, ensure_ascii=False))["selected_problem"]["id"] == "cube-view-001"
    assert state["retrieval_context"][0]["revision_id"] == "cube-view-001-r1"
    assert all(item["problem"]["id"] != "cube-view-001" for item in state["retrieval_results"])


def test_langgraph_no_candidate_stops_before_drafting() -> None:
    request = LessonBrief(starting_problem_id="missing-problem").model_dump(mode="json")
    state = run_lesson_workflow(request)
    assert state["status"] == "no_candidate"
    assert state["error_code"] == "problem_not_found"
    assert state["trace"][-1] == "retrieve_candidate:not_found"
    assert "stages" not in state


def test_langgraph_invalid_input_stops_at_validation() -> None:
    state = run_lesson_workflow({"topic": "   "})
    assert state["status"] == "invalid_input"
    assert state["error_code"] == "invalid_brief"
    assert state["trace"] == ["validate_brief:failed"]


def test_langgraph_rejects_draft_that_references_another_problem() -> None:
    state = run_lesson_workflow(LessonBrief().model_dump(mode="json"))
    state["stages"][1]["problem_id"] = "cube-view-999"
    result = validate_output_node(state)
    assert result["status"] == "invalid_output"
    assert result["error_code"] == "invalid_workflow_output"


def test_question_bank_search_returns_explainable_ranked_results() -> None:
    results = search_question_bank(SearchRequest(query="上视图 高度", grade=5, limit=4))
    assert results
    assert results[0].problem.id == "cube-view-006"
    assert results[0].score >= results[-1].score
    assert "concepts" in results[0].matched_fields


def test_question_bank_search_distinguishes_no_results() -> None:
    results = search_question_bank(SearchRequest(query="圆锥曲线", grade=5))
    assert results == []


def test_search_api_validates_query_and_returns_source_metadata() -> None:
    found = client.post("/api/demo/problems/search", json={
        "query": "正面图 遮挡",
        "grade": 5,
        "limit": 3,
    })
    blank = client.post("/api/demo/problems/search", json={"query": "   "})
    assert found.status_code == 200
    assert found.json()[0]["problem"]["revision_id"].startswith("cube-view-")
    assert found.json()[0]["matched_fields"]
    assert blank.status_code == 422


def test_seed_geometry_matches_claimed_projection_invariants() -> None:
    top_practice = build_lesson_plan(LessonBrief(starting_problem_id="cube-view-004"))
    left_practice = build_lesson_plan(LessonBrief(starting_problem_id="cube-view-005"))
    layer_count = build_lesson_plan(LessonBrief(starting_problem_id="cube-view-007"))

    assert len(top_practice.stages[0].cubes) == 5
    assert len(top_practice.stages[0].projections[ViewName.TOP]) == 4
    assert len(left_practice.stages[0].projections[ViewName.LEFT]) == 4
    assert sum(cell.depth > 1 for cell in left_practice.stages[0].projections[ViewName.LEFT]) == 1
    assert len(layer_count.stages[0].cubes) == 6
    assert sorted(cell.depth for cell in layer_count.stages[0].projections[ViewName.TOP]) == [1, 2, 3]


def test_seed_ids_relations_and_metadata_are_consistent() -> None:
    problems = list_demo_problems(topic="观察物体（三）")
    ids = [problem.id for problem in problems]
    revisions = [problem.revision_id for problem in problems]
    assert len(ids) == len(set(ids)) == 8
    assert len(revisions) == len(set(revisions)) == 8
    assert all(problem.grade == 5 for problem in problems)
    assert all(problem.concepts and problem.methods and problem.tags for problem in problems)
    plan = build_lesson_plan(LessonBrief(starting_problem_id="cube-view-001"))
    assert plan.related_problems[0].problem.id == "cube-view-002"


def test_each_topic_starts_with_featured_problem_then_increases_difficulty() -> None:
    difficulty_order = {"基础": 0, "进阶": 1, "挑战": 2}
    catalog = get_curriculum(5)
    for unit in catalog.units:
        problems = list_demo_problems(grade=5, topic=unit.name)
        assert problems[0].is_featured is True
        assert problems[0].difficulty == "基础"
        remaining_levels = [difficulty_order[problem.difficulty] for problem in problems[1:]]
        assert remaining_levels == sorted(remaining_levels)


def test_open_question_titles_are_short_content_names() -> None:
    open_questions = [
        problem for problem in list_demo_problems()
        if problem.content_kind == "开放数据题"
    ]
    assert len(open_questions) == 100
    assert all(len(problem.title) == 4 for problem in open_questions)
    assert all("开放题库" not in problem.title for problem in open_questions)


def test_open_question_titles_follow_their_actual_topic() -> None:
    expected = {
        "cmath-g5-010": ("5b-2", "车辆分组"),
        "cmath-g5-018": ("5a-7", "间隔计数"),
        "cmath-g5-021": ("5a-5", "鸡兔同笼"),
        "cmath-g5-022": ("5a-5", "果树倍数"),
        "cmath-g5-038": ("5b-3", "容积计算"),
        "cmath-g5-049": ("5b-3", "展开表面"),
        "cmath-g5-065": ("5a-7", "线杆间隔"),
        "cmath-g5-079": ("5a-3", "租船计费"),
        "cmath-g5-089": ("5a-3", "排版计数"),
    }
    for problem_id, (unit_id, title) in expected.items():
        problem = get_problem_source(problem_id)
        assert (problem["unit_id"], problem["title"]) == (unit_id, title)


def test_related_section_uses_distinct_titles_from_the_same_topic() -> None:
    plan = build_lesson_plan(LessonBrief(
        topic="简易方程",
        starting_problem_id="cmath-g5-030",
    ))
    related = plan.related_problems[:3]
    assert all(item.problem.topic == plan.selected_problem.topic for item in related)
    assert [item.problem.title for item in related[:2]] == ["年龄关系", "年龄倍数"]
    assert len({item.problem.title for item in related}) == len(related)


def test_explicit_search_query_is_preserved_in_rag_trace() -> None:
    plan = build_lesson_plan(LessonBrief(
        starting_problem_id="cube-view-004",
        search_query="上视图 高度",
    ))
    assert plan.retrieval.query == "上视图 高度"
    assert plan.retrieval.context[0].problem_id == "cube-view-004"
    assert all(item.revision_id for item in plan.retrieval.context)


def test_problem_api_filters_one_curriculum_folder() -> None:
    response = client.get("/api/demo/problems", params={
        "grade": 5,
        "topic": "因数与倍数",
    })
    assert response.status_code == 200
    assert len(response.json()) >= 5
    assert {item["unit_id"] for item in response.json()} == {"5b-2"}


def test_non_spatial_problem_builds_text_lesson_without_cube_tool() -> None:
    plan = build_lesson_plan(LessonBrief(
        topic="可能性",
        starting_problem_id="topic-seed-007",
    ))
    assert plan.selected_problem.unit_id == "5a-4"
    assert plan.selected_problem.has_interactive_model is False
    assert all(stage.cubes == [] for stage in plan.stages)
    assert all(stage.projections[view] == [] for stage in plan.stages for view in ViewName)
    assert {resource.kind for resource in plan.resources} == {"board_plan", "variation"}


def test_curriculum_api_marks_unavailable_grades_explicitly() -> None:
    available = client.get("/api/demo/curriculum", params={"grade": 5})
    unavailable = client.get("/api/demo/curriculum", params={"grade": 4})
    assert available.status_code == 200
    assert len(available.json()["units"]) == 15
    assert unavailable.json() == {
        "grade": 4,
        "edition": "人教版单元框架",
        "available": False,
        "units": [],
    }
