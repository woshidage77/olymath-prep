from operator import add
from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from .catalog import ProblemNotFoundError, get_problem_source, problem_summary, project_cubes
from .model_gateway import ModelNotConfiguredError, ModelProviderError, analyze_problem
from .models import (
    Cube,
    LessonBrief,
    ProblemAnalysis,
    RelatedProblem,
    SearchRequest,
    SearchResult,
    Stage,
    ViewName,
)
from .retrieval import question_bank_retriever

WorkflowStatus = Literal[
    "received",
    "brief_validated",
    "candidate_retrieved",
    "context_retrieved",
    "problem_analyzed",
    "model_failed",
    "no_candidate",
    "sequence_proposed",
    "draft_created",
    "draft_validated",
    "waiting_teacher_review",
    "invalid_input",
    "invalid_output",
]


class WorkflowState(TypedDict, total=False):
    request: dict[str, Any]
    brief: dict[str, Any]
    status: WorkflowStatus
    trace: Annotated[list[str], add]
    error_code: str
    error_message: str
    problem_source: dict[str, Any]
    selected_problem: dict[str, Any]
    related_problems: list[dict[str, Any]]
    retrieval_query: str
    retrieval_results: list[dict[str, Any]]
    retrieval_context: list[dict[str, Any]]
    stages: list[dict[str, Any]]
    use_model: bool
    model_analysis: dict[str, Any]


def validate_brief_node(state: WorkflowState) -> WorkflowState:
    try:
        brief = LessonBrief.model_validate(state.get("request", {}))
    except ValidationError as error:
        return {
            "status": "invalid_input",
            "error_code": "invalid_brief",
            "error_message": str(error),
            "trace": ["validate_brief:failed"],
        }
    return {
        "brief": brief.model_dump(mode="json"),
        "status": "brief_validated",
        "trace": ["validate_brief:passed"],
    }


def route_after_validation(state: WorkflowState) -> Literal["retrieve_candidate", "end"]:
    return "retrieve_candidate" if state["status"] == "brief_validated" else "end"


def retrieve_candidate_node(state: WorkflowState) -> WorkflowState:
    problem_id = state["brief"]["starting_problem_id"]
    try:
        source = get_problem_source(problem_id)
    except ProblemNotFoundError:
        return {
            "status": "no_candidate",
            "error_code": "problem_not_found",
            "error_message": f"演示题目不存在：{problem_id}",
            "trace": ["retrieve_candidate:not_found"],
        }

    serializable_source = {
        **source,
        "cubes": [cube.model_dump(mode="json") for cube in source["cubes"]],
    }
    return {
        "problem_source": serializable_source,
        "selected_problem": problem_summary(source).model_dump(mode="json"),
        "status": "candidate_retrieved",
        "trace": ["retrieve_candidate:found"],
    }


def route_after_retrieval(state: WorkflowState) -> Literal["retrieve_context", "end"]:
    if state["status"] == "candidate_retrieved" and "selected_problem" in state:
        return "retrieve_context"
    return "end"


def retrieve_context_node(state: WorkflowState) -> WorkflowState:
    source = state["problem_source"]
    brief = state["brief"]
    query = brief.get("search_query") or " ".join([
        source["title"],
        source["statement"],
    ])
    results = question_bank_retriever.search(
        SearchRequest(
            query=query,
            grade=brief["grade"],
            topic=source["topic"],
            limit=3,
        ),
        exclude_ids={source["id"]},
    )
    context_ids = [source["id"], *[result.problem.id for result in results]]
    context = question_bank_retriever.context_for(context_ids)
    return {
        "retrieval_query": query,
        "retrieval_results": [result.model_dump(mode="json") for result in results],
        "retrieval_context": [item.model_dump(mode="json") for item in context],
        "status": "context_retrieved",
        "trace": ["retrieve_context:completed"],
    }


def route_after_context(state: WorkflowState) -> Literal["analyze_problem", "propose_sequence"]:
    return "analyze_problem" if state.get("use_model", False) else "propose_sequence"


def analyze_problem_node(state: WorkflowState) -> WorkflowState:
    try:
        analysis = analyze_problem(state["problem_source"])
    except ModelNotConfiguredError as error:
        return {
            "status": "model_failed",
            "error_code": "model_not_configured",
            "error_message": str(error),
            "trace": ["analyze_problem:not_configured"],
        }
    except ModelProviderError as error:
        return {
            "status": "model_failed",
            "error_code": "model_provider_error",
            "error_message": str(error),
            "trace": ["analyze_problem:failed"],
        }
    return {
        "model_analysis": analysis.model_dump(mode="json"),
        "status": "problem_analyzed",
        "trace": ["analyze_problem:completed"],
    }


def route_after_analysis(state: WorkflowState) -> Literal["propose_sequence", "end"]:
    return "propose_sequence" if state["status"] == "problem_analyzed" else "end"


def propose_sequence_node(state: WorkflowState) -> WorkflowState:
    source = state["problem_source"]
    related: list[dict[str, Any]] = []
    if source["next"] is not None:
        next_source = get_problem_source(source["next"]["id"])
        related.append(RelatedProblem(
            problem=problem_summary(next_source),
            relation=source["next"]["relation"],
            reason=source["next"]["reason"],
        ).model_dump(mode="json"))
    existing_ids = {item["problem"]["id"] for item in related}
    for result_data in state["retrieval_results"]:
        result = SearchResult.model_validate(result_data)
        if result.problem.id in existing_ids:
            continue
        shared_concepts = [
            concept for concept in result.problem.concepts
            if concept in source["concepts"]
        ]
        shared_methods = [
            method for method in result.problem.methods
            if method in source["methods"]
        ]
        connection = "、".join([*shared_concepts, *shared_methods]) or source["topic"]
        related.append(RelatedProblem(
            problem=result.problem,
            relation="同专题候选",
            reason=f"与原题共同训练：{connection}。可用于巩固或改变条件后的迁移。",
        ).model_dump(mode="json"))
        existing_ids.add(result.problem.id)
    return {
        "related_problems": related,
        "status": "sequence_proposed",
        "trace": ["propose_sequence:completed"],
    }


def draft_teaching_notes_node(state: WorkflowState) -> WorkflowState:
    source = state["problem_source"]
    problem = state["selected_problem"]
    cubes = [Cube.model_validate(cube) for cube in source["cubes"]]
    projections = {view: project_cubes(cubes, view) for view in ViewName}
    analysis = (
        ProblemAnalysis.model_validate(state["model_analysis"])
        if "model_analysis" in state else None
    )
    stages = [
        Stage(
            id="read-problem",
            problem_id=problem["id"],
            phase="problem",
            title="第一步：先做原题",
            purpose=problem["statement"],
            teacher_prompt=analysis.opening_question if analysis else problem["question"],
            teaching_note="先让学生独立观察并说出判断依据，暂不展示答案。",
            cubes=cubes,
            projections=projections,
        ),
        Stage(
            id="understand-method",
            problem_id=problem["id"],
            phase="concept",
            title="第二步：理解概念",
            purpose=(
                f"教学目标：{analysis.teaching_objective} 核心方法：{analysis.core_method}"
                if analysis else source["purpose"]
            ),
            teacher_prompt=(
                "；".join(analysis.scaffolding_questions)
                if analysis else source["teacher_prompt"]
            ),
            teaching_note=(
                f"重点防错：{'；'.join(analysis.common_mistakes)}"
                if analysis else source["teaching_note"]
            ),
            cubes=cubes,
            projections=projections,
        ),
        Stage(
            id="return-to-problem",
            problem_id=problem["id"],
            phase="return",
            title="第三步：回到原题",
            purpose="使用刚才的观察方法重新回答同一道题，并检查每个条件是否都被解释。",
            teacher_prompt=problem["question"],
            teaching_note=(
                f"参考答案：{problem['answer']} 变式建议：{analysis.variation_idea}"
                if analysis else f"参考答案：{problem['answer']}"
            ),
            cubes=cubes,
            projections=projections,
        ),
    ]
    return {
        "stages": [stage.model_dump(mode="json") for stage in stages],
        "status": "draft_created",
        "trace": ["draft_teaching_notes:completed"],
    }


def validate_output_node(state: WorkflowState) -> WorkflowState:
    try:
        stages = [Stage.model_validate(stage) for stage in state.get("stages", [])]
        selected_id = state["selected_problem"]["id"]
        expected_phases = ["problem", "concept", "return"]
        if [stage.phase for stage in stages] != expected_phases:
            raise ValueError("teaching phases are incomplete or out of order")
        if any(stage.problem_id != selected_id for stage in stages):
            raise ValueError("teaching stages reference different problems")
        for related in state.get("related_problems", []):
            item = RelatedProblem.model_validate(related)
            if item.problem.id == selected_id:
                raise ValueError("related problem cannot point to itself")
    except (KeyError, TypeError, ValueError, ValidationError) as error:
        return {
            "status": "invalid_output",
            "error_code": "invalid_workflow_output",
            "error_message": str(error),
            "trace": ["validate_output:failed"],
        }
    return {
        "status": "draft_validated",
        "trace": ["validate_output:passed"],
    }


def route_after_output_validation(state: WorkflowState) -> Literal["await_teacher_review", "end"]:
    return "await_teacher_review" if state["status"] == "draft_validated" else "end"


def await_teacher_review_node(_: WorkflowState) -> WorkflowState:
    return {
        "status": "waiting_teacher_review",
        "trace": ["await_teacher_review:pending"],
    }


def build_workflow():
    builder = StateGraph(WorkflowState)
    builder.add_node("validate_brief", validate_brief_node)
    builder.add_node("retrieve_candidate", retrieve_candidate_node)
    builder.add_node("retrieve_context", retrieve_context_node)
    builder.add_node("analyze_problem", analyze_problem_node)
    builder.add_node("propose_sequence", propose_sequence_node)
    builder.add_node("draft_teaching_notes", draft_teaching_notes_node)
    builder.add_node("validate_output", validate_output_node)
    builder.add_node("await_teacher_review", await_teacher_review_node)
    builder.add_edge(START, "validate_brief")
    builder.add_conditional_edges(
        "validate_brief",
        route_after_validation,
        {"retrieve_candidate": "retrieve_candidate", "end": END},
    )
    builder.add_conditional_edges(
        "retrieve_candidate",
        route_after_retrieval,
        {"retrieve_context": "retrieve_context", "end": END},
    )
    builder.add_conditional_edges(
        "retrieve_context",
        route_after_context,
        {"analyze_problem": "analyze_problem", "propose_sequence": "propose_sequence"},
    )
    builder.add_conditional_edges(
        "analyze_problem",
        route_after_analysis,
        {"propose_sequence": "propose_sequence", "end": END},
    )
    builder.add_edge("propose_sequence", "draft_teaching_notes")
    builder.add_edge("draft_teaching_notes", "validate_output")
    builder.add_conditional_edges(
        "validate_output",
        route_after_output_validation,
        {"await_teacher_review": "await_teacher_review", "end": END},
    )
    builder.add_edge("await_teacher_review", END)
    return builder.compile()


lesson_workflow = build_workflow()


def run_lesson_workflow(request: dict[str, Any], *, use_model: bool = False) -> WorkflowState:
    return lesson_workflow.invoke({
        "request": request,
        "status": "received",
        "trace": [],
        "use_model": use_model,
    })
