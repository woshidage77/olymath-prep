import json
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import feedback_ai as ai
from app.storage import AppStore, VersionConflictError
from app.workspace import clear_store_cache, create_feedback, update_feedback, get_feedback, export_feedback_markdown
from app.models import CreateFeedbackRequest, UpdateFeedbackRequest
from app.model_gateway import ModelProviderError

client = TestClient(app)


@pytest.fixture
def source():
    return dict(student_name="测试学生", grade=5, topic="观察物体", lesson_date="2026-09-22",
        actual_content="练习观察三个方向的轮廓。学习画方格图。",
        observations=[dict(skill_area="固定方向", task_evidence="提醒后画出了正面轮廓",
            performance="prompted", correction_result="按照提示修改方向")],
        teacher_advice="画图前先标出观察方向", homework=["练习册 P1～3", "复习课堂笔记"],
        class_reminder="请勿将私人表现用于群发", photo_ids=[])


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("YIDUO_PRIVATE_DIR", str(tmp_path))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-test-key")
    monkeypatch.setenv("YIDUO_AI_DAILY_LIMIT", "20")
    monkeypatch.setattr(ai, "_client", lambda: pytest.fail("real model call forbidden"))
    clear_store_cache()
    yield
    clear_store_cache()


def ready(evidence):
    return ai.PolishResult(status="ready", questions_for_teacher=[], paragraphs=[
        ai.Paragraph(evidence_id=key, text=(
            "在老师提醒下画出轮廓，并按提示修正了方向。" if key.startswith("observation-")
            else "建议先标出观察方向再画图。" if key == "advice"
            else value + "。"
        )) for key, value in evidence.items()
    ])


def fake_generate(raw, request):
    evidence = ai.evidence_for(raw, request.audience)
    result = ready(evidence)
    ai.validate_result(result, evidence)
    return result, evidence


def test_input_separation_and_known_name_redaction(source):
    source["actual_content"] += "测试学生参加了观察活动。"
    group = ai.evidence_for(source, "class_group")
    assert all(key.startswith("content-") for key in group)
    encoded = json.dumps(group, ensure_ascii=False)
    assert "测试学生" not in encoded
    assert "提醒后画出了" not in encoded
    assert "P1" not in encoded
    individual = ai.evidence_for(source, "individual")
    assert "prompted" in individual["observation-0"]
    source["observations"][0]["performance"] = "not_observed"
    assert "observation-0" not in ai.evidence_for(source, "individual")


def test_gateway_contract(source):
    evidence = ai.evidence_for(source, "individual")
    calls = []
    def respond(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(output_text=ready(evidence).model_dump_json())
    request = ai.PolishRequest(expected_version=1, audience="individual", consent=True)
    result, _ = ai.generate(source, request, SimpleNamespace(responses=SimpleNamespace(create=respond)))
    assert result.status == "ready"
    assert len(calls) == 1 and calls[0]["store"] is False
    assert calls[0]["text"]["format"]["type"] == "json_schema"
    assert source["student_name"] not in calls[0]["input"]
    assert source["homework"][0] not in calls[0]["input"]


@pytest.mark.parametrize("text", ["正确率提升明显。", "独立完成所有题目。", "已发送给家长。", "得到了100分。", " ", "【课后作业】随便写"])
def test_invalid_claims_rejected(text):
    result = ai.PolishResult(status="ready", questions_for_teacher=[], paragraphs=[
        ai.Paragraph(evidence_id="content-0", text=text)])
    with pytest.raises(ValueError):
        ai.validate_result(result, {"content-0": "学习画图"})


def test_unknown_duplicate_or_missing_evidence_rejected():
    for ids in [["unknown"], ["content-0", "content-0"], ["content-0"]]:
        result = ai.PolishResult(status="ready", questions_for_teacher=[], paragraphs=[
            ai.Paragraph(evidence_id=key, text="学习画图。") for key in ids])
        with pytest.raises(ValueError):
            ai.validate_result(result, {"content-0": "学习画图", "content-1": "学习观察"})


def test_roundtrip_adopt_export_restore_and_edit_invalidation(source, monkeypatch):
    monkeypatch.setattr(ai, "generate", fake_generate)
    created = client.post("/api/feedback", json=source).json()
    route = f"/api/feedback/{created['id']}/polish"
    response = client.post(route, json=dict(expected_version=1, audience="individual", consent=True))
    assert response.status_code == 200, response.text
    proposal = response.json()
    unchanged = client.get(f"/api/feedback/{created['id']}").json()
    assert unchanged["version"] == 1 and unchanged["ai_audiences"] == []
    adopt = client.put(route, json=dict(expected_version=1, audience="individual", proposal_id=proposal["proposal_id"], reviewed=True))
    assert adopt.status_code == 200, adopt.text
    saved = adopt.json()
    assert saved["version"] == 2 and saved["status"] == "draft"
    assert saved["ai_audiences"] == ["individual"]
    assert "提示后完成" in saved["individual_report"]
    assert "P1～3" in saved["individual_report"]
    loaded = client.get(f"/api/feedback/{created['id']}").json()
    assert loaded["individual_report"] == saved["individual_report"]
    export = client.get(f"/api/feedback/{created['id']}/export?audience=individual")
    assert "提示后完成" in export.text and "P1～3" in export.text
    # Stored ordinary report remains available for comparison.
    assert loaded["ordinary_individual_report"] == created["individual_report"]
    assert client.put(route, json=dict(expected_version=2, audience="individual", proposal_id=proposal["proposal_id"], reviewed=True)).status_code == 409
    reset = client.put(route, json=dict(expected_version=2, audience="individual", proposal_id=None)).json()
    assert reset["ai_audiences"] == [] and reset["individual_report"] == created["individual_report"]
    p2 = client.post(route, json=dict(expected_version=3, audience="class_group", consent=True, group_content_confirmed=True)).json()
    accepted = client.put(route, json=dict(expected_version=3, audience="class_group", proposal_id=p2["proposal_id"], reviewed=True)).json()
    assert "测试学生" not in accepted["class_group_report"] and "已发送" not in accepted["class_group_report"]
    edited = client.put(f"/api/feedback/{created['id']}", json={**source, "expected_version":4, "teacher_advice":"先标方向，再画图并解释依据"}).json()
    assert edited["ai_audiences"] == [] and edited["version"] == 5


def test_stale_inputs_and_consent_rejected_before_model(source, monkeypatch):
    record = client.post("/api/feedback", json=source).json()
    route = f"/api/feedback/{record['id']}/polish"
    assert client.post(route, json=dict(expected_version=2, audience="individual", consent=True)).status_code == 409
    assert client.post(route, json=dict(expected_version=1, audience="individual", consent=False)).status_code == 422
    assert client.post(route, json=dict(expected_version=1, audience="class_group", consent=True)).status_code == 422
    assert client.get("/api/ai/status").json()["used"] == 0


def test_provider_error_retains_original_and_counts_once(source, monkeypatch):
    record = client.post("/api/feedback", json=source).json()
    def fail(*args): raise ModelProviderError("test failure")
    monkeypatch.setattr(ai, "generate", fail)
    response = client.post(f"/api/feedback/{record['id']}/polish", json=dict(expected_version=1, audience="individual", consent=True))
    assert response.status_code == 502
    current = client.get(f"/api/feedback/{record['id']}").json()
    assert current["version"] == 1 and current["ai_audiences"] == []
    assert client.get("/api/ai/status").json()["used"] == 1


def test_needs_input_returns_questions_without_proposal(source, monkeypatch):
    def needs(raw, request):
        return ai.PolishResult(status="needs_input", paragraphs=[], questions_for_teacher=["请确认本项是否需要提示。"]), ai.evidence_for(raw, request.audience)
    monkeypatch.setattr(ai, "generate", needs)
    record = client.post("/api/feedback", json=source).json()
    result = client.post(f"/api/feedback/{record['id']}/polish", json=dict(expected_version=1, audience="individual", consent=True)).json()
    assert result["status"] == "needs_input" and result["proposal_id"] is None and result["report"] == ""


def test_cross_record_proposal_cannot_be_adopted(source, monkeypatch):
    monkeypatch.setattr(ai, "generate", fake_generate)
    first = client.post("/api/feedback", json=source).json()
    second = client.post("/api/feedback", json=source).json()
    result = client.post(f"/api/feedback/{first['id']}/polish", json=dict(expected_version=1, audience="individual", consent=True)).json()
    assert client.put(f"/api/feedback/{second['id']}/polish", json=dict(expected_version=1, audience="individual", proposal_id=result["proposal_id"], reviewed=True)).status_code == 404


def test_generation_race_is_rejected(source, tmp_path):
    store = AppStore(tmp_path)
    record = create_feedback(CreateFeedbackRequest(**source), store)
    update_feedback(record.id, UpdateFeedbackRequest(**source, expected_version=1), store)
    with pytest.raises(VersionConflictError):
        store.save_feedback_proposal(record.id, 1, "individual", {})


def test_migration_idempotent_and_delete_cascades(source, tmp_path):
    store = AppStore(tmp_path)
    record = create_feedback(CreateFeedbackRequest(**source), store)
    store.save_feedback_proposal(record.id, 1, "individual", {})
    store = AppStore(tmp_path)
    store.delete_feedback(record.id)
    with store.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM feedback_ai_proposals").fetchone()[0] == 0


def test_quota_zero_prevents_generation(source, monkeypatch):
    monkeypatch.setenv("YIDUO_AI_DAILY_LIMIT", "0")
    record = client.post("/api/feedback", json=source).json()
    assert client.post(f"/api/feedback/{record['id']}/polish", json=dict(expected_version=1, audience="individual", consent=True)).status_code == 429


@pytest.mark.parametrize("output", ["not json", "", '{"status":"ready","paragraphs":[],"questions_for_teacher":[]}'])
def test_bad_model_output_is_explicit_error(source, output):
    stub = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: SimpleNamespace(output_text=output)))
    with pytest.raises(ModelProviderError):
        ai.generate(source, ai.PolishRequest(expected_version=1, audience="individual", consent=True), stub)


def test_all_unobserved_requires_input_before_charge(source):
    source["observations"][0]["performance"] = "not_observed"
    record = client.post("/api/feedback", json=source).json()
    response = client.post(f"/api/feedback/{record['id']}/polish", json=dict(expected_version=1, audience="individual", consent=True))
    assert response.status_code == 422
    assert client.get("/api/ai/status").json()["used"] == 0


def test_adopt_requires_review_and_preserves_photos(source, monkeypatch):
    monkeypatch.setattr(ai, "generate", fake_generate)
    record = client.post("/api/feedback", json=source).json()
    route = f"/api/feedback/{record['id']}/polish"
    proposal = client.post(route, json=dict(expected_version=1, audience="individual", consent=True)).json()
    assert client.put(route, json=dict(expected_version=1, audience="individual", proposal_id=proposal["proposal_id"])).status_code == 422
    evidence = ai.evidence_for(source, "individual")
    report = ai.render_polish({**source, "photo_names":["课堂作业.png"]}, "individual", ready(evidence).model_dump())
    assert "课堂作业.png" in report and source["homework"][0] in report
