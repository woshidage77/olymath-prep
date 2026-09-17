<script setup lang="ts">
import { computed, defineAsyncComponent, nextTick, onMounted, reactive, ref } from 'vue'
import {
  askTeacherAssistant,
  createAiLessonPlan,
  createDraft,
  createLessonPlan,
  deleteDraft,
  deletePhoto,
  exportDraftUrl,
  getCurriculum,
  getDraft,
  getModelStatus,
  listDrafts,
  listPhotos,
  listProblems,
  reviewDraft,
  searchPhoto,
  searchProblems,
  updateDraft,
  updatePhotoTranscript,
  uploadPhoto,
} from './api'
import type {
  CurriculumCatalog,
  CurriculumUnit,
  ChatMessage,
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

const CubeWorkbench = defineAsyncComponent(() => import('./components/CubeWorkbench.vue'))

type ViewMode = 'library' | 'drafts' | 'photo'
type DifficultyFilter = '全部' | '基础' | '进阶' | '挑战'

const grades = [1, 2, 3, 4, 5, 6, 7, 8, 9]
const semesterOptions = ['全部', '上册', '下册'] as const
const difficultyOptions: DifficultyFilter[] = ['全部', '基础', '进阶', '挑战']
const difficultyRank: Record<string, number> = { 基础: 0, 进阶: 1, 挑战: 2 }
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
const modelState = ref<ModelStatus | null>(null)
const generatingAi = ref(false)
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

async function loadCatalog() {
  loadingCatalog.value = true
  error.value = ''
  selectedUnitId.value = null
  problems.value = []
  plan.value = null
  searchResults.value = null
  searchQuery.value = ''
  difficulty.value = '全部'
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
}

function enterWorkspace() {
  entered.value = true
  mode.value = 'library'
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
  brief.grade = problem.grade
  brief.topic = problem.topic
  brief.starting_problem_id = problem.id
  brief.search_query = searchQuery.value.trim() || null
  loadingPlan.value = true
  error.value = ''
  try {
    plan.value = modelState.value?.configured
      ? await createAiLessonPlan(problem.id, brief.search_query)
      : await createLessonPlan(brief)
    activeStageIndex.value = 0
    chatMessages.value = []
    draftNotice.value = ''
    await nextTick()
    document.querySelector('#lesson-workspace')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '备课草稿生成失败'
  } finally {
    loadingPlan.value = false
  }
}

async function switchMode(nextMode: ViewMode) {
  mode.value = nextMode
  error.value = ''
  if (nextMode === 'drafts') await loadDrafts()
  if (nextMode === 'photo') await loadPhotos()
}

async function runAiAnalysis() {
  if (!plan.value || !modelState.value?.configured) return
  generatingAi.value = true
  error.value = ''
  try {
    plan.value = await createAiLessonPlan(plan.value.selected_problem.id, brief.search_query)
    activeStageIndex.value = 0
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '智能分析失败'
  } finally {
    generatingAi.value = false
  }
}

async function askAssistant() {
  const message = chatInput.value.trim()
  if (!message || !plan.value || chatting.value) return
  const history = [...chatMessages.value]
  chatMessages.value.push({ role: 'user', content: message })
  chatInput.value = ''
  chatting.value = true
  error.value = ''
  try {
    const answer = await askTeacherAssistant(plan.value.selected_problem.id, message, history)
    chatMessages.value.push({ role: 'assistant', content: answer })
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '智能助教回答失败'
  } finally {
    chatting.value = false
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

async function removeActiveDraft() {
  if (!activeDraft.value) return
  await deleteDraft(activeDraft.value.id)
  activeDraft.value = null
  await loadDrafts()
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

async function removeActivePhoto() {
  if (!activePhoto.value) return
  await deletePhoto(activePhoto.value.id)
  activePhoto.value = null
  photoTranscript.value = ''
  photoResults.value = []
  await loadPhotos()
}

onMounted(async () => {
  await Promise.all([loadCatalog(), getModelStatus().then((value) => { modelState.value = value })])
})
</script>

<template>
  <header class="site-header" :class="{ 'landing-header': !entered }">
    <a class="brand" href="#" @click.prevent="goHome">
      <span class="brand-mark">一朵</span>
      <span><strong>一朵教学</strong><small>教师备课工作台</small></span>
    </a>
    <nav v-if="entered" class="main-nav" aria-label="主要功能">
      <button :class="{ active: mode === 'library' }" @click="switchMode('library')">题库备课</button>
      <button :class="{ active: mode === 'drafts' }" @click="switchMode('drafts')">我的备课</button>
      <button :class="{ active: mode === 'photo' }" @click="switchMode('photo')">拍照录题</button>
    </nav>
    <template v-else>
      <nav class="home-nav" aria-label="首页导航"><a href="#preparation">备课方式</a><a href="#subjects">学科专题</a><a href="#questions">常见问题</a></nav>
      <button type="button" class="header-entry" @click="enterWorkspace">进入工作台 <span aria-hidden="true">↗</span></button>
    </template>
  </header>

  <main :class="{ 'landing-main': !entered }">
    <LandingPage v-if="!entered" @enter="enterWorkspace" @destination="openHomeDestination" @topic="openHomeTopic" />

    <section v-else-if="mode === 'library'" class="selection-card" aria-labelledby="selection-title">
      <div class="step-title">
        <span>01</span>
        <div>
          <h1 id="selection-title">选择备课专题</h1>
          <p>先确定年级和专题，再按难度选择本节课的起始题。</p>
        </div>
      </div>

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
            <span class="open-label">备这道题 →</span>
          </button>
        </div>
      </template>
      <p v-if="error" class="error-message">{{ error }}</p>
    </section>

    <section v-if="entered && mode === 'library' && plan && activeStage" id="lesson-workspace" class="lesson-workspace">
      <div class="step-title">
        <span>2</span>
        <div>
          <h2>围绕这道题组织讲解</h2>
          <p>{{ plan.teaching_strategy }}</p>
        </div>
      </div>

      <div class="workspace-actions">
        <div>
          <strong>{{ modelState?.configured ? '智能助教已开启' : '当前使用基础备课逻辑' }}</strong>
          <span v-if="!modelState?.configured">配置模型后可自动识别知识点并实时追问。</span>
          <span v-else>知识点分析会经过 Graph 整理成可编辑备课资料。</span>
        </div>
        <button
          v-if="modelState?.configured && !plan.model_analysis"
          type="button"
          :disabled="generatingAi"
          @click="runAiAnalysis"
        >{{ generatingAi ? '分析中…' : 'AI 分析这道题' }}</button>
        <button type="button" class="primary-action" :disabled="savingDraft" @click="saveCurrentPlan">
          {{ savingDraft ? '保存中…' : '保存为备课草稿' }}
        </button>
      </div>
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

      <div class="teaching-grid" :class="{ 'text-only': !activeStage.cubes.length }">
        <CubeWorkbench
          v-if="activeStage.cubes.length"
          :cubes="activeStage.cubes"
          :projections="activeStage.projections"
        />
        <article class="teacher-notes">
          <span class="note-label">本环节要解决什么</span>
          <h3>{{ activeStage.title }}</h3>
          <p>{{ activeStage.purpose }}</p>
          <div class="prompt-block">
            <span>课堂先问</span>
            <p>{{ activeStage.teacher_prompt }}</p>
          </div>
          <div class="prompt-block secondary">
            <span>讲解动作</span>
            <p>{{ activeStage.teaching_note }}</p>
          </div>
        </article>
      </div>

      <section v-if="plan.model_analysis" class="analysis-card">
        <div class="section-heading">
          <h2>题目分析</h2>
          <p>由模型提出，已转入固定备课结构，仍需老师核对。</p>
        </div>
        <div class="analysis-grid">
          <div><span>知识点</span><strong>{{ plan.model_analysis.knowledge_points.join('、') }}</strong></div>
          <div><span>题型</span><strong>{{ plan.model_analysis.problem_type }}</strong></div>
          <div><span>核心方法</span><p>{{ plan.model_analysis.core_method }}</p></div>
          <div><span>主要难点</span><p>{{ plan.model_analysis.difficulty_reasons.join('；') }}</p></div>
          <div><span>常见错误</span><p>{{ plan.model_analysis.common_mistakes.join('；') }}</p></div>
          <div><span>变式方向</span><p>{{ plan.model_analysis.variation_idea }}</p></div>
        </div>
        <small>{{ plan.model_analysis.review_warning }}</small>
      </section>

      <section class="assistant-card">
        <div class="section-heading">
          <h2>围绕这道题问助教</h2>
          <p v-if="modelState?.configured">可以继续问讲解顺序、追问方式、易错点和变式。</p>
          <p v-else>在后端配置模型密钥后开放问答。</p>
        </div>
        <div v-if="chatMessages.length" class="chat-log">
          <p v-for="(message, index) in chatMessages" :key="index" :class="message.role">
            <strong>{{ message.role === 'user' ? '我' : '备课助教' }}</strong>{{ message.content }}
          </p>
        </div>
        <form class="chat-form" @submit.prevent="askAssistant">
          <input v-model="chatInput" maxlength="2000" :disabled="!modelState?.configured" placeholder="例如：这道题学生最容易错在哪里？" />
          <button :disabled="!modelState?.configured || chatting || !chatInput.trim()">
            {{ chatting ? '思考中…' : '发送' }}
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
              <button type="button" @click="chooseProblem(related.problem)">查看备课</button>
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
        <aside class="record-list">
          <button v-for="draft in draftSummaries" :key="draft.id" :class="{ active: activeDraft?.id === draft.id }" @click="openDraft(draft.id)">
            <strong>{{ draft.title }}</strong>
            <span>{{ draft.item_count }}道题 · {{ draft.status === 'approved' ? '已确认' : '待确认' }}</span>
          </button>
          <p v-if="!draftSummaries.length && !draftLoading" class="empty-state compact">还没有草稿，请先从题库保存一份。</p>
        </aside>
        <article v-if="activeDraft" class="draft-editor">
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
            <button class="danger" @click="removeActiveDraft">删除</button>
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
        <aside class="record-list">
          <button v-for="photo in photos" :key="photo.id" :class="{ active: activePhoto?.id === photo.id }" @click="openPhoto(photo)">
            <strong>{{ photo.original_name }}</strong>
            <span>{{ photo.status === 'ready' ? '文字已校对' : '等待校对' }} · {{ photo.width }}×{{ photo.height }}</span>
          </button>
        </aside>
        <article v-if="activePhoto" class="draft-editor">
          <div class="manual-note"><strong>请人工校对题目文字</strong><p>当前版本不伪造 OCR 结果。请把照片中的完整题干与问题输入下方，再检索同类题。</p></div>
          <label>题目文字<textarea v-model="photoTranscript" rows="8" maxlength="5000" placeholder="输入完整题干和问题"></textarea></label>
          <div class="editor-actions">
            <button class="primary-action" :disabled="photoBusy || !photoTranscript.trim()" @click="saveTranscriptAndSearch">保存并查找同类题</button>
            <button class="danger" @click="removeActivePhoto">删除记录</button>
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
  </main>
</template>
