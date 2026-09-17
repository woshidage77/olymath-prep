from .catalog import ProblemNotFoundError, list_demo_problems, project_cubes
from .models import (
    LessonBrief,
    LessonPlan,
    ProblemSummary,
    RetrievalContextItem,
    RetrievalInfo,
    RelatedProblem,
    SearchResult,
    ResourceSuggestion,
    Stage,
    WorkflowInfo,
)
from .workflow import run_lesson_workflow


class WorkflowExecutionError(RuntimeError):
    def __init__(self, status: str, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code


def build_lesson_plan(brief: LessonBrief, *, use_model: bool = False) -> LessonPlan:
    state = run_lesson_workflow(brief.model_dump(mode="json"), use_model=use_model)
    if state["status"] == "no_candidate":
        raise ProblemNotFoundError(brief.starting_problem_id)
    if state["status"] != "waiting_teacher_review":
        raise WorkflowExecutionError(
            status=state["status"],
            code=state.get("error_code", "workflow_failed"),
            message=state.get("error_message", "lesson workflow did not produce a reviewable draft"),
        )
    problem = ProblemSummary.model_validate(state["selected_problem"])
    stages = [Stage.model_validate(stage) for stage in state["stages"]]
    related_problems = [
        RelatedProblem.model_validate(related)
        for related in state["related_problems"]
    ]

    if problem.has_interactive_model:
        teaching_strategy = "先读题和猜想，再用小方块固定视角验证，最后回到原题说清判断依据。"
        resources = [
            ResourceSuggestion(
                kind="interactive_model",
                title="课堂互动小正方体",
                why="可以暂停、旋转和固定观察方向，帮助学生把立体与平面图对应起来。",
                action="依次演示自由视角、正面、左面和上面，让学生先猜再验证。",
            ),
            ResourceSuggestion(
                kind="physical_material",
                title="可拼搭小方块",
                why="学生先摸到和摆出实体，再解释投影，能减少只看平面图时的认知负担。",
                action="准备8—12个相同方块，让学生摆出题目结构并从指定方向观察。",
            ),
        ]
    else:
        teaching_strategy = "先让学生独立读题，再提炼数量或图形关系，比较方法后回到原题验算。"
        resources = [
            ResourceSuggestion(
                kind="board_plan",
                title="关系图或表格",
                why="把文字条件整理成可检查的关系，便于发现漏条件和单位错误。",
                action="根据题型选择线段图、列表、坐标图或数量关系式，并让学生解释每一项来源。",
            ),
            ResourceSuggestion(
                kind="variation",
                title="一题一变",
                why="改变一个条件可以检查学生掌握的是方法还是答案。",
                action="保留核心关系，只改变一个数字或问法，再让学生比较解法哪里保持不变。",
            ),
        ]
    return LessonPlan(
        brief=brief,
        selected_problem=problem,
        teaching_strategy=teaching_strategy,
        stages=stages,
        related_problems=related_problems,
        workflow=WorkflowInfo(status="waiting_teacher_review", trace=state["trace"]),
        retrieval=RetrievalInfo(
            query=state["retrieval_query"],
            candidates=[
                SearchResult.model_validate(result)
                for result in state["retrieval_results"]
            ],
            context=[
                RetrievalContextItem.model_validate(item)
                for item in state["retrieval_context"]
            ],
        ),
        resources=resources,
        safety_note="题目来源和答案已标注；专题归类与教学建议仍需教师确认。",
        model_analysis=state.get("model_analysis"),
    )
