from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.models import (
    ChatMessage,
    CreateDraftRequest,
    CreateFeedbackRequest,
    FeedbackObservation,
    DraftItemUpdate,
    LessonBrief,
    PhotoSearchRequest,
    ProblemAnalysis,
    ReviewDraftRequest,
    UpdateDraftRequest,
    UpdateFeedbackRequest,
)
from app.model_gateway import analyze_problem, answer_teacher
from app.service import build_lesson_plan
from app.storage import AppStore, VersionConflictError
from app.workspace import (
    clear_store_cache,
    create_draft,
    create_feedback,
    delete_photo,
    export_draft_markdown,
    export_feedback_markdown,
    save_photo,
    search_from_photo,
    update_draft,
    update_feedback,
    update_photo_transcript,
)

client = TestClient(app)


def sample_analysis() -> ProblemAnalysis:
    return ProblemAnalysis(
        scope_note="本题只覆盖固定方向观察和遮挡判断，不代表完整专题。",
        knowledge_points=["三视图", "遮挡"],
        knowledge_evidence=[{
            "knowledge_point": "遮挡",
            "evidence": "题目要求从正面判断组合体轮廓。",
            "source_ids": ["cube-view-001"],
        }],
        problem_type="观察物体",
        core_method="固定观察方向，把同一视线上的方块合并为一个轮廓格。",
        prerequisites=["认识正面、左面和上面"],
        skill_plans=[{
            "skill": "固定观察方向",
            "observable_behavior": "能在不转动题目的情况下指出正面轮廓。",
            "teaching_activity": "先预测，再固定正面观察模型并核对。",
            "success_criterion": "能独立解释每个轮廓格的来源。",
        }],
        difficulty_reasons=["容易把深度误当成宽度"],
        common_mistakes=["转动题目而没有固定观察方向"],
        teaching_objective="能说明每个轮廓格来自哪一列方块。",
        opening_question="先不计算，你认为正面能看到几列？为什么？",
        scaffolding_questions=["先固定哪个方向？", "被挡住的方块还画吗？"],
        variation_idea="保持正面轮廓不变，移动后排一个方块。",
        teacher_confirmations=["确认学生是否已经认识三个观察方向。"],
        review_warning="模型建议需教师核对图形方向。",
    )


def test_draft_persists_reorders_reviews_and_exports(tmp_path) -> None:
    store = AppStore(tmp_path)
    draft = create_draft(CreateDraftRequest(
        starting_problem_id="cube-view-001",
        related_problem_ids=["cube-view-002"],
    ), store)
    assert draft.version == 1
    assert [item.problem.id for item in draft.items] == ["cube-view-001", "cube-view-002"]

    items = [
        DraftItemUpdate(
            id=item.id,
            problem_id=item.problem.id,
            problem_revision_id=item.problem_revision_id,
            relation=item.relation,
            teacher_prompt=f"追问：{item.teacher_prompt}",
            teaching_note=item.teaching_note,
        )
        for item in reversed(draft.items)
    ]
    updated = update_draft(draft.id, UpdateDraftRequest(
        expected_version=draft.version,
        title="观察物体复习课",
        teacher_note="先让学生摆一摆。",
        items=items,
    ), store)
    assert updated.version == 2
    assert [item.problem.id for item in updated.items] == ["cube-view-002", "cube-view-001"]
    approved = store.review_draft(
        draft_id=draft.id,
        expected_version=updated.version,
        status="approved",
    )
    assert approved["status"] == "approved"
    assert AppStore(tmp_path).get_draft(draft.id)["title"] == "观察物体复习课"

    teacher = export_draft_markdown(updated, "teacher")
    student = export_draft_markdown(updated, "student")
    assert "参考答案" in teacher
    assert "参考答案" not in student
    assert "先让学生摆一摆" in teacher


def test_draft_preserves_generated_plan_snapshot(tmp_path) -> None:
    store = AppStore(tmp_path)
    plan = build_lesson_plan(LessonBrief(starting_problem_id="cube-view-001"))
    draft = create_draft(CreateDraftRequest(
        starting_problem_id=plan.selected_problem.id,
        related_problem_ids=[plan.related_problems[0].problem.id],
        plan_snapshot=plan,
    ), store)
    assert draft.plan_snapshot is not None
    assert draft.plan_snapshot.retrieval.context[0].problem_id == "cube-view-001"
    assert "第一步" in draft.items[0].teaching_note


def test_draft_rejects_stale_version(tmp_path) -> None:
    store = AppStore(tmp_path)
    draft = create_draft(CreateDraftRequest(starting_problem_id="cube-view-001"), store)
    item = draft.items[0]
    request = UpdateDraftRequest(
        expected_version=99,
        title=draft.title,
        items=[DraftItemUpdate(
            id=item.id,
            problem_id=item.problem.id,
            problem_revision_id=item.problem_revision_id,
            relation=item.relation,
            teacher_prompt=item.teacher_prompt,
            teaching_note=item.teaching_note,
        )],
    )
    try:
        update_draft(draft.id, request, store)
    except VersionConflictError:
        pass
    else:
        raise AssertionError("expected optimistic-lock conflict")


def test_photo_is_reencoded_transcribed_searched_and_deleted(tmp_path) -> None:
    store = AppStore(tmp_path)
    original = BytesIO()
    Image.new("RGB", (96, 80), "white").save(original, format="JPEG", quality=90)
    photo = save_photo(
        filename="../../一道题.jpg",
        content_type="image/jpeg",
        raw=original.getvalue(),
        store=store,
    )
    stored_name = store.get_photo(photo.id)["stored_name"]
    saved = store.safe_child("uploads", stored_name)
    assert saved.exists()
    assert Image.open(saved).format == "PNG"
    assert photo.original_name == "一道题.jpg"

    update_photo_transcript(photo.id, "从正面观察小正方体 遮挡", store)
    results = search_from_photo(photo.id, PhotoSearchRequest(grade=5), store)
    assert results
    delete_photo(photo.id, store)
    assert not saved.exists()


def test_private_store_rejects_path_escape(tmp_path) -> None:
    store = AppStore(tmp_path / "private")
    try:
        store.safe_child("..", "outside.png")
    except ValueError:
        pass
    else:
        raise AssertionError("expected path boundary rejection")


def test_store_migration_is_safe_during_concurrent_first_access(tmp_path) -> None:
    root = tmp_path / "shared"
    with ThreadPoolExecutor(max_workers=4) as executor:
        stores = list(executor.map(lambda _: AppStore(root), range(4)))
    assert all(store.list_feedback() == [] for store in stores)


def test_ai_graph_uses_validated_analysis(monkeypatch) -> None:
    captured_context = []

    def fake_analysis(_source, context):
        captured_context.extend(context)
        return sample_analysis()

    monkeypatch.setattr("app.workflow.analyze_problem", fake_analysis)
    plan = build_lesson_plan(LessonBrief(), use_model=True)
    assert plan.model_analysis is not None
    assert plan.model_analysis.problem_type == "观察物体"
    assert "analyze_problem:completed" in plan.workflow.trace
    assert "能说明每个轮廓格" in plan.stages[1].purpose
    assert "保持正面轮廓" in plan.stages[2].teaching_note
    assert "先预测" in plan.stages[1].teaching_note
    assert captured_context[0]["problem_id"] == "cube-view-001"


class FakeAnalysisResponse:
    output_text = sample_analysis().model_dump_json()


class FakeTextResponse:
    output_text = "先让学生说出观察方向，再逐列核对轮廓。"


class FakeResponses:
    def create(self, **kwargs):
        assert kwargs["store"] is False
        if "text" in kwargs:
            assert kwargs["text"]["format"]["type"] == "json_schema"
            return FakeAnalysisResponse()
        assert kwargs["input"][-1]["content"] == "这道题先问什么？"
        return FakeTextResponse()


class FakeOpenAI:
    responses = FakeResponses()


def test_model_gateway_parses_analysis_and_answers_without_remote_state() -> None:
    from app.catalog import get_problem_source

    source = get_problem_source("cube-view-001")
    analysis = analyze_problem(
        source,
        [{"problem_id": "cube-view-001", "excerpt": "题目资料"}],
        FakeOpenAI(),
    )
    response = answer_teacher(
        source,
        message="这道题先问什么？",
        history=[ChatMessage(role="assistant", content="我们先读题。")],
        analysis=analysis,
        client=FakeOpenAI(),
    )
    assert analysis.knowledge_points == ["三视图", "遮挡"]
    assert "观察方向" in response.answer


def test_ai_endpoint_is_explicit_when_key_is_missing(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    status = client.get("/api/ai/status")
    plan = client.post("/api/ai/lesson-plan", json={"problem_id": "cube-view-001"})
    assert status.status_code == 200
    assert status.json()["configured"] is False
    assert plan.status_code == 503
    assert plan.json()["detail"]["code"] == "model_not_configured"


def test_draft_api_round_trip_and_exports(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("YIDUO_PRIVATE_DIR", str(tmp_path))
    clear_store_cache()
    try:
        created = client.post("/api/drafts", json={
            "starting_problem_id": "topic-seed-007",
            "related_problem_ids": [],
        })
        assert created.status_code == 201
        draft = created.json()
        draft["title"] = "可能性试讲"
        draft["items"][0]["teacher_prompt"] = "哪一种结果更容易出现？说出理由。"
        updated = client.put(f"/api/drafts/{draft['id']}", json={
            "expected_version": draft["version"],
            "title": draft["title"],
            "teacher_note": "记录学生的不同猜想。",
            "items": [{
                "id": item["id"],
                "problem_id": item["problem"]["id"],
                "problem_revision_id": item["problem_revision_id"],
                "relation": item["relation"],
                "teacher_prompt": item["teacher_prompt"],
                "teaching_note": item["teaching_note"],
            } for item in draft["items"]],
        })
        assert updated.status_code == 200
        assert updated.json()["version"] == 2
        approved = client.put(f"/api/drafts/{draft['id']}/review", json={
            "expected_version": 2,
            "status": "approved",
        })
        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"
        student = client.get(f"/api/drafts/{draft['id']}/export", params={"audience": "student"})
        assert student.status_code == 200
        assert "参考答案" not in student.text
    finally:
        clear_store_cache()


def test_feedback_guides_facts_persists_and_separates_class_report(tmp_path) -> None:
    store = AppStore(tmp_path)
    request = CreateFeedbackRequest(
        student_name="示例学生甲",
        grade=5,
        topic="多角度观察物体",
        lesson_date="2026-09-20",
        actual_content="从正面、左面和上面观察组合体，并根据三视图还原图形。",
        observations=[FeedbackObservation(
            skill_area="固定观察方向",
            task_evidence="在第2题中先预测正面轮廓，再摆方块核对。",
            performance="prompted",
            correction_result="提醒固定正面后能够改正并说明原因。",
        )],
        teacher_advice="继续练习先标观察方向再画方格图。",
        homework=["复习课堂笔记", "完成上分攻略P1—3"],
        class_reminder="画图前先确认观察方向。",
    )
    feedback = create_feedback(request, store)
    assert feedback.version == 1
    assert "提示后完成" in feedback.individual_report
    assert "示例学生甲" not in feedback.class_group_report
    assert "固定观察方向" not in feedback.class_group_report
    assert "画图前先确认观察方向" in feedback.class_group_report

    updated_payload = {
        **request.model_dump(),
        "teacher_advice": "继续练习，并在完成后口述每一格的来源。",
    }
    updated = update_feedback(
        feedback.id,
        UpdateFeedbackRequest(expected_version=feedback.version, **updated_payload),
        store,
    )
    assert updated.version == 2
    assert "口述每一格" in updated.individual_report
    assert "示例学生甲" in export_feedback_markdown(updated, "individual")
