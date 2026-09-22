import type { AdjustmentProposal, LessonPlan, Stage } from './types'

export function stageWithProposal(stage: Stage, proposal: AdjustmentProposal): Stage {
  return {
    ...stage,
    purpose: proposal.objective,
    teaching_steps: proposal.steps.map((step) => ({ ...step })),
    teacher_prompt: proposal.steps.map((step, index) => `${index + 1}. ${step.teacher_question}`).join('\n'),
    teaching_note: [
      `本环节目标：${proposal.objective}`,
      ...proposal.steps.map((step, index) => `${index + 1}. 学生动作：${step.student_action} 检查理解：${step.checkpoint}`),
      `教师核对：${proposal.teacher_check}`,
    ].join('\n'),
  }
}

// Compare the exact stage shown when generation started; never overwrite newer work.
export function replaceStage(plan: LessonPlan, expected: Stage, replacement: Stage): LessonPlan | null {
  const current = plan.stages.find((stage) => stage.id === expected.id)
  if (plan.selected_problem.id !== expected.problem_id
      || replacement.id !== expected.id || replacement.problem_id !== expected.problem_id
      || !current || JSON.stringify(current) !== JSON.stringify(expected)) return null
  return { ...plan, stages: plan.stages.map((stage) => stage.id === expected.id ? replacement : stage) }
}
