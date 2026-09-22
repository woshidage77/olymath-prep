from urllib.parse import quote

from fastapi import FastAPI, File, HTTPException, Query, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .catalog import get_curriculum, get_problem_source
from .ai_budget import allowance, BudgetExceededError
from .adjustment import AdjustmentRequest, AdjustmentResponse, StaleAdjustmentError, validate_source, build_adjustment
from .feedback_ai import PolishRequest, PolishResponse, AdoptPolishRequest, check_version, propose
from .workspace import get_store
from .config import model_settings
from .model_gateway import (
    ModelNotConfiguredError,
    ModelProviderError,
    answer_teacher,
    model_status,
)
from .models import (
    AIPlanRequest,
    AfterClassFeedback,
    CreateFeedbackRequest,
    CreateDraftRequest,
    CurriculumCatalog,
    FeedbackSummary,
    LessonBrief,
    LessonDraft,
    LessonDraftSummary,
    LessonPlan,
    ModelStatus,
    PhotoRecord,
    PhotoSearchRequest,
    ProblemSummary,
    ReviewDraftRequest,
    ReviewFeedbackRequest,
    SearchRequest,
    SearchResult,
    TeacherChatRequest,
    TeacherChatResponse,
    UpdateDraftRequest,
    UpdateFeedbackRequest,
    UpdateTranscriptRequest,
)
from .retrieval import search_question_bank
from .service import (
    ProblemNotFoundError,
    WorkflowExecutionError,
    build_lesson_plan,
    list_demo_problems,
)
from .storage import RecordNotFoundError, VersionConflictError
from .workspace import (
    MAX_UPLOAD_BYTES,
    InvalidUploadError,
    PhotoInUseError,
    StaleProblemRevisionError,
    create_feedback,
    create_draft,
    delete_feedback,
    delete_draft,
    delete_photo,
    export_draft_markdown,
    export_feedback_markdown,
    get_feedback,
    get_draft,
    list_feedback,
    list_drafts,
    list_photos,
    photo_content_path,
    review_draft,
    review_feedback,
    save_photo,
    search_from_photo,
    update_draft,
    update_feedback,
    update_photo_transcript,
)

app = FastAPI(
    title="一朵教学 API",
    description="Question-driven lesson preparation with editable drafts and optional AI assistance.",
    version="0.4.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)


def reserve_ai_attempt() -> None:
    if not model_settings().configured:
        raise HTTPException(status_code=503, detail={"code": "model_not_configured"})
    try:
        allowance(consume=True)
    except BudgetExceededError as error:
        raise HTTPException(status_code=429, detail=str(error)) from error


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "demo"}


@app.get("/api/ai/status", response_model=ModelStatus)
def get_model_status() -> ModelStatus:
    return model_status()


@app.post("/api/ai/lesson-plan", response_model=LessonPlan)
def create_ai_lesson_plan(request: AIPlanRequest) -> LessonPlan:
    source = _problem_source_or_404(request.problem_id)
    brief = LessonBrief(
        grade=source["grade"],
        topic=source["topic"],
        starting_problem_id=source["id"],
        search_query=request.search_query,
    )
    try:
        reserve_ai_attempt()
        return build_lesson_plan(brief, use_model=True, teacher_request=request.teacher_request)
    except WorkflowExecutionError as error:
        status_code = 503 if error.code == "model_not_configured" else 502
        raise HTTPException(status_code=status_code, detail={"code": error.code}) from error


@app.post("/api/ai/adjust-stage", response_model=AdjustmentResponse)
def adjust_teaching_stage(request: AdjustmentRequest) -> AdjustmentResponse:
    try:
        source = validate_source(request)
    except ProblemNotFoundError as error:
        raise HTTPException(status_code=404, detail="题目不存在") from error
    except StaleAdjustmentError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    reserve_ai_attempt()
    try:
        return build_adjustment(request, source)
    except (ModelProviderError, ModelNotConfiguredError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.post("/api/ai/chat", response_model=TeacherChatResponse)
def chat_with_teacher(request: TeacherChatRequest) -> TeacherChatResponse:
    source = _problem_source_or_404(request.problem_id)
    try:
        context_plan = build_lesson_plan(LessonBrief(
            grade=source["grade"],
            topic=source["topic"],
            starting_problem_id=source["id"],
        ))
        reserve_ai_attempt()
        return answer_teacher(
            source,
            message=request.message,
            history=request.history,
            analysis=request.analysis,
            retrieval_context=[
                item.model_dump(mode="json") for item in context_plan.retrieval.context
            ],
        )
    except ModelNotConfiguredError as error:
        raise HTTPException(status_code=503, detail={"code": "model_not_configured"}) from error
    except ModelProviderError as error:
        raise HTTPException(status_code=502, detail={"code": "model_provider_error"}) from error


@app.post("/api/demo/lesson-plan", response_model=LessonPlan)
def create_demo_lesson_plan(brief: LessonBrief) -> LessonPlan:
    try:
        return build_lesson_plan(brief)
    except ProblemNotFoundError as error:
        raise HTTPException(status_code=404, detail={"code": "problem_not_found", "problem_id": error.problem_id}) from error
    except WorkflowExecutionError as error:
        raise HTTPException(status_code=500, detail={"code": error.code, "status": error.status}) from error


@app.get("/api/demo/curriculum", response_model=CurriculumCatalog)
def get_demo_curriculum(grade: int = Query(default=5, ge=1, le=12)) -> CurriculumCatalog:
    return get_curriculum(grade)


@app.get("/api/demo/problems", response_model=list[ProblemSummary])
def get_demo_problems(
    grade: int | None = Query(default=None, ge=1, le=12),
    topic: str | None = Query(default=None, min_length=1, max_length=80),
) -> list[ProblemSummary]:
    return list_demo_problems(grade=grade, topic=topic)


@app.post("/api/demo/problems/search", response_model=list[SearchResult])
def search_demo_problems(request: SearchRequest) -> list[SearchResult]:
    return search_question_bank(request)


@app.post("/api/drafts", response_model=LessonDraft, status_code=201)
def create_lesson_draft(request: CreateDraftRequest) -> LessonDraft:
    try:
        return create_draft(request)
    except ProblemNotFoundError as error:
        raise HTTPException(status_code=404, detail={"code": "problem_not_found"}) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail={"code": "invalid_plan_snapshot"}) from error


@app.get("/api/drafts", response_model=list[LessonDraftSummary])
def get_lesson_drafts() -> list[LessonDraftSummary]:
    return list_drafts()


@app.get("/api/drafts/{draft_id}", response_model=LessonDraft)
def get_lesson_draft(draft_id: str) -> LessonDraft:
    try:
        return get_draft(draft_id)
    except RecordNotFoundError as error:
        raise HTTPException(status_code=404, detail={"code": "draft_not_found"}) from error


@app.put("/api/drafts/{draft_id}", response_model=LessonDraft)
def update_lesson_draft(draft_id: str, request: UpdateDraftRequest) -> LessonDraft:
    try:
        return update_draft(draft_id, request)
    except RecordNotFoundError as error:
        raise HTTPException(status_code=404, detail={"code": "draft_not_found"}) from error
    except VersionConflictError as error:
        raise HTTPException(status_code=409, detail={"code": "draft_version_conflict"}) from error
    except StaleProblemRevisionError as error:
        raise HTTPException(status_code=409, detail={"code": "problem_revision_changed"}) from error
    except ProblemNotFoundError as error:
        raise HTTPException(status_code=404, detail={"code": "problem_not_found"}) from error


@app.put("/api/drafts/{draft_id}/review", response_model=LessonDraft)
def review_lesson_draft(draft_id: str, request: ReviewDraftRequest) -> LessonDraft:
    try:
        return review_draft(draft_id, request)
    except RecordNotFoundError as error:
        raise HTTPException(status_code=404, detail={"code": "draft_not_found"}) from error
    except VersionConflictError as error:
        raise HTTPException(status_code=409, detail={"code": "draft_version_conflict"}) from error


@app.delete("/api/drafts/{draft_id}", status_code=204)
def delete_lesson_draft(draft_id: str) -> Response:
    try:
        delete_draft(draft_id)
    except RecordNotFoundError as error:
        raise HTTPException(status_code=404, detail={"code": "draft_not_found"}) from error
    return Response(status_code=204)


@app.get("/api/drafts/{draft_id}/export")
def export_lesson_draft(draft_id: str, audience: str = Query(pattern="^(teacher|student)$")) -> Response:
    try:
        draft = get_draft(draft_id)
    except RecordNotFoundError as error:
        raise HTTPException(status_code=404, detail={"code": "draft_not_found"}) from error
    content = export_draft_markdown(draft, audience)
    filename = quote(f"{draft.title}-{'教师版' if audience == 'teacher' else '学生版'}.md")
    return Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@app.post("/api/photos", response_model=PhotoRecord, status_code=201)
async def upload_problem_photo(file: UploadFile = File(...)) -> PhotoRecord:
    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    try:
        return save_photo(filename=file.filename, content_type=file.content_type, raw=raw)
    except InvalidUploadError as error:
        raise HTTPException(status_code=422, detail={"code": "invalid_photo", "message": str(error)}) from error
    finally:
        await file.close()


@app.get("/api/photos", response_model=list[PhotoRecord])
def get_problem_photos() -> list[PhotoRecord]:
    return list_photos()


@app.get("/api/photos/{photo_id}/content")
def get_problem_photo_content(photo_id: str) -> FileResponse:
    try:
        path = photo_content_path(photo_id)
    except RecordNotFoundError as error:
        raise HTTPException(status_code=404, detail={"code": "photo_not_found"}) from error
    return FileResponse(path, media_type="image/png")


@app.put("/api/photos/{photo_id}/transcript", response_model=PhotoRecord)
def set_photo_transcript(photo_id: str, request: UpdateTranscriptRequest) -> PhotoRecord:
    try:
        return update_photo_transcript(photo_id, request.transcript)
    except RecordNotFoundError as error:
        raise HTTPException(status_code=404, detail={"code": "photo_not_found"}) from error


@app.post("/api/photos/{photo_id}/search", response_model=list[SearchResult])
def search_photo_problem(photo_id: str, request: PhotoSearchRequest) -> list[SearchResult]:
    try:
        return search_from_photo(photo_id, request)
    except RecordNotFoundError as error:
        raise HTTPException(status_code=404, detail={"code": "photo_not_found"}) from error
    except InvalidUploadError as error:
        raise HTTPException(status_code=422, detail={"code": "transcript_required"}) from error


@app.delete("/api/photos/{photo_id}", status_code=204)
def delete_problem_photo(photo_id: str) -> Response:
    try:
        delete_photo(photo_id)
    except RecordNotFoundError as error:
        raise HTTPException(status_code=404, detail={"code": "photo_not_found"}) from error
    except PhotoInUseError as error:
        raise HTTPException(status_code=409, detail={"code": "photo_in_use"}) from error
    return Response(status_code=204)


@app.post("/api/feedback/{feedback_id}/polish", response_model=PolishResponse)
def polish_feedback(feedback_id: str, request: PolishRequest):
    try:
        store = get_store()
        raw = store.get_feedback(feedback_id)
        check_version(raw, request.expected_version)
        # Input checks precede the billable attempt.
        from .feedback_ai import evidence_for
        evidence = evidence_for(raw, request.audience)
        if len(evidence) > 40 or (request.audience == "individual" and not any(key.startswith("observation-") for key in evidence)):
            raise ValueError("请精简学习内容，并补充实际观察到的任务表现。")
        reserve_ai_attempt()
        return propose(raw, request, store)
    except RecordNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except VersionConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except (ModelProviderError, ModelNotConfiguredError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.put("/api/feedback/{feedback_id}/polish", response_model=AfterClassFeedback)
def adopt_feedback_polish(feedback_id: str, request: AdoptPolishRequest):
    try:
        get_store().adopt_feedback_proposal(
            feedback_id, request.expected_version, request.proposal_id, request.audience,
        )
        return get_feedback(feedback_id)
    except RecordNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except VersionConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post("/api/feedback", response_model=AfterClassFeedback, status_code=201)
def create_after_class_feedback(request: CreateFeedbackRequest) -> AfterClassFeedback:
    try:
        return create_feedback(request)
    except RecordNotFoundError as error:
        raise HTTPException(status_code=422, detail={"code": "photo_not_found"}) from error


@app.get("/api/feedback", response_model=list[FeedbackSummary])
def get_after_class_feedback_list() -> list[FeedbackSummary]:
    return list_feedback()


@app.get("/api/feedback/{feedback_id}", response_model=AfterClassFeedback)
def get_after_class_feedback(feedback_id: str) -> AfterClassFeedback:
    try:
        return get_feedback(feedback_id)
    except RecordNotFoundError as error:
        raise HTTPException(status_code=404, detail={"code": "feedback_not_found"}) from error


@app.put("/api/feedback/{feedback_id}", response_model=AfterClassFeedback)
def update_after_class_feedback(
    feedback_id: str, request: UpdateFeedbackRequest
) -> AfterClassFeedback:
    try:
        return update_feedback(feedback_id, request)
    except RecordNotFoundError as error:
        raise HTTPException(status_code=404, detail={"code": "feedback_or_photo_not_found"}) from error
    except VersionConflictError as error:
        raise HTTPException(status_code=409, detail={"code": "feedback_version_conflict"}) from error


@app.put("/api/feedback/{feedback_id}/review", response_model=AfterClassFeedback)
def review_after_class_feedback(
    feedback_id: str, request: ReviewFeedbackRequest
) -> AfterClassFeedback:
    try:
        return review_feedback(feedback_id, request)
    except RecordNotFoundError as error:
        raise HTTPException(status_code=404, detail={"code": "feedback_not_found"}) from error
    except VersionConflictError as error:
        raise HTTPException(status_code=409, detail={"code": "feedback_version_conflict"}) from error


@app.get("/api/feedback/{feedback_id}/export")
def export_after_class_feedback(
    feedback_id: str,
    audience: str = Query(pattern="^(individual|class_group)$"),
) -> Response:
    try:
        feedback = get_feedback(feedback_id)
    except RecordNotFoundError as error:
        raise HTTPException(status_code=404, detail={"code": "feedback_not_found"}) from error
    content = export_feedback_markdown(feedback, audience)
    label = "个人反馈" if audience == "individual" else "班群反馈"
    filename = quote(f"{feedback.lesson_date}-{feedback.topic}-{label}.md")
    return Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@app.delete("/api/feedback/{feedback_id}", status_code=204)
def delete_after_class_feedback(feedback_id: str) -> Response:
    try:
        delete_feedback(feedback_id)
    except RecordNotFoundError as error:
        raise HTTPException(status_code=404, detail={"code": "feedback_not_found"}) from error
    return Response(status_code=204)


def _problem_source_or_404(problem_id: str) -> dict:
    try:
        return get_problem_source(problem_id)
    except ProblemNotFoundError as error:
        raise HTTPException(status_code=404, detail={"code": "problem_not_found"}) from error
