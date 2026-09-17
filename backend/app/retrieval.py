import re
from collections.abc import Iterable

from langchain_core.documents import Document

from .catalog import get_problem_source, problem_summary
from .models import RetrievalContextItem, SearchRequest, SearchResult
from .question_bank import ALL_PROBLEMS

FIELD_WEIGHTS = {
    "title": 5,
    "question": 4,
    "statement": 2,
    "concepts": 6,
    "methods": 6,
    "tags": 5,
    "topic": 3,
}


def _tokens(text: str) -> set[str]:
    normalized = text.lower().strip()
    ascii_words = set(re.findall(r"[a-z0-9]+", normalized))
    chinese_runs = re.findall(r"[\u4e00-\u9fff]+", normalized)
    chinese_ngrams = {
        run[index:index + 2]
        for run in chinese_runs
        for index in range(max(1, len(run) - 1))
        if len(run[index:index + 2]) == 2
    }
    return ascii_words | chinese_ngrams


def _as_text(value: str | Iterable[str]) -> str:
    return value if isinstance(value, str) else " ".join(value)


def problem_document(source: dict) -> Document:
    page_content = "\n".join([
        f"题目：{source['title']}",
        f"题干：{source['statement']}",
        f"问题：{source['question']}",
        f"答案：{source['answer']}",
        f"概念：{'、'.join(source['concepts'])}",
        f"方法：{'、'.join(source['methods'])}",
    ])
    return Document(
        id=source["revision_id"],
        page_content=page_content,
        metadata={
            "problem_id": source["id"],
            "revision_id": source["revision_id"],
            "source_label": source["source_label"],
            "school_stage": source["school_stage"],
            "grade": source["grade"],
            "topic": source["topic"],
            **{field: source[field] for field in FIELD_WEIGHTS},
        },
    )


class QuestionBankRetriever:
    strategy = "keyword_tag_baseline"

    def __init__(self, documents: list[Document] | None = None) -> None:
        self._documents = documents or [problem_document(source) for source in ALL_PROBLEMS]

    def search(
        self,
        request: SearchRequest,
        *,
        exclude_ids: set[str] | None = None,
    ) -> list[SearchResult]:
        excluded = exclude_ids or set()
        query = request.query.lower()
        query_tokens = _tokens(query)
        ranked: list[SearchResult] = []
        for document in self._documents:
            metadata = document.metadata
            problem_id = str(metadata["problem_id"])
            if problem_id in excluded:
                continue
            if request.grade is not None and metadata["grade"] != request.grade:
                continue
            if request.topic and request.topic not in str(metadata["topic"]):
                continue

            score = 0
            matched_fields: list[str] = []
            for field, weight in FIELD_WEIGHTS.items():
                field_text = _as_text(metadata[field]).lower()
                overlap = query_tokens & _tokens(field_text)
                phrase_match = query in field_text
                if phrase_match or overlap:
                    score += weight * (2 if phrase_match else 1) + len(overlap)
                    matched_fields.append(field)
            if score == 0:
                continue
            ranked.append(SearchResult(
                problem=problem_summary(get_problem_source(problem_id)),
                score=score,
                matched_fields=matched_fields,
            ))
        ranked.sort(key=lambda result: (-result.score, result.problem.id))
        return ranked[:request.limit]

    def context_for(self, problem_ids: list[str]) -> list[RetrievalContextItem]:
        by_problem_id = {
            str(document.metadata["problem_id"]): document
            for document in self._documents
        }
        context: list[RetrievalContextItem] = []
        for problem_id in dict.fromkeys(problem_ids):
            document = by_problem_id[problem_id]
            context.append(RetrievalContextItem(
                problem_id=problem_id,
                revision_id=str(document.metadata["revision_id"]),
                source_label=str(document.metadata["source_label"]),
                excerpt=document.page_content,
            ))
        return context


question_bank_retriever = QuestionBankRetriever()


def search_question_bank(request: SearchRequest) -> list[SearchResult]:
    return question_bank_retriever.search(request)
