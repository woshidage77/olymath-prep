from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.ai_budget import allowance, BudgetExceededError
from app.main import app


@pytest.fixture(autouse=True)
def isolated_budget(monkeypatch, tmp_path):
    monkeypatch.setenv("YIDUO_PRIVATE_DIR", str(tmp_path))
    monkeypatch.setenv("YIDUO_AI_DAILY_LIMIT", "2")


def test_persistent_budget_and_concurrent_limit():
    assert allowance()["remaining"] == 2

    def attempt(_):
        try:
            allowance(consume=True)
            return True
        except BudgetExceededError:
            return False

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(attempt, range(10)))
    assert sum(results) == 2
    assert allowance() == {"daily_limit": 2, "used": 2, "remaining": 0}


def test_zero_budget_blocks_ai_but_allows_basic(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-test-key")
    monkeypatch.setenv("YIDUO_AI_DAILY_LIMIT", "0")
    def forbidden(*args, **kwargs):
        pytest.fail("No paid request should be sent")
    monkeypatch.setattr("app.workflow.analyze_problem", forbidden)
    monkeypatch.setattr("app.main.answer_teacher", forbidden)
    client = TestClient(app)
    assert client.post("/api/demo/lesson-plan", json={"starting_problem_id": "cube-view-001"}).status_code == 200
    assert client.post("/api/ai/lesson-plan", json={"problem_id": "cube-view-001"}).status_code == 429
    assert client.post("/api/ai/chat", json={"problem_id": "cube-view-001", "message": "test"}).status_code == 429


def test_requirement_reaches_graph_and_failure_counts(monkeypatch):
    from app.model_gateway import ModelProviderError
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-test-key")
    captured = []
    def failed(source, context, teacher_request=""):
        captured.append(teacher_request)
        raise ModelProviderError("test failure")
    monkeypatch.setattr("app.workflow.analyze_problem", failed)
    client = TestClient(app)
    response = client.post("/api/ai/lesson-plan", json={
        "problem_id": "cube-view-001", "teacher_request": "simplify steps"
    })
    assert response.status_code == 502
    assert captured == ["simplify steps"]
    assert allowance()["remaining"] == 1
    assert client.post("/api/ai/lesson-plan", json={
        "problem_id": "cube-view-001", "teacher_request": "a" * 1001
    }).status_code == 422
    assert allowance()["remaining"] == 1
