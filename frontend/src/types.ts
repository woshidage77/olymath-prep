export type ViewName = 'front' | 'left' | 'top'

export interface LessonBrief {
  grade: number
  topic: string
  starting_problem_id: string
  search_query: string | null
}

export interface Cube {
  x: number
  y: number
  z: number
}

export interface ProjectionCell {
  col: number
  row: number
  depth: number
}

export interface TeachingStep {
  teacher_question: string
  student_action: string
  checkpoint: string
}

export type AdjustmentGoal = 'start' | 'explain' | 'confusion' | 'challenge' | 'unsure' | 'custom'
export type AdjustmentMethod = 'recommend' | 'visual' | 'hands_on' | 'discussion'
export type AdjustmentStageId = 'read-problem' | 'understand-method' | 'return-to-problem'

export interface AdjustmentProposal {
  rationale: string
  objective: string
  steps: TeachingStep[]
  teacher_check: string
}

export interface AdjustmentRequest {
  problem_id: string
  revision_id: string
  stage_id: AdjustmentStageId
  goal: AdjustmentGoal
  method: AdjustmentMethod
  note: string
  current: Pick<Stage, 'purpose' | 'teacher_prompt' | 'teaching_note' | 'teaching_steps'>
}

export interface AdjustmentResponse {
  problem_id: string
  stage_id: AdjustmentStageId
  proposal: AdjustmentProposal
}

export interface Stage {
  teaching_steps: TeachingStep[]
  id: string
  problem_id: string
  phase: 'problem' | 'concept' | 'return'
  title: string
  purpose: string
  teacher_prompt: string
  teaching_note: string
  cubes: Cube[]
  projections: Record<ViewName, ProjectionCell[]>
}

export interface ProblemSummary {
  id: string
  revision_id: string
  title: string
  statement: string
  question: string
  answer: string
  teaching_role: string
  difficulty: string
  source_label: string
  source_status: string
  school_stage: string
  grade: number
  topic: string
  semester: '上册' | '下册'
  unit_id: string
  unit_name: string
  content_kind: '原创教学题' | '开放数据题'
  has_interactive_model: boolean
  is_featured: boolean
  concepts: string[]
  methods: string[]
  tags: string[]
}

export interface SearchResult {
  problem: ProblemSummary
  score: number
  matched_fields: string[]
}

export interface RetrievalContextItem {
  problem_id: string
  revision_id: string
  source_label: string
  excerpt: string
}

export interface RetrievalInfo {
  strategy: 'keyword_tag_baseline'
  query: string
  candidates: SearchResult[]
  context: RetrievalContextItem[]
}

export interface RelatedProblem {
  problem: ProblemSummary
  relation: string
  reason: string
}

export interface WorkflowInfo {
  engine: 'langgraph'
  status: 'waiting_teacher_review'
  review_required: boolean
  trace: string[]
}

export interface ResourceSuggestion {
  kind: string
  title: string
  why: string
  action: string
}

export interface LessonPlan {
  demo_mode: boolean
  brief: LessonBrief
  selected_problem: ProblemSummary
  teaching_strategy: string
  stages: Stage[]
  related_problems: RelatedProblem[]
  workflow: WorkflowInfo
  retrieval: RetrievalInfo
  resources: ResourceSuggestion[]
  safety_note: string
  model_analysis: ProblemAnalysis | null
}

export interface ProblemAnalysis {
  scope_note: string
  knowledge_points: string[]
  knowledge_evidence: KnowledgeEvidence[]
  problem_type: string
  core_method: string
  prerequisites: string[]
  skill_plans: SkillPlan[]
  difficulty_reasons: string[]
  common_mistakes: string[]
  teaching_objective: string
  opening_question: string
  scaffolding_questions: string[]
  variation_idea: string
  teacher_confirmations: string[]
  review_warning: string
}

export interface KnowledgeEvidence {
  knowledge_point: string
  evidence: string
  source_ids: string[]
}

export interface SkillPlan {
  skill: string
  observable_behavior: string
  teaching_activity: string
  success_criterion: string
}

export interface ModelStatus {
  daily_limit: number
  used: number
  remaining: number
  configured: boolean
  provider: 'deepseek' | 'openai'
  model: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface DraftItem {
  id: string
  position: number
  problem: ProblemSummary
  problem_revision_id: string
  revision_is_current: boolean
  relation: string
  teacher_prompt: string
  teaching_note: string
}

export interface LessonDraftSummary {
  id: string
  title: string
  grade: number
  topic: string
  status: 'pending_review' | 'approved'
  version: number
  item_count: number
  created_at: string
  updated_at: string
}

export interface LessonDraft extends LessonDraftSummary {
  teacher_note: string
  items: DraftItem[]
  plan_snapshot: LessonPlan | null
}

export interface PhotoRecord {
  id: string
  original_name: string
  content_type: 'image/png'
  byte_size: number
  width: number
  height: number
  sha256: string
  status: 'awaiting_transcription' | 'ready'
  transcript: string
  created_at: string
  updated_at: string
}

export type ObservationPerformance = 'independent' | 'prompted' | 'not_yet' | 'not_observed'

export interface FeedbackObservation {
  skill_area: string
  task_evidence: string
  performance: ObservationPerformance
  correction_result: string
}

export interface FeedbackPayload {
  student_name: string
  grade: number
  topic: string
  lesson_date: string
  actual_content: string
  observations: FeedbackObservation[]
  teacher_advice: string
  homework: string[]
  class_reminder: string
  photo_ids: string[]
}

export interface FeedbackSummary {
  id: string
  student_name: string
  grade: number
  topic: string
  lesson_date: string
  status: 'draft' | 'approved'
  version: number
  created_at: string
  updated_at: string
}

export interface AfterClassFeedback extends FeedbackSummary, FeedbackPayload {
  photos: PhotoRecord[]
  individual_report: string
  class_group_report: string
  ai_audiences: Array<'individual' | 'class_group'>
  ordinary_individual_report: string
  ordinary_class_group_report: string
}

export interface CurriculumUnit {
  id: string
  grade: number
  semester: '上册' | '下册'
  order: number
  name: string
  focus: string
  olympiad_topics: string[]
  problem_count: number
}

export interface CurriculumCatalog {
  grade: number
  edition: string
  available: boolean
  units: CurriculumUnit[]
}
