from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ViewName(StrEnum):
    FRONT = "front"
    LEFT = "left"
    TOP = "top"


class LessonBrief(BaseModel):
    grade: int = Field(default=5, ge=1, le=9)
    topic: str = Field(default="观察物体（三）", min_length=2, max_length=80)
    starting_problem_id: str = Field(default="cube-view-001", min_length=3, max_length=80)
    search_query: str | None = Field(default=None, max_length=120)

    @field_validator("topic")
    @classmethod
    def topic_must_have_content(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("topic cannot be blank")
        return normalized

    @field_validator("search_query")
    @classmethod
    def normalize_optional_query(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class Cube(BaseModel):
    x: int = Field(ge=0, le=9)
    y: int = Field(ge=0, le=9)
    z: int = Field(ge=0, le=9)


class ProjectionCell(BaseModel):
    col: int = Field(ge=0)
    row: int = Field(ge=0)
    depth: int = Field(ge=1)


class Stage(BaseModel):
    id: str
    problem_id: str
    phase: Literal["problem", "concept", "return"]
    title: str
    purpose: str
    teacher_prompt: str
    teaching_note: str
    cubes: list[Cube]
    projections: dict[ViewName, list[ProjectionCell]]


class ResourceSuggestion(BaseModel):
    kind: str
    title: str
    why: str
    action: str


class ProblemSummary(BaseModel):
    id: str
    revision_id: str
    title: str
    statement: str
    question: str
    answer: str
    teaching_role: str
    difficulty: str
    source_label: str
    source_status: str
    school_stage: str
    grade: int = Field(ge=1, le=12)
    topic: str
    semester: Literal["上册", "下册"]
    unit_id: str
    unit_name: str
    content_kind: Literal["原创教学题", "开放数据题"]
    has_interactive_model: bool = False
    is_featured: bool = False
    concepts: list[str]
    methods: list[str]
    tags: list[str]


class RelatedProblem(BaseModel):
    problem: ProblemSummary
    relation: str
    reason: str


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=120)
    grade: int | None = Field(default=None, ge=1, le=12)
    topic: str | None = Field(default=None, max_length=80)
    limit: int = Field(default=12, ge=1, le=50)

    @field_validator("query")
    @classmethod
    def query_must_have_content(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("query cannot be blank")
        return normalized


class SearchResult(BaseModel):
    problem: ProblemSummary
    score: int = Field(ge=1)
    matched_fields: list[str]


class RetrievalContextItem(BaseModel):
    problem_id: str
    revision_id: str
    source_label: str
    excerpt: str


class RetrievalInfo(BaseModel):
    strategy: Literal["keyword_tag_baseline"] = "keyword_tag_baseline"
    query: str
    candidates: list[SearchResult]
    context: list[RetrievalContextItem]


class WorkflowInfo(BaseModel):
    engine: Literal["langgraph"] = "langgraph"
    status: Literal["waiting_teacher_review"]
    review_required: bool = True
    trace: list[str]


class CurriculumUnit(BaseModel):
    id: str
    grade: int = Field(ge=1, le=12)
    semester: Literal["上册", "下册"]
    order: int = Field(ge=1)
    name: str
    focus: str
    olympiad_topics: list[str]
    problem_count: int = Field(ge=0)


class CurriculumCatalog(BaseModel):
    grade: int = Field(ge=1, le=12)
    edition: str
    available: bool
    units: list[CurriculumUnit]


class LessonPlan(BaseModel):
    demo_mode: bool = True
    brief: LessonBrief
    selected_problem: ProblemSummary
    teaching_strategy: str
    stages: list[Stage]
    related_problems: list[RelatedProblem]
    workflow: WorkflowInfo
    retrieval: RetrievalInfo
    resources: list[ResourceSuggestion]
    safety_note: str
    model_analysis: "ProblemAnalysis | None" = None


class ProblemAnalysis(BaseModel):
    knowledge_points: list[str] = Field(min_length=1, max_length=6)
    problem_type: str = Field(min_length=1, max_length=80)
    core_method: str = Field(min_length=1, max_length=500)
    prerequisites: list[str] = Field(max_length=6)
    difficulty_reasons: list[str] = Field(max_length=6)
    common_mistakes: list[str] = Field(max_length=6)
    teaching_objective: str = Field(min_length=1, max_length=500)
    opening_question: str = Field(min_length=1, max_length=500)
    scaffolding_questions: list[str] = Field(min_length=1, max_length=6)
    variation_idea: str = Field(min_length=1, max_length=500)
    review_warning: str = Field(min_length=1, max_length=300)


class ModelStatus(BaseModel):
    configured: bool
    provider: Literal["openai"] = "openai"
    model: str


class AIPlanRequest(BaseModel):
    problem_id: str = Field(min_length=3, max_length=80)
    search_query: str | None = Field(default=None, max_length=120)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)

    @field_validator("content")
    @classmethod
    def content_must_have_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("chat message cannot be blank")
        return normalized


class TeacherChatRequest(BaseModel):
    problem_id: str = Field(min_length=3, max_length=80)
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=12)

    @field_validator("message")
    @classmethod
    def message_must_have_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("chat message cannot be blank")
        return normalized


class TeacherChatResponse(BaseModel):
    answer: str
    provider: Literal["openai"] = "openai"
    model: str


class CreateDraftRequest(BaseModel):
    starting_problem_id: str = Field(min_length=3, max_length=80)
    related_problem_ids: list[str] = Field(default_factory=list, max_length=6)
    title: str | None = Field(default=None, max_length=120)

    @field_validator("title")
    @classmethod
    def normalize_optional_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def problem_ids_must_be_unique(self) -> "CreateDraftRequest":
        ids = [self.starting_problem_id, *self.related_problem_ids]
        if len(ids) != len(set(ids)):
            raise ValueError("draft problem IDs must be unique")
        return self


class DraftItemUpdate(BaseModel):
    id: str | None = Field(default=None, max_length=64)
    problem_id: str = Field(min_length=3, max_length=80)
    problem_revision_id: str = Field(min_length=3, max_length=120)
    relation: str = Field(min_length=1, max_length=40)
    teacher_prompt: str = Field(min_length=1, max_length=1000)
    teaching_note: str = Field(min_length=1, max_length=2000)

    @field_validator("relation", "teacher_prompt", "teaching_note")
    @classmethod
    def text_must_have_content(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("draft item text cannot be blank")
        return normalized


class UpdateDraftRequest(BaseModel):
    expected_version: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=120)
    teacher_note: str = Field(default="", max_length=4000)
    items: list[DraftItemUpdate] = Field(min_length=1, max_length=12)

    @field_validator("title")
    @classmethod
    def title_must_have_content(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("draft title cannot be blank")
        return normalized

    @model_validator(mode="after")
    def items_must_reference_unique_problems(self) -> "UpdateDraftRequest":
        ids = [item.problem_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("draft items must reference unique problems")
        return self


class ReviewDraftRequest(BaseModel):
    expected_version: int = Field(ge=1)
    status: Literal["pending_review", "approved"]


class DraftItem(BaseModel):
    id: str
    position: int = Field(ge=0)
    problem: ProblemSummary
    problem_revision_id: str
    revision_is_current: bool
    relation: str
    teacher_prompt: str
    teaching_note: str


class LessonDraftSummary(BaseModel):
    id: str
    title: str
    grade: int
    topic: str
    status: Literal["pending_review", "approved"]
    version: int = Field(ge=1)
    item_count: int = Field(ge=1)
    created_at: str
    updated_at: str


class LessonDraft(LessonDraftSummary):
    teacher_note: str
    items: list[DraftItem]


class PhotoRecord(BaseModel):
    id: str
    original_name: str
    content_type: Literal["image/png"] = "image/png"
    byte_size: int = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    sha256: str
    status: Literal["awaiting_transcription", "ready"]
    transcript: str
    created_at: str
    updated_at: str


class UpdateTranscriptRequest(BaseModel):
    transcript: str = Field(min_length=1, max_length=5000)

    @field_validator("transcript")
    @classmethod
    def transcript_must_have_content(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("transcript cannot be blank")
        return normalized


class PhotoSearchRequest(BaseModel):
    grade: int = Field(default=5, ge=1, le=12)
    topic: str | None = Field(default=None, max_length=80)
    limit: int = Field(default=10, ge=1, le=20)
