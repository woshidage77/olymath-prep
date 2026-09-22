<script setup lang="ts">
import StudentRecords from './components/StudentRecords.vue'
import RecordManager from './components/RecordManager.vue'
import DeleteRecordDialog from './components/DeleteRecordDialog.vue'
import FeedbackPolish from './components/FeedbackPolish.vue'
import UsageGuide from './components/UsageGuide.vue'
import { computed, defineAsyncComponent, nextTick, onMounted, reactive, ref, watch } from 'vue'
import {
  askTeacherAssistant,
  requestStageAdjustment,
  createDraft,
  createFeedback,
  createLessonPlan,
  deleteDraft,
  deleteFeedback,
  deletePhoto,
  exportDraftUrl,
  exportFeedbackUrl,
  getCurriculum,
  getDraft,
  getFeedback,
  getModelStatus,
  listDrafts,
  listFeedback,
  listPhotos,
  photoContentUrl,
  listProblems,
  reviewDraft,
  reviewFeedback,
  searchPhoto,
  searchProblems,
  updateDraft,
  updateFeedback,
  updatePhotoTranscript,
  uploadPhoto,
} from './api'
import type {
  AfterClassFeedback,
  AdjustmentGoal,
  AdjustmentMethod,
  AdjustmentProposal,
  AdjustmentStageId,
  Stage,
  CurriculumCatalog,
  CurriculumUnit,
  ChatMessage,
  FeedbackObservation,
  FeedbackPayload,
  FeedbackSummary,
  LessonDraft,
  LessonDraftSummary,
  LessonBrief,
  LessonPlan,
  ModelStatus,
  PhotoRecord,
  ProblemSummary,
  SearchResult,
} from './types'

import LandingPage from './components/LandingPage.vue'
import { stageWithProposal, replaceStage } from './adjustment'
import TeachingSteps from './components/TeachingSteps.vue'

const CubeWorkbench = defineAsyncComponent(() => import('./components/CubeWorkbench.vue'))

type ViewMode = 'library' | 'drafts' | 'photo' | 'feedback'
type DifficultyFilter = '全部' | '基础' | '进阶' | '挑战'
type LibraryPage = 'browse' | 'generating' | 'plan'

const grades = [1, 2, 3, 4, 5, 6, 7, 8, 9]
const semesterOptions = ['全部', '上册', '下册'] as const
const difficultyOptions: DifficultyFilter[] = ['全部', '基础', '进阶', '挑战']
const difficultyRank: Record<string, number> = { 基础: 0, 进阶: 1, 挑战: 2 }
// 测试阶段额度提示：准备上线时改为 false 即可统一隐藏。
const showModelUsageHints = true
const entered = ref(false)
const grade = ref(5)
const semester = ref<'全部' | '上册' | '下册'>('全部')
const difficulty = ref<DifficultyFilter>('全部')
const catalog = ref<CurriculumCatalog | null>(null)
const selectedUnitId = ref<string | null>(null)
const problems = ref<ProblemSummary[]>([])
const searchQuery = ref('')
const searchResults = ref<SearchResult[] | null>(null)
const plan = ref<LessonPlan | null>(null)
const activeStageIndex = ref(0)
const loadingCatalog = ref(false)
const loadingProblems = ref(false)
const loadingPlan = ref(false)
const searching = ref(false)
const error = ref('')
const mode = ref<ViewMode>('library')
const libraryPage = ref<LibraryPage>('browse')
const pendingProblem = ref<ProblemSummary | null>(null)
const generationMessage = ref('')
const modelState = ref<ModelStatus | null>(null)
const generatingAi = ref(false)
const aiPanelOpen = ref(false)
const teacherRequest = ref('')
const adjustmentGoal = ref<AdjustmentGoal>('unsure')
const adjustmentMethod = ref<AdjustmentMethod>('recommend')
const adjustmentStageId = ref<AdjustmentStageId>('understand-method')
const adjustmentGoals: { value: AdjustmentGoal; label: string }[] = [
  { value: 'start', label: '不知道从哪里开始' },
  { value: 'explain', label: '会算，但说不出为什么' },
  { value: 'confusion', label: '容易混淆概念或方向' },
  { value: 'challenge', label: '需要增加挑战' },
  { value: 'unsure', label: '暂不清楚，先检查理解' },
  { value: 'custom', label: '我有自己的教学设计' },
]
const adjustmentMethods: { value: AdjustmentMethod; label: string }[] = [
  { value: 'recommend', label: '由平台推荐' },
  { value: 'visual', label: '图示对比' },
  { value: 'hands_on', label: '动手操作' },
  { value: 'discussion', label: '追问讨论' },
]
const adjustmentStage = computed(() => plan.value?.stages.find((stage) => stage.id === adjustmentStageId.value))
const adjustmentPreview = ref<{ before: Stage; proposal: AdjustmentProposal } | null>(null)
const undoAdjustment = ref<{ before: Stage; after: Stage } | null>(null)
const adjustmentNotice = ref('')
const adjustmentReady = computed(() => adjustmentGoal.value !== 'custom' || Boolean(teacherRequest.value.trim()))
const adjustmentSignature = computed(() => JSON.stringify({
  revision: plan.value?.selected_problem.revision_id,
  stage: adjustmentStage.value, goal: adjustmentGoal.value, method: adjustmentMethod.value,
  note: teacherRequest.value,
}))
watch(adjustmentSignature, () => { adjustmentPreview.value = null })
watch(() => plan.value?.selected_problem.id, () => { undoAdjustment.value = null; adjustmentNotice.value = '' })

function applyAdjustment() {
  const preview = adjustmentPreview.value
  if (!preview || !plan.value) return
  const after = stageWithProposal(preview.before, preview.proposal)
  const updated = replaceStage(plan.value, preview.before, after)
  if (!updated) { adjustmentNotice.value = '原稿已变化，请重新生成建议。'; adjustmentPreview.value = null; return }
  plan.value = updated
  undoAdjustment.value = { before: preview.before, after }
  activeStageIndex.value = updated.stages.findIndex((stage) => stage.id === after.id)
  adjustmentPreview.value = null
  adjustmentNotice.value = '已采用到本环节，其他环节保持原样。可撤销，也可保存为备课草稿。'
}

function undoLastAdjustment() {
  if (!undoAdjustment.value || !plan.value) return
  const { before, after } = undoAdjustment.value
  const updated = replaceStage(plan.value, after, before)
  if (!updated) { adjustmentNotice.value = '该环节已变化，不能覆盖当前内容。'; return }
  plan.value = updated
  undoAdjustment.value = null
  adjustmentNotice.value = '已恢复调整前的内容。若之前已保存，保存的草稿不受影响。'
}

function discardAdjustment() {
  adjustmentPreview.value = null
  adjustmentNotice.value = '已放弃这份建议，原稿未修改；本次生成已使用的额度不退回。'
}
const aiConsent = ref(false)
const canCallAi = computed(() => Boolean(modelState.value?.configured && modelState.value.remaining > 0 && aiConsent.value && !generatingAi.value && !chatting.value))
async function refreshAllowance() {
  try { modelState.value = await getModelStatus() }
  catch { modelState.value = null }
}
const savingDraft = ref(false)
const draftNotice = ref('')
const chatInput = ref('')
const chatMessages = ref<ChatMessage[]>([])
const chatting = ref(false)
const draftSummaries = ref<LessonDraftSummary[]>([])
const activeDraft = ref<LessonDraft | null>(null)
const draftLoading = ref(false)
const draftProblemOptions = ref<ProblemSummary[]>([])
const draftAddId = ref('')
const photos = ref<PhotoRecord[]>([])
const activePhoto = ref<PhotoRecord | null>(null)
const photoTranscript = ref('')
const photoResults = ref<SearchResult[]>([])
const photoBusy = ref(false)
const feedbackSummaries = ref<FeedbackSummary[]>([])
const activeFeedback = ref<AfterClassFeedback | null>(null)
const feedbackBusy = ref(false)
const feedbackNotice = ref('')

function emptyObservation(): FeedbackObservation {
  return { skill_area: '', task_evidence: '', performance: 'independent', correction_result: '' }
}

function todayText(): string {
  return new Date().toISOString().slice(0, 10)
}

const feedbackForm = reactive<FeedbackPayload>({
  student_name: '',
  grade: 5,
  topic: '',
  lesson_date: todayText(),
  actual_content: '',
  observations: [emptyObservation()],
  teacher_advice: '',
  homework: [''],
  class_reminder: '',
  photo_ids: [],
})

const brief = reactive<LessonBrief>({
  grade: 5,
  topic: '观察物体（三）',
  starting_problem_id: 'cube-view-001',
  search_query: null,
})

const filteredUnits = computed(() => (
  catalog.value?.units.filter((unit) => semester.value === '全部' || unit.semester === semester.value) ?? []
))
const selectedUnit = computed(() => (
  catalog.value?.units.find((unit) => unit.id === selectedUnitId.value) ?? null
))
const displayedProblems = computed(() => (
  [...(searchResults.value?.map((result) => result.problem) ?? problems.value)]
    .filter((problem) => difficulty.value === '全部' || problem.difficulty === difficulty.value)
    .sort((left, right) => (
      Number(right.is_featured) - Number(left.is_featured)
      || (difficultyRank[left.difficulty] ?? 9) - (difficultyRank[right.difficulty] ?? 9)
      || left.title.localeCompare(right.title, 'zh-CN')
    ))
))
const difficultyCounts = computed(() => Object.fromEntries(
  difficultyOptions.map((level) => [
    level,
    level === '全部' ? problems.value.length : problems.value.filter((problem) => problem.difficulty === level).length,
  ]),
) as Record<DifficultyFilter, number>)
const activeStage = computed(() => plan.value?.stages[activeStageIndex.value] ?? null)
const feedbackReady = computed(() => (
  Boolean(feedbackForm.student_name.trim())
  && Boolean(feedbackForm.topic.trim())
  && Boolean(feedbackForm.actual_content.trim())
  && Boolean(feedbackForm.teacher_advice.trim())
  && feedbackForm.homework.some((item) => item.trim())
  && feedbackForm.observations.every((item) => item.skill_area.trim() && item.task_evidence.trim())
))

async function loadCatalog() {
  loadingCatalog.value = true
  error.value = ''
  selectedUnitId.value = null
  problems.value = []
  plan.value = null
  searchResults.value = null
  searchQuery.value = ''
  difficulty.value = '全部'
  libraryPage.value = 'browse'
  try {
    catalog.value = await getCurriculum(grade.value)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '课程目录加载失败'
  } finally {
    loadingCatalog.value = false
  }
}

async function openUnit(unit: CurriculumUnit) {
  selectedUnitId.value = unit.id
  brief.grade = grade.value
  brief.topic = unit.name
  plan.value = null
  searchQuery.value = ''
  searchResults.value = null
  difficulty.value = '全部'
  libraryPage.value = 'browse'
  loadingProblems.value = true
  error.value = ''
  try {
    problems.value = await listProblems(grade.value, unit.name)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '题目加载失败'
  } finally {
    loadingProblems.value = false
  }
}

function backToUnits() {
  selectedUnitId.value = null
  problems.value = []
  plan.value = null
  searchResults.value = null
  searchQuery.value = ''
  difficulty.value = '全部'
  libraryPage.value = 'browse'
}

const guideOpen = ref(false)
const guideIntroductory = ref(false)
let offeredGuide = false
function openGuide() { guideIntroductory.value = false; guideOpen.value = true }
watch(entered, (value) => {
  if (!value || offeredGuide) return
  offeredGuide = true
  try { if (localStorage.getItem('yiduo.guide.quiet.v1') === 'true') return } catch { /* Optional browser preference; guide remains usable. */ }
  guideIntroductory.value = true
  guideOpen.value = true
})

function enterWorkspace() {
  entered.value = true
  mode.value = 'library'
  libraryPage.value = 'browse'
  window.scrollTo({ top: 0, behavior: 'instant' })
}

function openHomeDestination(destination: ViewMode) {
  entered.value = true
  void switchMode(destination)
  window.scrollTo({ top: 0, behavior: 'instant' })
}

async function openHomeTopic(unitId: string) {
  enterWorkspace()
  if (grade.value !== 5 || !catalog.value?.available) {
    grade.value = 5
    await loadCatalog()
  }
  const unit = catalog.value?.units.find((item) => item.id === unitId)
  if (unit) await openUnit(unit)
}

function goHome() {
  entered.value = false
  mode.value = 'library'
  backToUnits()
  window.scrollTo({ top: 0, behavior: 'instant' })
}

async function runSearch() {
  const query = searchQuery.value.trim()
  if (!query || !selectedUnit.value) {
    searchResults.value = null
    return
  }
  searching.value = true
  error.value = ''
  try {
    searchResults.value = await searchProblems(query, grade.value, selectedUnit.value.name)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '搜索失败'
  } finally {
    searching.value = false
  }
}

function clearSearch() {
  searchQuery.value = ''
  searchResults.value = null
}

async function chooseProblem(problem: ProblemSummary) {
  if (loadingPlan.value || generatingAi.value || chatting.value) return
  brief.grade = problem.grade
  brief.topic = problem.topic
  brief.starting_problem_id = problem.id
  brief.search_query = searchQuery.value.trim() || null
  pendingProblem.value = problem
  generationMessage.value = '正在读取基础备课资料，不调用模型…'
  plan.value = null
  aiPanelOpen.value = false
  teacherRequest.value = ''
  chatMessages.value = []
  draftNotice.value = ''
  libraryPage.value = 'generating'
  loadingPlan.value = true
  error.value = ''
  await nextTick()
  window.scrollTo({ top: 0, behavior: 'instant' })
  try {
    plan.value = await createLessonPlan({ ...brief })
    activeStageIndex.value = 0
    libraryPage.value = 'plan'
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '读取基础备课资料失败'
    libraryPage.value = 'browse'
  } finally {
    loadingPlan.value = false
    pendingProblem.value = null
  }
}

function backToProblemList() {
  libraryPage.value = 'browse'
  error.value = ''
  window.scrollTo({ top: 0, behavior: 'instant' })
}

async function switchMode(nextMode: ViewMode) {
  mode.value = nextMode
  error.value = ''
  if (nextMode === 'library') libraryPage.value = 'browse'
  if (nextMode === 'drafts') await loadDrafts()
  if (nextMode === 'photo') await loadPhotos()
  if (nextMode === 'feedback') await Promise.all([loadFeedback(), loadPhotos()])
}

async function runAiAnalysis() {
  if (!plan.value || !adjustmentStage.value || !canCallAi.value || !adjustmentReady.value) return
  const before: Stage = JSON.parse(JSON.stringify(adjustmentStage.value))
  const signature = adjustmentSignature.value
  const problem = plan.value.selected_problem
  generatingAi.value = true
  adjustmentPreview.value = null
  adjustmentNotice.value = ''
  error.value = ''
  try {
    const response = await requestStageAdjustment({
      problem_id: problem.id, revision_id: problem.revision_id,
      stage_id: adjustmentStageId.value, goal: adjustmentGoal.value,
      method: adjustmentMethod.value, note: teacherRequest.value.trim(),
      current: {
        purpose: before.purpose, teacher_prompt: before.teacher_prompt,
        teaching_note: before.teaching_note, teaching_steps: before.teaching_steps ?? [],
      },
    })
    if (signature !== adjustmentSignature.value || response.problem_id !== problem.id || response.stage_id !== before.id) {
      adjustmentNotice.value = '当前题目或要求已变化，本次建议未应用。'
      return
    }
    adjustmentPreview.value = { before, proposal: response.proposal }
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '生成失败，原稿已保留'
  } finally {
    generatingAi.value = false
    await refreshAllowance()
  }
}

async function askAssistant() {
  const message = chatInput.value.trim()
  if (!message || !plan.value || !canCallAi.value) return
  const history = [...chatMessages.value]
  chatMessages.value.push({ role: 'user', content: message })
  chatInput.value = ''
  chatting.value = true
  error.value = ''
  try {
    const answer = await askTeacherAssistant(plan.value, message, history)
    chatMessages.value.push({ role: 'assistant', content: answer })
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '智能助教回答失败'
  } finally {
    chatting.value = false
    await refreshAllowance()
  }
}

async function saveCurrentPlan() {
  if (!plan.value) return
  savingDraft.value = true
  error.value = ''
  try {
    const saved = await createDraft(
      plan.value.selected_problem.id,
      plan.value.related_problems.slice(0, 3).map((item) => item.problem.id),
      plan.value,
    )
    draftNotice.value = `已保存“${saved.title}”，可到我的备课继续编辑。`
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '保存备课草稿失败'
  } finally {
    savingDraft.value = false
  }
}

async function loadDrafts() {
  draftLoading.value = true
  try {
    draftSummaries.value = await listDrafts()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '备课草稿加载失败'
  } finally {
    draftLoading.value = false
  }
}

async function openDraft(id: string) {
  draftLoading.value = true
  try {
    activeDraft.value = await getDraft(id)
    draftProblemOptions.value = await listProblems(activeDraft.value.grade, activeDraft.value.topic)
    draftAddId.value = ''
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '备课草稿加载失败'
  } finally {
    draftLoading.value = false
  }
}

function addProblemToDraft() {
  if (!activeDraft.value || !draftAddId.value) return
  if (activeDraft.value.items.some((item) => item.problem.id === draftAddId.value)) return
  const problem = draftProblemOptions.value.find((item) => item.id === draftAddId.value)
  if (!problem || activeDraft.value.items.length >= 12) return
  activeDraft.value.items.push({
    id: '',
    position: activeDraft.value.items.length,
    problem,
    problem_revision_id: problem.revision_id,
    revision_is_current: true,
    relation: '补充练习',
    teacher_prompt: problem.question,
    teaching_note: '先让学生独立作答，再比较它与上一题保持不变和发生变化的条件。',
  })
  draftAddId.value = ''
}

function moveDraftItem(index: number, direction: -1 | 1) {
  if (!activeDraft.value) return
  const target = index + direction
  if (target < 0 || target >= activeDraft.value.items.length) return
  const items = activeDraft.value.items
  ;[items[index], items[target]] = [items[target], items[index]]
}

function removeDraftItem(index: number) {
  if (!activeDraft.value || activeDraft.value.items.length <= 1) return
  activeDraft.value.items.splice(index, 1)
}

async function saveDraftEdits() {
  if (!activeDraft.value) return
  draftLoading.value = true
  error.value = ''
  try {
    activeDraft.value = await updateDraft(activeDraft.value)
    await loadDrafts()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '草稿保存失败'
  } finally {
    draftLoading.value = false
  }
}

async function setDraftStatus(status: 'pending_review' | 'approved') {
  if (!activeDraft.value) return
  draftLoading.value = true
  try {
    activeDraft.value = await reviewDraft(activeDraft.value, status)
    await loadDrafts()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '审核状态更新失败'
  } finally {
    draftLoading.value = false
  }
}

function removeActiveDraft() {
  if (activeDraft.value) requestRecordDelete('draft', activeDraft.value.id, activeDraft.value.title)
}

async function loadPhotos() {
  try {
    photos.value = await listPhotos()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '拍照记录加载失败'
  }
}

async function handlePhoto(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  photoBusy.value = true
  try {
    activePhoto.value = await uploadPhoto(file)
    photoTranscript.value = ''
    photoResults.value = []
    await loadPhotos()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '上传失败'
  } finally {
    photoBusy.value = false
    ;(event.target as HTMLInputElement).value = ''
  }
}

function openPhoto(photo: PhotoRecord) {
  activePhoto.value = photo
  photoTranscript.value = photo.transcript
  photoResults.value = []
}

async function saveTranscriptAndSearch() {
  if (!activePhoto.value || !photoTranscript.value.trim()) return
  photoBusy.value = true
  try {
    activePhoto.value = await updatePhotoTranscript(activePhoto.value.id, photoTranscript.value)
    photoResults.value = await searchPhoto(activePhoto.value.id, grade.value)
    await loadPhotos()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '题目文字处理失败'
  } finally {
    photoBusy.value = false
  }
}

function removeActivePhoto() {
  if (activePhoto.value) requestRecordDelete('photo', activePhoto.value.id, activePhoto.value.original_name)
}

const feedbackDirty = computed(() => {
  if (!activeFeedback.value) return true
  return Object.keys(feedbackForm).some((key) =>
    JSON.stringify(feedbackForm[key as keyof FeedbackPayload]) !== JSON.stringify(activeFeedback.value![key as keyof FeedbackPayload]))
})
function onPolishAdopted(feedback: AfterClassFeedback) {
  activeFeedback.value = feedback
  feedbackNotice.value = '反馈版本已保存为草稿，请核对后确认并导出。'
  void loadFeedback()
}

function newStudentFeedback(name: string, studentGrade: number) {
  resetFeedbackForm()
  feedbackForm.student_name = name
  feedbackForm.grade = studentGrade
  feedbackNotice.value = '已填写学生姓名和最近记录的年级，请核对本次课程信息。'
}

function resetFeedbackForm() {
  activeFeedback.value = null
  feedbackForm.student_name = ''
  feedbackForm.grade = grade.value
  feedbackForm.topic = selectedUnit.value?.name ?? ''
  feedbackForm.lesson_date = todayText()
  feedbackForm.actual_content = ''
  feedbackForm.observations = [emptyObservation()]
  feedbackForm.teacher_advice = ''
  feedbackForm.homework = ['']
  feedbackForm.class_reminder = ''
  feedbackForm.photo_ids = []
  feedbackNotice.value = ''
}

async function loadFeedback() {
  feedbackBusy.value = true
  try {
    feedbackSummaries.value = await listFeedback()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '课后反馈加载失败'
  } finally {
    feedbackBusy.value = false
  }
}

async function openFeedback(id: string) {
  feedbackBusy.value = true
  try {
    activeFeedback.value = await getFeedback(id)
    const current = activeFeedback.value
    feedbackForm.student_name = current.student_name
    feedbackForm.grade = current.grade
    feedbackForm.topic = current.topic
    feedbackForm.lesson_date = current.lesson_date
    feedbackForm.actual_content = current.actual_content
    feedbackForm.observations = current.observations.map((item) => ({ ...item }))
    feedbackForm.teacher_advice = current.teacher_advice
    feedbackForm.homework = [...current.homework]
    feedbackForm.class_reminder = current.class_reminder
    feedbackForm.photo_ids = [...current.photo_ids]
    feedbackNotice.value = ''
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '课后反馈加载失败'
  } finally {
    feedbackBusy.value = false
  }
}

function addObservation() {
  if (feedbackForm.observations.length < 8) feedbackForm.observations.push(emptyObservation())
}

function removeObservation(index: number) {
  if (feedbackForm.observations.length > 1) feedbackForm.observations.splice(index, 1)
}

function addHomework() {
  if (feedbackForm.homework.length < 10) feedbackForm.homework.push('')
}

function removeHomework(index: number) {
  if (feedbackForm.homework.length > 1) feedbackForm.homework.splice(index, 1)
}

function toggleFeedbackPhoto(photoId: string) {
  const index = feedbackForm.photo_ids.indexOf(photoId)
  if (index >= 0) feedbackForm.photo_ids.splice(index, 1)
  else if (feedbackForm.photo_ids.length < 9) feedbackForm.photo_ids.push(photoId)
}

async function handleFeedbackPhoto(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  feedbackBusy.value = true
  try {
    const photo = await uploadPhoto(file)
    feedbackForm.photo_ids.push(photo.id)
    await loadPhotos()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '课堂作业上传失败'
  } finally {
    feedbackBusy.value = false
    ;(event.target as HTMLInputElement).value = ''
  }
}

async function saveFeedback() {
  if (!feedbackReady.value) return
  feedbackBusy.value = true
  error.value = ''
  try {
    const payload: FeedbackPayload = {
      ...feedbackForm,
      observations: feedbackForm.observations.map((item) => ({ ...item })),
      homework: feedbackForm.homework.map((item) => item.trim()).filter(Boolean),
      photo_ids: [...feedbackForm.photo_ids],
    }
    activeFeedback.value = activeFeedback.value
      ? await updateFeedback({ ...activeFeedback.value, ...payload })
      : await createFeedback(payload)
    await openFeedback(activeFeedback.value.id)
    await loadFeedback()
    feedbackNotice.value = '已生成个人反馈和班群反馈，请核对后确认。'
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '课后反馈保存失败'
  } finally {
    feedbackBusy.value = false
  }
}

async function setFeedbackStatus(status: 'draft' | 'approved') {
  if (!activeFeedback.value) return
  feedbackBusy.value = true
  try {
    activeFeedback.value = await reviewFeedback(activeFeedback.value, status)
    await loadFeedback()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '反馈状态更新失败'
  } finally {
    feedbackBusy.value = false
  }
}

function removeActiveFeedback() {
  if (activeFeedback.value) requestRecordDelete('feedback', activeFeedback.value.id, activeFeedback.value.student_name + ' · ' + activeFeedback.value.topic)
}
type RecordKind = 'draft' | 'feedback' | 'photo'
const deleteTarget = ref<{kind:RecordKind; id:string; title:string} | null>(null)
const deletingRecord = ref(false)
const deletionError = ref('')
const recordNotice = ref('')
const recordKindLabels = { draft:'备课草稿', feedback:'课后反馈', photo:'拍照记录' }
function requestRecordDelete(kind:RecordKind, id:string, title:string) {
  if (deletingRecord.value) return
  deleteTarget.value = {kind,id,title}
  deletionError.value = ''
  recordNotice.value = ''
}
async function confirmRecordDelete() {
  const target = deleteTarget.value
  if (!target || deletingRecord.value) return
  deletingRecord.value = true
  deletionError.value = ''
  try {
    if (target.kind === 'draft') {
      await deleteDraft(target.id)
      draftSummaries.value = draftSummaries.value.filter(item => item.id !== target.id)
      if (activeDraft.value?.id === target.id) activeDraft.value = null
    } else if (target.kind === 'feedback') {
      await deleteFeedback(target.id)
      feedbackSummaries.value = feedbackSummaries.value.filter(item => item.id !== target.id)
      if (activeFeedback.value?.id === target.id) resetFeedbackForm()
    } else {
      await deletePhoto(target.id)
      photos.value = photos.value.filter(item => item.id !== target.id)
      feedbackForm.photo_ids = feedbackForm.photo_ids.filter(id => id !== target.id)
      if (activePhoto.value?.id === target.id) {
        activePhoto.value = null
        photoTranscript.value = ''
        photoResults.value = []
      }
    }
    recordNotice.value = '已删除「' + target.title + '」。'
    deleteTarget.value = null
  } catch (reason) {
    deletionError.value = reason instanceof Error ? reason.message : '删除失败，请稍后重试。'
  } finally { deletingRecord.value = false }
}
watch(mode, () => { recordNotice.value = '' })


onMounted(async () => {
  await Promise.all([loadCatalog(), getModelStatus().then((value) => { modelState.value = value })])
})
</script>

<template>
  <DeleteRecordDialog v-if="deleteTarget" :title="deleteTarget.title" :kind="recordKindLabels[deleteTarget.kind]" :busy="deletingRecord" :error="deletionError" @cancel="deleteTarget = null" @confirm="confirmRecordDelete" />
  <UsageGuide v-if="guideOpen" :introductory="guideIntroductory" @close="guideOpen = false" />
  <header class="site-header" :class="{ 'landing-header': !entered }">
    <a class="brand" href="#" @click.prevent="goHome">
      <span class="brand-mark">一朵</span>
      <span><strong>一朵教学</strong><small>教师备课工作台</small></span>
    </a>
    <nav v-if="entered" class="main-nav" aria-label="主要功能">
      <button :class="{ active: mode === 'library' }" @click="switchMode('library')">题库备课</button>
      <button :class="{ active: mode === 'drafts' }" @click="switchMode('drafts')">我的备课</button>
      <button :class="{ active: mode === 'photo' }" @click="switchMode('photo')">拍照录题</button>
      <button class="guide-nav-entry" @click="openGuide">使用指南</button>
      <button :class="{ active: mode === 'feedback' }" @click="switchMode('feedback')">课后反馈</button>
    </nav>
    <template v-else>
      <nav class="home-nav" aria-label="首页导航"><button class="guide-nav-entry" @click="openGuide">使用指南</button><a href="#preparation">备课方式</a><a href="#subjects">学科专题</a><a href="#questions">常见问题</a></nav>
      <button type="button" class="header-entry" @click="enterWorkspace">进入工作台 <span aria-hidden="true">↗</span></button>
    </template>
  </header>

  <main :key="[entered, mode, libraryPage, selectedUnit?.id].join('|')" class="page-arrival" :class="{ 'landing-main': !entered }">
    <p v-if="recordNotice && entered" class="success-message" role="status">{{ recordNotice }}</p>
    <LandingPage @guide="openGuide" v-if="!entered" @enter="enterWorkspace" @destination="openHomeDestination" @topic="openHomeTopic" />

    <section v-else-if="mode === 'library' && libraryPage === 'browse'" class="selection-card" aria-labelledby="selection-title">
      <div class="step-title">
        <span>01</span>
        <div>
          <h1 id="selection-title">选择备课专题</h1>
          <p>先确定年级和专题，再按难度选择本节课的起始题。</p>
        </div>
      </div>

      <aside v-if="showModelUsageHints && modelState?.configured" class="model-budget-notice">
        <strong>测试额度提示</strong>
        <span>打开题目使用基础资料，不调用模型。只有主动提交 AI 调整或发送追问才消耗本站额度。</span>
      </aside>

      <div class="grade-row">
        <label for="grade">年级</label>
        <select id="grade" v-model.number="grade" @change="loadCatalog">
          <option v-for="item in grades" :key="item" :value="item">{{ item }}年级</option>
        </select>
        <span v-if="catalog?.available">{{ catalog.edition }}</span>
      </div>

      <p v-if="loadingCatalog" class="state-message">正在读取课程目录…</p>
      <div v-else-if="catalog && !catalog.available" class="empty-state">
        <strong>{{ grade }}年级题库正在整理</strong>
        <p>当前先把五年级备课流程做扎实。你可以切换到五年级查看完整示例。</p>
      </div>

      <template v-else-if="catalog?.available && !selectedUnit">
        <div class="semester-tabs" aria-label="册别筛选">
          <button
            v-for="item in semesterOptions"
            :key="item"
            type="button"
            :class="{ active: semester === item }"
            @click="semester = item"
          >{{ item }}</button>
        </div>

        <div class="folder-grid">
          <button
            v-for="unit in filteredUnits"
            :key="unit.id"
            type="button"
            class="folder-card"
            @click="openUnit(unit)"
          >
            <span class="unit-number">{{ String(unit.order).padStart(2, '0') }}</span>
            <span class="folder-copy">
              <small>{{ unit.semester }} · 第{{ unit.order }}单元</small>
              <strong>{{ unit.name }}</strong>
              <em>{{ unit.focus }}</em>
            </span>
            <span class="folder-count">{{ unit.problem_count }}题</span>
          </button>
        </div>
      </template>

      <template v-else-if="selectedUnit">
        <div class="unit-header">
          <button type="button" class="back-button" @click="backToUnits">← 返回课题</button>
          <div>
            <small>{{ selectedUnit.semester }} · 第{{ selectedUnit.order }}单元</small>
            <h2>{{ selectedUnit.name }}</h2>
            <p>{{ selectedUnit.focus }}</p>
          </div>
          <span>{{ selectedUnit.problem_count }}道题</span>
        </div>

        <div class="topic-tags">
          <span v-for="topic in selectedUnit.olympiad_topics" :key="topic">{{ topic }}</span>
        </div>

        <div class="difficulty-filter" aria-label="按难度筛选">
          <span>难度</span>
          <button
            v-for="level in difficultyOptions"
            :key="level"
            type="button"
            :class="{ active: difficulty === level }"
            @click="difficulty = level"
          >{{ level }} <small>{{ difficultyCounts[level] }}</small></button>
        </div>

        <form class="question-search" @submit.prevent="runSearch">
          <label for="search">在本课题中找题</label>
          <div>
            <input id="search" v-model="searchQuery" maxlength="120" placeholder="输入题型、概念或方法" />
            <button type="submit" :disabled="searching">{{ searching ? '搜索中…' : '搜索' }}</button>
          </div>
          <button v-if="searchResults !== null" type="button" class="clear-button" @click="clearSearch">
            清除搜索
          </button>
        </form>

        <p v-if="modelState?.configured" class="model-call-note">
          点击题目查看基础备课资料，不消耗 AI 额度；进入后可按需使用 AI 调整。
        </p>

        <p v-if="loadingProblems" class="state-message">正在打开题目文件夹…</p>
        <p v-else-if="displayedProblems.length === 0" class="empty-state compact">没有符合当前难度的题目，请切换难度或搜索词。</p>
        <div v-else class="question-list">
          <button
            v-for="(problem, index) in displayedProblems"
            :key="problem.id"
            type="button"
            :class="{ active: plan?.selected_problem.id === problem.id, featured: problem.is_featured }"
            :disabled="loadingPlan"
            @click="chooseProblem(problem)"
          >
            <span class="question-number">{{ String(index + 1).padStart(2, '0') }}</span>
            <span class="question-copy">
              <small>
                <b v-if="problem.is_featured">推荐起点</b>
                {{ problem.difficulty }} · {{ problem.teaching_role }}
              </small>
              <strong>{{ problem.title }}</strong>
              <em>{{ problem.statement }}</em>
            </span>
            <span class="open-label">
              <span>查看基础方案 →</span>
            </span>
          </button>
        </div>
      </template>
      <p v-if="error" class="error-message">{{ error }}</p>
    </section>

    <section
      v-if="entered && mode === 'library' && libraryPage === 'generating'"
      class="generation-page"
      aria-live="polite"
      aria-busy="true"
    >
      <div class="generation-spinner" aria-hidden="true"><span></span><span></span><span></span></div>
      <p class="generation-kicker">正在准备这节课</p>
      <h1>{{ pendingProblem?.title }}</h1>
      <p class="generation-status">{{ generationMessage }}</p>
      <ol>
        <li>读取题目、答案与已有教学信息</li>
        <li>查找同专题的相近题目作为参考</li>
        <li>按已有资料整理讲解顺序，不调用模型</li>
      </ol>
      <small>基础资料支持直接查看、保存与编辑。</small>
    </section>

    <section v-if="entered && mode === 'library' && libraryPage === 'plan' && plan && activeStage" id="lesson-workspace" class="lesson-workspace plan-page">
      <button type="button" class="back-button plan-back" @click="backToProblemList">← 返回题目列表</button>
      <div class="step-title">
        <span>2</span>
        <div>
          <h2>围绕这道题组织讲解</h2>
          <p>{{ plan.teaching_strategy }}</p>
        </div>
      </div>

      <div class="workspace-actions">
        <div>
          <strong>{{ plan.stages.some(stage => stage.teaching_steps?.length) ? '已采用局部调整' : plan.model_analysis ? 'AI 辅助备课' : '基础备课 · 不调用模型' }}</strong>
          <span>查看、演示与保存不消耗 AI 额度。</span>
        </div>
        <button type="button" :disabled="!modelState?.configured" @click="aiPanelOpen = !aiPanelOpen">AI 帮我调整</button>
        <button type="button" class="primary-action" :disabled="savingDraft || generatingAi" @click="saveCurrentPlan">
          {{ savingDraft ? '保存中…' : '保存为备课草稿' }}
        </button>
      </div>
      <section v-if="aiPanelOpen" class="ai-request-panel">
        <div class="section-heading">
          <h2>你想解决什么教学问题？</h2>
          <p>选一选就能生成建议，无需写提示词。建议先预览，由你决定是否采用。</p>
        </div>
        <fieldset :disabled="generatingAi">
          <legend>1. 学生目前遇到了什么？</legend>
          <div class="adjustment-options">
            <label v-for="option in adjustmentGoals" :key="option.value" :class="{ selected: adjustmentGoal === option.value }">
              <input v-model="adjustmentGoal" type="radio" name="adjustment-goal" :value="option.value" />{{ option.label }}
            </label>
          </div>
          <p v-if="adjustmentGoal === 'unsure'" class="choice-note">还不了解学生情况也没关系，先用提问检查理解，不预设学生存在弱点。</p>
          <p v-if="adjustmentGoal === 'challenge'" class="choice-note">增加解释、比较或反推任务；本轮不生成独立的新题入库。</p>
        </fieldset>
        <fieldset :disabled="generatingAi">
          <legend>2. 希望怎样帮助学生理解？</legend>
          <div class="adjustment-options">
            <label v-for="option in adjustmentMethods" :key="option.value" :class="{ selected: adjustmentMethod === option.value }">
              <input v-model="adjustmentMethod" type="radio" name="adjustment-method" :value="option.value" />{{ option.label }}
            </label>
          </div>
          <p v-if="adjustmentMethod === 'visual' || adjustmentMethod === 'hands_on'" class="choice-note">将提供教师活动建议，不会自动生成动画或视频。</p>
        </fieldset>
        <label class="adjustment-field">3. 只调整哪个环节？
          <select v-model="adjustmentStageId" :disabled="generatingAi">
            <option v-for="stage in plan.stages" :key="stage.id" :value="stage.id">{{ stage.title }}</option>
          </select>
        </label>
        <label class="adjustment-field">{{ adjustmentGoal === 'custom' ? '补充你的教学设计（必填）' : '补充课堂情况（选填）' }}
          <textarea v-model="teacherRequest" :disabled="generatingAi" maxlength="1000" rows="3" placeholder="例如：学生分不清顺时针和逆时针，我想先让他用手转一转。请勿填写学生姓名等个人信息。"></textarea>
        </label>
        <label><input v-model="aiConsent" type="checkbox" />同意使用平台 AI 服务，将原题、当前环节和本次选择发送给 {{ modelState?.provider }}；追问也会发送相关对话。</label>
        <p>本站共享内测额度：今日剩余 {{ modelState?.remaining ?? '未知' }} / {{ modelState?.daily_limit ?? '未知' }} 次。生成与追问共用额度。</p>
        <small>北京时间零点重置。失败尝试也计数，不自动重试。预览、采用、放弃和撤销不额外调用模型。</small>
        <button type="button" class="primary-action" :disabled="!canCallAi || !adjustmentReady" @click="runAiAnalysis">{{ generatingAi ? '正在生成调整建议…' : adjustmentPreview ? '重新生成 · 使用 1 次 AI 额度' : '生成调整建议 · 使用 1 次 AI 额度' }}</button>
        <p v-if="generatingAi" class="generation-status" role="status" aria-live="polite">正在调整“{{ adjustmentStage?.title }}”，原稿保持不变，请稍候。</p>

        <section v-if="adjustmentPreview" class="adjustment-preview stage-arrival" aria-label="调整建议预览">
          <header class="preview-heading"><span class="preview-kicker">调整已就绪 · 待你采用</span><h3>{{ adjustmentPreview.before.title }}</h3><p>{{ adjustmentPreview.proposal.rationale }}</p></header>
          <details>
            <summary>对照原稿</summary>
            <p><strong>目标：</strong>{{ adjustmentPreview.before.purpose }}</p>
            <p><strong>追问：</strong>{{ adjustmentPreview.before.teacher_prompt }}</p>
            <p class="preserve-lines"><strong>讲解：</strong>{{ adjustmentPreview.before.teaching_note }}</p>
          </details>
          <div class="lesson-objective"><span>这一环节，要让学生学会</span><p>{{ adjustmentPreview.proposal.objective }}</p></div>
          <TeachingSteps :steps="adjustmentPreview.proposal.steps" />
          <p class="teacher-confirmations"><strong>采用前请核对：</strong>{{ adjustmentPreview.proposal.teacher_check }}</p>
          <div class="editor-actions">
            <button type="button" class="primary-action" @click="applyAdjustment">采用到这个环节</button>
            <button type="button" @click="discardAdjustment">放弃，保留原稿</button>
          </div>
        </section>
      </section>
      <p v-if="adjustmentNotice" role="status" class="success-message">{{ adjustmentNotice }}</p>
      <button v-if="undoAdjustment" type="button" class="secondary-action" :disabled="generatingAi" @click="undoLastAdjustment">撤销上次采用（不消耗额度）</button>
      <p v-if="error" role="alert" class="error-message">{{ error }}</p>
      <p v-if="draftNotice" class="success-message">{{ draftNotice }}</p>

      <article class="problem-card">
        <div class="problem-meta">
          <span>{{ plan.selected_problem.unit_name }}</span>
          <span>{{ plan.selected_problem.difficulty }}</span>
          <span>{{ plan.selected_problem.source_label }}</span>
        </div>
        <h3>{{ plan.selected_problem.title }}</h3>
        <p>{{ plan.selected_problem.statement }}</p>
        <strong>{{ plan.selected_problem.question }}</strong>
        <small>{{ plan.selected_problem.source_status }}</small>
      </article>

      <nav class="stage-tabs" aria-label="教学环节">
        <button
          v-for="(stage, index) in plan.stages"
          :key="stage.id"
          type="button"
          :class="{ active: index === activeStageIndex }"
          @click="activeStageIndex = index"
        >
          <span>{{ index + 1 }}</span>{{ stage.title.replace(/^第.步：/, '') }}
        </button>
      </nav>

      <div :key="activeStage.id" class="teaching-grid stage-arrival" :class="{ 'text-only': !activeStage.cubes.length }">
        <CubeWorkbench
          v-if="activeStage.cubes.length"
          :cubes="activeStage.cubes"
          :projections="activeStage.projections"
        />
        <article class="teacher-notes">
          <span class="note-label">本环节要解决什么</span>
          <h3>{{ activeStage.title }}</h3>
          <p>{{ activeStage.purpose }}</p>
          <TeachingSteps v-if="activeStage.teaching_steps?.length" :steps="activeStage.teaching_steps" />
          <div v-else class="prompt-block">
            <span>课堂先问</span>
            <p>{{ activeStage.teacher_prompt }}</p>
          </div>
          <div v-if="!activeStage.teaching_steps?.length" class="prompt-block secondary">
            <span>讲解动作</span>
            <p>{{ activeStage.teaching_note }}</p>
          </div>
          <details v-else class="stage-notes-details"><summary>完整讲解与教师核对事项</summary><p class="preserve-lines">{{ activeStage.teaching_note }}</p></details>
        </article>
      </div>

      <details v-if="plan.model_analysis" class="analysis-card">
        <summary>展开完整题目分析与依据</summary>
        <div class="section-heading">
          <h2>题目分析</h2>
          <p>由模型提出，已转入固定备课结构，仍需老师核对。</p>
        </div>
        <div class="analysis-grid">
          <div class="analysis-wide"><span>本题覆盖范围</span><p>{{ plan.model_analysis.scope_note }}</p></div>
          <div><span>知识点</span><strong>{{ plan.model_analysis.knowledge_points.join('、') }}</strong></div>
          <div><span>题型</span><strong>{{ plan.model_analysis.problem_type }}</strong></div>
          <div><span>核心方法</span><p>{{ plan.model_analysis.core_method }}</p></div>
          <div><span>主要难点</span><p>{{ plan.model_analysis.difficulty_reasons.join('；') }}</p></div>
          <div><span>常见错误</span><p>{{ plan.model_analysis.common_mistakes.join('；') }}</p></div>
          <div><span>变式方向</span><p>{{ plan.model_analysis.variation_idea }}</p></div>
        </div>
        <div class="evidence-list">
          <article v-for="item in plan.model_analysis.knowledge_evidence" :key="`${item.knowledge_point}-${item.evidence}`">
            <strong>{{ item.knowledge_point }}</strong>
            <p>{{ item.evidence }}</p>
            <small>依据：{{ item.source_ids.join('、') }}</small>
          </article>
        </div>
        <div class="skill-list">
          <article v-for="item in plan.model_analysis.skill_plans" :key="item.skill">
            <strong>{{ item.skill }}</strong>
            <p>观察表现：{{ item.observable_behavior }}</p>
            <p>教学活动：{{ item.teaching_activity }}</p>
            <small>达成标准：{{ item.success_criterion }}</small>
          </article>
        </div>
        <div v-if="plan.model_analysis.teacher_confirmations.length" class="teacher-confirmations">
          <strong>请老师确认</strong>
          <ul><li v-for="item in plan.model_analysis.teacher_confirmations" :key="item">{{ item }}</li></ul>
        </div>
        <small>{{ plan.model_analysis.review_warning }}</small>
      </details>

      <section v-if="aiPanelOpen" class="assistant-card">
        <div class="section-heading">
          <h2>围绕这道题问助教 <small v-if="showModelUsageHints && modelState?.configured" class="model-usage-badge">每次发送调用模型</small></h2>
          <p v-if="modelState?.configured">每次发送使用 1 次 AI 额度。本站今日剩余 {{ modelState.remaining }} 次。请先在“AI 帮我调整”中确认使用平台服务。</p>
          <p v-else>在后端配置模型密钥后开放问答。</p>
        </div>
        <div v-if="chatMessages.length" class="chat-log">
          <p v-for="(message, index) in chatMessages" :key="index" :class="message.role">
            <strong>{{ message.role === 'user' ? '我' : '备课助教' }}</strong>{{ message.content }}
          </p>
        </div>
        <form class="chat-form" @submit.prevent="askAssistant">
          <input v-model="chatInput" maxlength="2000" :disabled="!modelState?.configured" placeholder="例如：这道题学生最容易错在哪里？" />
          <button :disabled="!canCallAi || !chatInput.trim()">
            <span>{{ chatting ? '正在回答…' : '发送 · 使用 1 次额度' }}</span>
            <small v-if="showModelUsageHints && modelState?.configured">调用模型</small>
          </button>
        </form>
      </section>

      <div class="lesson-columns">
        <section>
          <div class="section-heading">
            <h2>接下来可以讲什么</h2>
            <p>这些题和当前题目属于同一课题，老师决定是否加入。</p>
          </div>
          <div v-if="plan.related_problems.length" class="related-list">
            <article v-for="related in plan.related_problems.slice(0, 3)" :key="related.problem.id">
              <div>
                <span>{{ related.relation }}</span>
                <h3>{{ related.problem.title }}</h3>
                <p>{{ related.reason }}</p>
              </div>
              <button type="button" @click="chooseProblem(related.problem)">查看基础方案</button>
            </article>
          </div>
          <p v-else class="empty-state compact">当前还没有合适的关联题。</p>
        </section>

        <section>
          <div class="section-heading">
            <h2>课堂呈现建议</h2>
            <p>选择能帮助学生理解当前难点的方式。</p>
          </div>
          <div class="resource-list">
            <article v-for="resource in plan.resources" :key="resource.kind">
              <h3>{{ resource.title }}</h3>
              <p>{{ resource.why }}</p>
              <strong>{{ resource.action }}</strong>
            </article>
          </div>
        </section>
      </div>
    </section>

    <section v-if="entered && mode === 'drafts'" class="selection-card workspace-page">
      <div class="step-title">
        <span>备</span>
        <div><h1>我的备课</h1><p>继续编辑题目顺序、课堂追问和讲解动作。</p></div>
      </div>
      <p v-if="draftLoading" class="state-message">正在读取草稿…</p>
      <div class="draft-layout">
        <RecordManager title="备课记录" :items="draftSummaries.map(d => ({id:d.id,title:d.title,detail:d.item_count + '道题 · ' + (d.status === 'approved' ? '已确认' : '待确认')}))" :active-id="activeDraft?.id" :busy="draftLoading || deletingRecord" @select="openDraft($event)" @remove="(id,title) => requestRecordDelete('draft',id,title)" />
        <article v-if="activeDraft" class="draft-editor">
          <div class="record-toolbar"><div><small>当前备课草稿</small><strong>{{ activeDraft.title }}</strong></div><button :disabled="draftLoading" @click="saveDraftEdits">保存修改</button><button class="record-danger" :disabled="draftLoading" @click="removeActiveDraft">删除草稿</button></div>
          <label>备课标题<input v-model="activeDraft.title" maxlength="120" /></label>
          <label>整节课备注<textarea v-model="activeDraft.teacher_note" rows="3" maxlength="4000"></textarea></label>
          <div class="draft-add">
            <select v-model="draftAddId">
              <option value="">从同课题选择一道题</option>
              <option
                v-for="problem in draftProblemOptions.filter((candidate) => !activeDraft?.items.some((item) => item.problem.id === candidate.id))"
                :key="problem.id"
                :value="problem.id"
              >{{ problem.title }}</option>
            </select>
            <button :disabled="!draftAddId || activeDraft.items.length >= 12" @click="addProblemToDraft">加入草稿</button>
          </div>
          <div v-for="(item, index) in activeDraft.items" :key="item.id" class="draft-item">
            <header>
              <div><small>第{{ index + 1 }}题</small><h3>{{ item.problem.title }}</h3></div>
              <div class="item-buttons">
                <button :disabled="index === 0" @click="moveDraftItem(index, -1)">上移</button>
                <button :disabled="index === activeDraft.items.length - 1" @click="moveDraftItem(index, 1)">下移</button>
                <button :disabled="activeDraft.items.length === 1" @click="removeDraftItem(index)">移除</button>
              </div>
            </header>
            <p>{{ item.problem.statement }} {{ item.problem.question }}</p>
            <label>题间作用<input v-model="item.relation" maxlength="40" /></label>
            <label>课堂追问<textarea v-model="item.teacher_prompt" rows="2" maxlength="1000"></textarea></label>
            <label>讲解动作<textarea v-model="item.teaching_note" rows="3" maxlength="2000"></textarea></label>
          </div>
          <div class="editor-actions">
            <button class="primary-action" :disabled="draftLoading" @click="saveDraftEdits">保存修改</button>
            <button @click="setDraftStatus(activeDraft.status === 'approved' ? 'pending_review' : 'approved')">
              {{ activeDraft.status === 'approved' ? '改回待确认' : '确认备课稿' }}
            </button>
            <a :href="exportDraftUrl(activeDraft.id, 'teacher')">导出教师版</a>
            <a :href="exportDraftUrl(activeDraft.id, 'student')">导出学生版</a>

          </div>
        </article>
        <div v-else class="empty-state">选择左侧草稿开始编辑。</div>
      </div>
      <p v-if="error" class="error-message">{{ error }}</p>
    </section>

    <section v-if="entered && mode === 'photo'" class="selection-card workspace-page">
      <div class="step-title">
        <span>录</span>
        <div><h1>拍照录题</h1><p>上传单题照片，校对题目文字后查找题库中的同类题。</p></div>
      </div>
      <label class="upload-box">
        <strong>{{ photoBusy ? '处理中…' : '选择 JPG、PNG 或 WebP 单题照片' }}</strong>
        <span>最多 8 MB；图片保存在本机私有目录，不会进入开源仓库。</span>
        <input type="file" accept="image/jpeg,image/png,image/webp" :disabled="photoBusy" @change="handlePhoto" />
      </label>
      <div class="draft-layout">
        <RecordManager title="拍照记录" :items="photos.map(d => ({id:d.id,title:d.original_name,detail:d.status === 'ready' ? '文字已校对' : '等待校对'}))" :active-id="activePhoto?.id" :busy="photoBusy || deletingRecord" @select="photos.find(p => p.id === $event) && openPhoto(photos.find(p => p.id === $event)!)" @remove="(id,title) => requestRecordDelete('photo',id,title)" />
        <article v-if="activePhoto" class="draft-editor">
          <div class="record-toolbar"><div><small>当前拍照记录</small><strong>{{ activePhoto.original_name }}</strong></div><button class="record-danger" :disabled="photoBusy" @click="removeActivePhoto">删除记录</button></div>
          <div class="manual-note"><strong>请人工校对题目文字</strong><p>当前版本不伪造 OCR 结果。请把照片中的完整题干与问题输入下方，再检索同类题。</p></div>
          <label>题目文字<textarea v-model="photoTranscript" rows="8" maxlength="5000" placeholder="输入完整题干和问题"></textarea></label>
          <div class="editor-actions">
            <button class="primary-action" :disabled="photoBusy || !photoTranscript.trim()" @click="saveTranscriptAndSearch">保存并查找同类题</button>

          </div>
          <div v-if="photoResults.length" class="photo-results">
            <h2>题库中的相近题目</h2>
            <button v-for="result in photoResults" :key="result.problem.id" @click="switchMode('library').then(() => chooseProblem(result.problem))">
              <strong>{{ result.problem.title }}</strong><span>{{ result.problem.unit_name }}</span>
            </button>
          </div>
        </article>
        <div v-else class="empty-state">上传或选择一条记录开始整理。</div>
      </div>
      <p v-if="error" class="error-message">{{ error }}</p>
    </section>

    <section v-if="entered && mode === 'feedback'" class="selection-card workspace-page">
      <div class="step-title feedback-heading">
        <span>评</span>
        <div><h1>课后反馈</h1><p>记录课堂事实，整理个人反馈和班群通知。所有判断都由老师确认。</p></div>
        <button type="button" class="secondary-action" @click="resetFeedbackForm">新建反馈</button>
      </div>

      <div class="feedback-layout">
        <StudentRecords :records="feedbackSummaries" :active-id="activeFeedback?.id" :busy="feedbackBusy || deletingRecord" @select="openFeedback($event)" @remove="(id,title) => requestRecordDelete('feedback',id,title)" @create="newStudentFeedback" />

        <div class="feedback-editor">
          <div class="record-toolbar"><div><small>{{ activeFeedback ? '当前反馈档案' : '新建反馈' }}</small><strong>{{ activeFeedback ? activeFeedback.student_name + ' · ' + activeFeedback.topic : '填写并保存课堂记录' }}</strong></div><button :disabled="feedbackBusy || !feedbackReady" @click="saveFeedback">保存课堂记录</button><button v-if="activeFeedback" class="record-danger" :disabled="feedbackBusy" @click="removeActiveFeedback">删除档案</button></div>
      <FeedbackPolish :key="activeFeedback?.id ?? 'new'" :feedback="activeFeedback" :dirty="feedbackDirty" @adopted="onPolishAdopted" @allowance="refreshAllowance" />
          <section class="feedback-form-card">
            <div class="section-heading"><h2>1. 基本信息与实际教学内容</h2><p>这里只记录这节课真实发生的内容。</p></div>
            <div class="field-grid three">
              <label>学生姓名<input v-model="feedbackForm.student_name" maxlength="40" placeholder="用于个人反馈" /></label>
              <label>年级<select v-model.number="feedbackForm.grade"><option v-for="item in grades" :key="item" :value="item">{{ item }}年级</option></select></label>
              <label>上课日期<input v-model="feedbackForm.lesson_date" type="date" /></label>
            </div>
            <label>课题<input v-model="feedbackForm.topic" maxlength="80" placeholder="例如：多角度观察物体" /></label>
            <label>本节实际学习内容<textarea v-model="feedbackForm.actual_content" rows="4" maxlength="3000" placeholder="写清实际讲了哪些内容、做了哪些活动；不要直接复制课前计划。"></textarea></label>
          </section>

          <section class="feedback-form-card">
            <div class="section-heading split-heading">
              <div><h2>2. 有证据的课堂表现</h2><p>写具体任务和完成情况，“未观察”不会被当成“不会”。</p></div>
              <button type="button" class="secondary-action" :disabled="feedbackForm.observations.length >= 8" @click="addObservation">增加一项</button>
            </div>
            <article v-for="(item, index) in feedbackForm.observations" :key="index" class="observation-row">
              <div class="field-grid two">
                <label>观察能力<input v-model="item.skill_area" maxlength="80" placeholder="例如：固定观察方向" /></label>
                <label>完成情况
                  <select v-model="item.performance">
                    <option value="independent">独立完成</option>
                    <option value="prompted">提示后完成</option>
                    <option value="not_yet">暂未完成</option>
                    <option value="not_observed">本节未观察</option>
                  </select>
                </label>
              </div>
              <label>课堂证据<textarea v-model="item.task_evidence" rows="2" maxlength="500" placeholder="在哪道题、哪个步骤中观察到什么"></textarea></label>
              <label>订正结果（选填）<textarea v-model="item.correction_result" rows="2" maxlength="500" placeholder="提示后是否改对，能否解释原因"></textarea></label>
              <button type="button" class="text-danger" :disabled="feedbackForm.observations.length === 1" @click="removeObservation(index)">移除这一项</button>
            </article>
          </section>

          <section class="feedback-form-card">
            <div class="section-heading"><h2>3. 建议、作业与图片</h2><p>建议由老师填写，平台只做整理。</p></div>
            <label>老师建议<textarea v-model="feedbackForm.teacher_advice" rows="3" maxlength="2000" placeholder="下一步重点、练习方法或需要保持的习惯"></textarea></label>
            <label>班群共同提醒（选填）<textarea v-model="feedbackForm.class_reminder" rows="2" maxlength="1000" placeholder="这里只写适合全班家长查看的共性提醒"></textarea></label>
            <div class="homework-list">
              <label v-for="(_, index) in feedbackForm.homework" :key="index">课后作业 {{ index + 1 }}
                <span><input v-model="feedbackForm.homework[index]" maxlength="300" placeholder="页码、题目或复习任务" /><button type="button" :disabled="feedbackForm.homework.length === 1" @click="removeHomework(index)">移除</button></span>
              </label>
              <button type="button" class="secondary-action" :disabled="feedbackForm.homework.length >= 10" @click="addHomework">增加作业</button>
            </div>
            <label class="upload-box compact-upload">
              <strong>{{ feedbackBusy ? '处理中…' : '上传课堂作业图片' }}</strong>
              <span>图片保存在本机私有目录，选择后会附在个人反馈中。</span>
              <input type="file" accept="image/jpeg,image/png,image/webp" :disabled="feedbackBusy" @change="handleFeedbackPhoto" />
            </label>
            <div v-if="photos.length" class="feedback-photo-picker">
              <button
                v-for="photo in photos"
                :key="photo.id"
                type="button"
                :class="{ selected: feedbackForm.photo_ids.includes(photo.id) }"
                @click="toggleFeedbackPhoto(photo.id)"
              >
                <img :src="photoContentUrl(photo.id)" :alt="photo.original_name" />
                <span>{{ photo.original_name }}</span>
              </button>
            </div>
          </section>

          <div class="editor-actions feedback-actions">
            <button type="button" class="primary-action" :disabled="feedbackBusy || !feedbackReady" @click="saveFeedback">
              {{ feedbackBusy ? '保存中…' : activeFeedback ? '保存事实并生成普通版' : '保存并生成普通版' }}
            </button>
            <button v-if="activeFeedback" type="button" :disabled="feedbackBusy || feedbackDirty" @click="setFeedbackStatus(activeFeedback.status === 'approved' ? 'draft' : 'approved')">
              {{ activeFeedback.status === 'approved' ? '改回草稿' : '确认反馈' }}
            </button>
            <a v-if="activeFeedback" :href="exportFeedbackUrl(activeFeedback.id, 'individual')">导出个人反馈</a>
            <a v-if="activeFeedback" :href="exportFeedbackUrl(activeFeedback.id, 'class_group')">导出班群反馈</a>

          </div>
          <p v-if="feedbackNotice" class="success-message">{{ feedbackNotice }}</p>

          <p v-if="activeFeedback" class="success-message">当前保存版本：个人反馈 {{ activeFeedback.ai_audiences.includes('individual') ? 'AI 润色' : '普通整理' }} · 班群通知 {{ activeFeedback.ai_audiences.includes('class_group') ? 'AI 润色' : '普通整理' }}。{{ feedbackDirty ? '还有未保存修改，导出仍为已保存版本。' : '' }}</p>
          <section v-if="activeFeedback" class="feedback-preview-grid">
            <article>
              <span>个人反馈预览</span><pre>{{ activeFeedback.individual_report }}</pre>
              <div v-if="activeFeedback.photos.length" class="feedback-preview-photos">
                <img v-for="photo in activeFeedback.photos" :key="photo.id" :src="photoContentUrl(photo.id)" :alt="photo.original_name" />
              </div>
            </article>
            <article><span>班群反馈预览</span><pre>{{ activeFeedback.class_group_report }}</pre></article>
          </section>
        </div>
      </div>
      <p v-if="error" class="error-message">{{ error }}</p>
    </section>
  </main>
</template>
