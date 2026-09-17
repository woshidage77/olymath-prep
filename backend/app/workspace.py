from __future__ import annotations

import hashlib
import io
import os
import warnings
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError

from .catalog import ProblemNotFoundError, get_problem_source, problem_summary
from .models import (
    CreateDraftRequest,
    DraftItem,
    DraftItemUpdate,
    LessonDraft,
    LessonDraftSummary,
    PhotoRecord,
    PhotoSearchRequest,
    ReviewDraftRequest,
    SearchRequest,
    SearchResult,
    UpdateDraftRequest,
)
from .retrieval import search_question_bank
from .service import build_lesson_plan
from .models import LessonBrief
from .storage import AppStore, RecordNotFoundError, VersionConflictError, private_root

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


class InvalidUploadError(ValueError):
    pass


class StaleProblemRevisionError(RuntimeError):
    pass


@lru_cache(maxsize=8)
def _store_for_root(root: str) -> AppStore:
    return AppStore(Path(root))


def get_store() -> AppStore:
    return _store_for_root(str(private_root()))


def clear_store_cache() -> None:
    _store_for_root.cache_clear()


def create_draft(request: CreateDraftRequest, store: AppStore | None = None) -> LessonDraft:
    repository = store or get_store()
    source = get_problem_source(request.starting_problem_id)
    plan = build_lesson_plan(LessonBrief(
        grade=source["grade"],
        topic=source["topic"],
        starting_problem_id=source["id"],
    ))
    relation_by_id = {
        related.problem.id: related.relation
        for related in plan.related_problems
    }
    problem_ids = [request.starting_problem_id, *request.related_problem_ids]
    items = [
        _draft_item_payload(
            get_problem_source(problem_id),
            relation="起始题" if position == 0 else relation_by_id.get(problem_id, "关联题"),
        )
        for position, problem_id in enumerate(problem_ids)
    ]
    title = request.title or f"{source['unit_name']} · {source['title']}"
    raw = repository.create_draft(
        title=title,
        grade=source["grade"],
        topic=source["topic"],
        items=items,
    )
    return _lesson_draft(raw)


def list_drafts(store: AppStore | None = None) -> list[LessonDraftSummary]:
    repository = store or get_store()
    return [LessonDraftSummary.model_validate(item) for item in repository.list_drafts()]


def get_draft(draft_id: str, store: AppStore | None = None) -> LessonDraft:
    return _lesson_draft((store or get_store()).get_draft(draft_id))


def update_draft(
    draft_id: str,
    request: UpdateDraftRequest,
    store: AppStore | None = None,
) -> LessonDraft:
    repository = store or get_store()
    items = [_validated_update_item(item) for item in request.items]
    raw = repository.update_draft(
        draft_id=draft_id,
        expected_version=request.expected_version,
        title=request.title,
        teacher_note=request.teacher_note.strip(),
        items=items,
    )
    return _lesson_draft(raw)


def review_draft(
    draft_id: str,
    request: ReviewDraftRequest,
    store: AppStore | None = None,
) -> LessonDraft:
    raw = (store or get_store()).review_draft(
        draft_id=draft_id,
        expected_version=request.expected_version,
        status=request.status,
    )
    return _lesson_draft(raw)


def delete_draft(draft_id: str, store: AppStore | None = None) -> None:
    (store or get_store()).delete_draft(draft_id)


def export_draft_markdown(draft: LessonDraft, audience: str) -> str:
    if audience not in {"teacher", "student"}:
        raise ValueError("audience must be teacher or student")
    lines = [f"# {draft.title}", "", f"课题：{draft.topic}", ""]
    if audience == "teacher":
        lines.extend([
            f"审核状态：{'已确认' if draft.status == 'approved' else '待确认'}",
            f"教师备注：{draft.teacher_note or '无'}",
            "",
        ])
    for index, item in enumerate(draft.items, start=1):
        lines.extend([
            f"## {index}. {item.problem.title}",
            "",
            item.problem.statement,
            "",
            f"问题：{item.problem.question}",
            "",
        ])
        if audience == "teacher":
            lines.extend([
                f"题间作用：{item.relation}",
                f"课堂追问：{item.teacher_prompt}",
                f"讲解动作：{item.teaching_note}",
                f"参考答案：{item.problem.answer}",
                f"来源：{item.problem.source_label}（{item.problem.source_status}）",
                "",
            ])
    return "\n".join(lines).rstrip() + "\n"


def save_photo(
    *,
    filename: str | None,
    content_type: str | None,
    raw: bytes,
    store: AppStore | None = None,
) -> PhotoRecord:
    repository = store or get_store()
    if not raw:
        raise InvalidUploadError("图片内容为空")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise InvalidUploadError("图片不能超过 8 MB")
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise InvalidUploadError("只支持 JPG、PNG 或 WebP 图片")

    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as opened:
                if opened.format not in {"JPEG", "PNG", "WEBP"}:
                    raise InvalidUploadError("图片真实格式不受支持")
                opened.verify()
            with Image.open(io.BytesIO(raw)) as opened:
                image = ImageOps.exif_transpose(opened)
                width, height = image.size
                if width < 64 or height < 64:
                    raise InvalidUploadError("图片尺寸过小，请上传清晰的单题照片")
                if width * height > MAX_IMAGE_PIXELS:
                    raise InvalidUploadError("图片像素过大")
                sanitized = image.convert("RGB")
                buffer = io.BytesIO()
                sanitized.save(buffer, format="PNG", optimize=True)
    except InvalidUploadError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning, UnidentifiedImageError, OSError) as error:
        raise InvalidUploadError("图片无法安全解码") from error

    payload = buffer.getvalue()
    if len(payload) > MAX_UPLOAD_BYTES:
        raise InvalidUploadError("安全重编码后的图片不能超过 8 MB")
    stored_name = f"{uuid4()}.png"
    final_path = repository.safe_child("uploads", stored_name)
    temporary_path = repository.safe_child("uploads", f".{stored_name}.tmp")
    try:
        temporary_path.write_bytes(payload)
        os.replace(temporary_path, final_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    try:
        raw_record = repository.create_photo(
            original_name=_safe_original_name(filename),
            stored_name=stored_name,
            byte_size=len(payload),
            width=width,
            height=height,
            sha256=hashlib.sha256(payload).hexdigest(),
        )
    except BaseException:
        final_path.unlink(missing_ok=True)
        raise
    return _photo_record(raw_record)


def list_photos(store: AppStore | None = None) -> list[PhotoRecord]:
    return [_photo_record(item) for item in (store or get_store()).list_photos()]


def update_photo_transcript(
    photo_id: str,
    transcript: str,
    store: AppStore | None = None,
) -> PhotoRecord:
    raw = (store or get_store()).update_transcript(photo_id, transcript.strip())
    return _photo_record(raw)


def search_from_photo(
    photo_id: str,
    request: PhotoSearchRequest,
    store: AppStore | None = None,
) -> list[SearchResult]:
    photo = (store or get_store()).get_photo(photo_id)
    transcript = photo["transcript"].strip()
    if not transcript:
        raise InvalidUploadError("请先校对并保存题目文字")
    return search_question_bank(SearchRequest(
        query=transcript,
        grade=request.grade,
        topic=request.topic,
        limit=request.limit,
    ))


def delete_photo(photo_id: str, store: AppStore | None = None) -> None:
    path = (store or get_store()).delete_photo(photo_id)
    path.unlink(missing_ok=True)


def _draft_item_payload(source: dict, *, relation: str) -> dict:
    problem = problem_summary(source)
    return {
        "id": None,
        "problem_id": problem.id,
        "problem_revision_id": problem.revision_id,
        "relation": relation,
        "teacher_prompt": source["teacher_prompt"],
        "teaching_note": source["teaching_note"],
        "problem_snapshot": problem.model_dump(mode="json"),
    }


def _validated_update_item(item: DraftItemUpdate) -> dict:
    source = get_problem_source(item.problem_id)
    problem = problem_summary(source)
    if problem.revision_id != item.problem_revision_id:
        raise StaleProblemRevisionError(
            f"problem revision changed: {item.problem_revision_id} -> {problem.revision_id}"
        )
    return {
        "id": item.id,
        "problem_id": item.problem_id,
        "problem_revision_id": item.problem_revision_id,
        "relation": item.relation,
        "teacher_prompt": item.teacher_prompt,
        "teaching_note": item.teaching_note,
        "problem_snapshot": problem.model_dump(mode="json"),
    }


def _lesson_draft(raw: dict) -> LessonDraft:
    items: list[DraftItem] = []
    for item in raw["items"]:
        snapshot = problem_summary(item["problem_snapshot"])
        try:
            current_revision = problem_summary(get_problem_source(snapshot.id)).revision_id
        except ProblemNotFoundError:
            current_revision = ""
        items.append(DraftItem(
            id=item["id"],
            position=item["position"],
            problem=snapshot,
            problem_revision_id=item["problem_revision_id"],
            revision_is_current=current_revision == item["problem_revision_id"],
            relation=item["relation"],
            teacher_prompt=item["teacher_prompt"],
            teaching_note=item["teaching_note"],
        ))
    return LessonDraft.model_validate({**raw, "items": items})


def _photo_record(raw: dict) -> PhotoRecord:
    return PhotoRecord.model_validate({
        field: raw[field]
        for field in PhotoRecord.model_fields
    })


def _safe_original_name(filename: str | None) -> str:
    name = Path(filename or "upload").name
    cleaned = "".join(character for character in name if character.isprintable()).strip()
    return (cleaned or "upload")[:120]
