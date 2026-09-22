from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ai_budget import allowance
from app.adjustment import AdjustmentRequest, AdjustmentProposal, generate_proposal, validate_source
from app.model_gateway import ModelProviderError
from app.models import LessonBrief, CreateDraftRequest
from app.service import build_lesson_plan
from app.storage import AppStore
from app.workspace import create_draft, export_draft_markdown


def proposal():
    return AdjustmentProposal(
        rationale="先观察固定点，再区分方向。",
        objective="能根据固定点和运动方向解释判断。",
        steps=[
            {"teacher_question": "哪个点不动？", "student_action": "标出固定点。", "checkpoint": "能解释固定点的依据。"},
            {"teacher_question": "方向改变后哪里不同？", "student_action": "比较两种运动方向。", "checkpoint": "能用语言区分方向。"},
        ],
        teacher_check="请教师核对图形与观察方向。",
    )


@pytest.fixture
def request_data():
    plan = build_lesson_plan(LessonBrief())
    stage = plan.stages[1]
    return {
        "problem_id": plan.selected_problem.id,
        "revision_id": plan.selected_problem.revision_id,
        "stage_id": stage.id, "goal": "confusion", "method": "hands_on",
        "note": "", "current": {
            "purpose": stage.purpose, "teacher_prompt": "老师已经编辑的追问",
            "teaching_note": stage.teaching_note, "teaching_steps": [],
        },
    }


@pytest.fixture(autouse=True)
def local_only(monkeypatch, tmp_path):
    monkeypatch.setenv("YIDUO_PRIVATE_DIR", str(tmp_path))
    monkeypatch.setenv("YIDUO_AI_DAILY_LIMIT", "3")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-key")
    def no_network():
        pytest.fail("Tests must never call the live provider")
    monkeypatch.setattr("app.adjustment._client", no_network)


def test_guided_request_needs_no_free_text_and_preserves_input(monkeypatch, request_data):
    captured = []
    before = deepcopy(request_data)
    def generate(request, source, context):
        captured.append((request, context))
        return proposal()
    monkeypatch.setattr("app.adjustment.generate_proposal", generate)
    client = TestClient(app)
    response = client.post("/api/ai/adjust-stage", json=request_data)
    assert response.status_code == 200
    assert response.json()["stage_id"] == "understand-method"
    assert response.json()["proposal"]["steps"][0]["teacher_question"] == "哪个点不动？"
    assert captured[0][0].current.teacher_prompt == "老师已经编辑的追问"
    assert captured[0][1]
    assert request_data == before
    assert allowance()["used"] == 1


@pytest.mark.parametrize("change,status", [
    ({"goal": "invalid"}, 422),
    ({"goal": "custom", "note": "   "}, 422),
    ({"stage_id": "nonexistent-stage"}, 422),
    ({"revision_id": "outdated"}, 409),
    ({"note": "x" * 1001}, 422),
])
def test_invalid_request_rejected_without_charge(request_data, change, status):
    response = TestClient(app).post("/api/ai/adjust-stage", json={**request_data, **change})
    assert response.status_code == status
    assert allowance()["used"] == 0


def test_zero_budget_blocks_adjustment(monkeypatch, request_data):
    monkeypatch.setenv("YIDUO_AI_DAILY_LIMIT", "0")
    assert TestClient(app).post("/api/ai/adjust-stage", json=request_data).status_code == 429


def test_provider_failure_returns_no_replacement(monkeypatch, request_data):
    def failed(*args):
        raise ModelProviderError("test failure")
    monkeypatch.setattr("app.adjustment.generate_proposal", failed)
    response = TestClient(app).post("/api/ai/adjust-stage", json=request_data)
    assert response.status_code == 502
    assert "proposal" not in response.json()
    assert allowance()["used"] == 1


def test_prompt_carries_selection_current_text_and_schema(request_data):
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(output_text=proposal().model_dump_json())
    request = AdjustmentRequest.model_validate(request_data)
    result = generate_proposal(request, validate_source(request), [],
        SimpleNamespace(responses=SimpleNamespace(create=create)))
    assert len(calls) == 1
    assert "老师已经编辑的追问" in calls[0]["input"]
    assert "动手操作" in calls[0]["input"]
    assert "正反对比" in calls[0]["input"]
    assert calls[0]["text"]["format"]["type"] == "json_schema"
    assert result == proposal()


@pytest.mark.parametrize("output", ["", "not json", '{"steps":[]}', proposal().model_dump_json().replace("哪个点不动？", "   ")])
def test_malformed_model_output_is_rejected(request_data, output):
    request = AdjustmentRequest.model_validate(request_data)
    fake = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: SimpleNamespace(output_text=output)))
    with pytest.raises(ModelProviderError):
        generate_proposal(request, validate_source(request), [], fake)


def test_structured_steps_persist_and_export(tmp_path):
    plan = build_lesson_plan(LessonBrief())
    original_first = plan.stages[0].model_dump()
    suggested = proposal()
    plan.stages[1].teaching_steps = suggested.steps
    plan.stages[1].teacher_prompt = suggested.steps[0].teacher_question
    plan.stages[1].teaching_note = suggested.steps[0].student_action + suggested.steps[0].checkpoint
    draft = create_draft(CreateDraftRequest(
        starting_problem_id=plan.selected_problem.id, plan_snapshot=plan
    ), AppStore(tmp_path))
    assert draft.plan_snapshot.stages[0].model_dump() == original_first
    assert draft.plan_snapshot.stages[1].teaching_steps == suggested.steps
    assert "标出固定点" in export_draft_markdown(draft, "teacher")
