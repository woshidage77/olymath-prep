import type {
  AfterClassFeedback,
  AdjustmentRequest,
  AdjustmentResponse,
  ChatMessage,
  CurriculumCatalog,
  FeedbackPayload,
  FeedbackSummary,
  LessonBrief,
  LessonDraft,
  LessonDraftSummary,
  LessonPlan,
  ModelStatus,
  PhotoRecord,
  ProblemSummary,
  SearchResult,
} from './types'

async function apiError(response: Response, fallback: string): Promise<Error> {
  let detail = ''
  try {
    const payload = await response.json() as { detail?: string | { code?: string } }
    detail = typeof payload.detail === 'string' ? payload.detail : payload.detail?.code ?? ''
  } catch {
    // The status remains the useful fallback when the server did not return JSON.
  }
  return new Error(`${fallback}（HTTP ${response.status}${detail ? ` · ${detail}` : ''}）`)
}

export async function getCurriculum(grade: number): Promise<CurriculumCatalog> {
  const response = await fetch(`/api/demo/curriculum?grade=${grade}`)
  if (!response.ok) throw await apiError(response, '读取课程目录失败')
  return response.json() as Promise<CurriculumCatalog>
}

export async function listProblems(grade: number, topic?: string): Promise<ProblemSummary[]> {
  const params = new URLSearchParams({ grade: String(grade) })
  if (topic) params.set('topic', topic)
  const response = await fetch(`/api/demo/problems?${params.toString()}`)
  if (!response.ok) throw await apiError(response, '读取演示题目失败')
  return response.json() as Promise<ProblemSummary[]>
}

export async function searchProblems(
  query: string,
  grade = 5,
  topic?: string,
  limit = 20,
): Promise<SearchResult[]> {
  const response = await fetch('/api/demo/problems/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, grade, topic, limit }),
  })
  if (!response.ok) throw await apiError(response, '检索题库失败')
  return response.json() as Promise<SearchResult[]>
}

export async function createLessonPlan(brief: LessonBrief): Promise<LessonPlan> {
  const response = await fetch('/api/demo/lesson-plan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(brief),
  })
  if (!response.ok) {
    throw await apiError(response, '生成备课方案失败')
  }
  return response.json() as Promise<LessonPlan>
}

export async function getModelStatus(): Promise<ModelStatus> {
  const response = await fetch('/api/ai/status')
  if (!response.ok) throw await apiError(response, '读取智能助教状态失败')
  return response.json() as Promise<ModelStatus>
}

export async function createAiLessonPlan(problemId: string, searchQuery: string | null, teacherRequest: string): Promise<LessonPlan> {
  const response = await fetch('/api/ai/lesson-plan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ problem_id: problemId, search_query: searchQuery, teacher_request: teacherRequest }),
  })
  if (!response.ok) throw await apiError(response, '智能分析失败')
  return response.json() as Promise<LessonPlan>
}

export async function requestStageAdjustment(request: AdjustmentRequest): Promise<AdjustmentResponse> {
  const response = await fetch('/api/ai/adjust-stage', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  if (!response.ok) throw await apiError(response, '生成调整建议失败')
  return response.json() as Promise<AdjustmentResponse>
}

export async function askTeacherAssistant(
  plan: LessonPlan,
  message: string,
  history: ChatMessage[],
): Promise<string> {
  const response = await fetch('/api/ai/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      problem_id: plan.selected_problem.id,
      message,
      history,
      analysis: plan.model_analysis,
    }),
  })
  if (!response.ok) throw await apiError(response, '智能助教回答失败')
  const payload = await response.json() as { answer: string }
  return payload.answer
}

export async function createDraft(
  problemId: string,
  relatedIds: string[],
  planSnapshot: LessonPlan,
): Promise<LessonDraft> {
  const response = await fetch('/api/drafts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      starting_problem_id: problemId,
      related_problem_ids: relatedIds,
      plan_snapshot: planSnapshot,
    }),
  })
  if (!response.ok) throw await apiError(response, '保存备课草稿失败')
  return response.json() as Promise<LessonDraft>
}

export async function listDrafts(): Promise<LessonDraftSummary[]> {
  const response = await fetch('/api/drafts')
  if (!response.ok) throw await apiError(response, '读取备课草稿失败')
  return response.json() as Promise<LessonDraftSummary[]>
}

export async function getDraft(id: string): Promise<LessonDraft> {
  const response = await fetch(`/api/drafts/${encodeURIComponent(id)}`)
  if (!response.ok) throw await apiError(response, '读取备课草稿失败')
  return response.json() as Promise<LessonDraft>
}

export async function updateDraft(draft: LessonDraft): Promise<LessonDraft> {
  const response = await fetch(`/api/drafts/${encodeURIComponent(draft.id)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      expected_version: draft.version,
      title: draft.title,
      teacher_note: draft.teacher_note,
      items: draft.items.map((item) => ({
        id: item.id,
        problem_id: item.problem.id,
        problem_revision_id: item.problem_revision_id,
        relation: item.relation,
        teacher_prompt: item.teacher_prompt,
        teaching_note: item.teaching_note,
      })),
    }),
  })
  if (!response.ok) throw await apiError(response, '保存修改失败')
  return response.json() as Promise<LessonDraft>
}

export async function reviewDraft(draft: LessonDraft, status: 'pending_review' | 'approved'): Promise<LessonDraft> {
  const response = await fetch(`/api/drafts/${encodeURIComponent(draft.id)}/review`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ expected_version: draft.version, status }),
  })
  if (!response.ok) throw await apiError(response, '更新审核状态失败')
  return response.json() as Promise<LessonDraft>
}

export async function deleteDraft(id: string): Promise<void> {
  const response = await fetch(`/api/drafts/${encodeURIComponent(id)}`, { method: 'DELETE' })
  if (!response.ok) throw await apiError(response, '删除草稿失败')
}

export function exportDraftUrl(id: string, audience: 'teacher' | 'student'): string {
  return `/api/drafts/${encodeURIComponent(id)}/export?audience=${audience}`
}

export async function uploadPhoto(file: File): Promise<PhotoRecord> {
  const form = new FormData()
  form.append('file', file)
  const response = await fetch('/api/photos', { method: 'POST', body: form })
  if (!response.ok) throw await apiError(response, '上传题目照片失败')
  return response.json() as Promise<PhotoRecord>
}

export async function listPhotos(): Promise<PhotoRecord[]> {
  const response = await fetch('/api/photos')
  if (!response.ok) throw await apiError(response, '读取拍照记录失败')
  return response.json() as Promise<PhotoRecord[]>
}

export async function updatePhotoTranscript(id: string, transcript: string): Promise<PhotoRecord> {
  const response = await fetch(`/api/photos/${encodeURIComponent(id)}/transcript`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ transcript }),
  })
  if (!response.ok) throw await apiError(response, '保存题目文字失败')
  return response.json() as Promise<PhotoRecord>
}

export async function searchPhoto(id: string, grade: number): Promise<SearchResult[]> {
  const response = await fetch(`/api/photos/${encodeURIComponent(id)}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ grade, limit: 10 }),
  })
  if (!response.ok) throw await apiError(response, '检索相似题失败')
  return response.json() as Promise<SearchResult[]>
}

export async function deletePhoto(id: string): Promise<void> {
  const response = await fetch(`/api/photos/${encodeURIComponent(id)}`, { method: 'DELETE' })
  if (!response.ok) throw await apiError(response, '删除拍照记录失败')
}

export function photoContentUrl(id: string): string {
  return `/api/photos/${encodeURIComponent(id)}/content`
}

export async function createFeedback(payload: FeedbackPayload): Promise<AfterClassFeedback> {
  const response = await fetch('/api/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) throw await apiError(response, '创建课后反馈失败')
  return response.json() as Promise<AfterClassFeedback>
}

export async function listFeedback(): Promise<FeedbackSummary[]> {
  const response = await fetch('/api/feedback')
  if (!response.ok) throw await apiError(response, '读取课后反馈失败')
  return response.json() as Promise<FeedbackSummary[]>
}

export async function getFeedback(id: string): Promise<AfterClassFeedback> {
  const response = await fetch(`/api/feedback/${encodeURIComponent(id)}`)
  if (!response.ok) throw await apiError(response, '读取课后反馈失败')
  return response.json() as Promise<AfterClassFeedback>
}

export async function updateFeedback(feedback: AfterClassFeedback): Promise<AfterClassFeedback> {
  const response = await fetch(`/api/feedback/${encodeURIComponent(feedback.id)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      expected_version: feedback.version,
      student_name: feedback.student_name,
      grade: feedback.grade,
      topic: feedback.topic,
      lesson_date: feedback.lesson_date,
      actual_content: feedback.actual_content,
      observations: feedback.observations,
      teacher_advice: feedback.teacher_advice,
      homework: feedback.homework,
      class_reminder: feedback.class_reminder,
      photo_ids: feedback.photo_ids,
    }),
  })
  if (!response.ok) throw await apiError(response, '保存课后反馈失败')
  return response.json() as Promise<AfterClassFeedback>
}

export async function reviewFeedback(
  feedback: AfterClassFeedback,
  status: 'draft' | 'approved',
): Promise<AfterClassFeedback> {
  const response = await fetch(`/api/feedback/${encodeURIComponent(feedback.id)}/review`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ expected_version: feedback.version, status }),
  })
  if (!response.ok) throw await apiError(response, '更新反馈状态失败')
  return response.json() as Promise<AfterClassFeedback>
}

export async function deleteFeedback(id: string): Promise<void> {
  const response = await fetch(`/api/feedback/${encodeURIComponent(id)}`, { method: 'DELETE' })
  if (!response.ok) throw await apiError(response, '删除课后反馈失败')
}

export function exportFeedbackUrl(id: string, audience: 'individual' | 'class_group'): string {
  return `/api/feedback/${encodeURIComponent(id)}/export?audience=${audience}`
}
