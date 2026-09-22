<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { getModelStatus } from '../api'
import type { AfterClassFeedback, ModelStatus } from '../types'
const props = defineProps<{ feedback: AfterClassFeedback | null; dirty: boolean }>()
const emit = defineEmits<{ adopted: [feedback: AfterClassFeedback]; allowance: [] }>()
type Audience = 'individual' | 'class_group'
interface Proposal {
  status: 'ready' | 'needs_input'; proposal_id: string | null; source_version: number
  audience: Audience; report: string; questions_for_teacher: string[]
  evidence: Record<string, string>; paragraphs: { evidence_id: string; text: string }[]
}
const mode = ref<'ordinary' | 'ai'>('ordinary')
const audience = ref<Audience>('individual')
const consent = ref(false)
const groupConfirmed = ref(false)
const reviewed = ref(false)
const busy = ref(false)
const notice = ref('')
const status = ref<ModelStatus | null>(null)
const proposal = ref<Proposal | null>(null)
let mounted = true
onBeforeUnmount(() => { mounted = false })
const identity = computed(() => JSON.stringify([props.feedback?.id, props.feedback?.version, props.dirty, audience.value, groupConfirmed.value]))
watch(identity, () => { proposal.value = null; reviewed.value = false; notice.value = '' })
watch(mode, async (value) => {
  if (value !== 'ai') return
  try { status.value = await getModelStatus() } catch { notice.value = '暂时无法读取 AI 服务状态，请稍后重试。' }
})
const original = computed(() => audience.value === 'individual'
  ? props.feedback?.ordinary_individual_report : props.feedback?.ordinary_class_group_report)
const canGenerate = computed(() => props.feedback && !props.dirty && !busy.value && consent.value
  && status.value?.configured && status.value.remaining > 0 && (audience.value !== 'class_group' || groupConfirmed.value))
async function request(method: string, data: object) {
  const response = await fetch('/api/feedback/' + encodeURIComponent(props.feedback!.id) + '/polish', {
    method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(typeof body?.detail === 'string' ? body.detail : '操作未完成，请检查输入或重新打开记录。')
  }
  return response.json()
}
async function generate() {
  if (!canGenerate.value || !props.feedback) return
  const signature = identity.value
  busy.value = true; proposal.value = null; reviewed.value = false; notice.value = ''
  try {
    const result = await request('POST', { expected_version: props.feedback.version, audience: audience.value,
      consent: consent.value, group_content_confirmed: groupConfirmed.value }) as Proposal
    if (!mounted || signature !== identity.value) return
    proposal.value = result
  } catch (error) { if (mounted) notice.value = error instanceof Error ? error.message : '润色失败，原稿保留。' }
  finally {
    busy.value = false
    emit('allowance')
    try { if (mounted) status.value = await getModelStatus() } catch { if (mounted) status.value = null }
  }
}
async function adopt(reset = false) {
  if (!props.feedback || props.dirty || busy.value || (!reset && (!proposal.value?.proposal_id || !reviewed.value))) return
  const signature = identity.value
  busy.value = true; notice.value = ''
  try {
    const result = await request('PUT', { expected_version: props.feedback.version, audience: audience.value,
      proposal_id: reset ? null : proposal.value!.proposal_id, reviewed: reset || reviewed.value }) as AfterClassFeedback
    if (!mounted || signature !== identity.value) return
    emit('adopted', result); proposal.value = null; reviewed.value = false
  } catch (error) { notice.value = error instanceof Error ? error.message : '采用失败，原稿保留。' }
  finally { busy.value = false }
}
</script>
<template>
 <section class="feedback-polish">
  <div class="polish-mode" aria-label="反馈整理方式">
   <button :aria-pressed="mode === 'ordinary'" :disabled="busy" @click="mode='ordinary'">普通整理 <small>不调用模型</small></button>
   <button :aria-pressed="mode === 'ai'" :disabled="busy" @click="mode='ai'">AI 润色 <small>主动生成才使用额度</small></button>
  </div>
  <p v-if="mode === 'ordinary'">按下方表单记录真实课堂情况，保存后生成固定格式反馈。已采用的 AI 版本会保留；修改并保存课堂事实后将恢复普通版。</p>
  <div v-else class="stage-arrival">
   <h3>事实由你记录，表达交给 AI 整理</h3>
   <p>先保存下方课堂记录，再选择一份反馈润色。不会自动发送给家长。</p>
   <p v-if="!feedback || dirty" class="polish-warning">请先保存课堂记录；未保存的修改不会发送给模型。</p>
   <label>润色哪一份？<select v-model="audience" :disabled="busy"><option value="individual">个人反馈</option><option value="class_group">班群通知</option></select></label>
   <label v-if="audience === 'class_group'"><input v-model="groupConfirmed" :disabled="busy" type="checkbox" />我确认“本节实际学习内容”属于全班共同授课内容，且不含个体信息。</label>
   <label><input v-model="consent" :disabled="busy" type="checkbox" />同意将相关课堂文字发送给 {{ status?.provider || '平台模型服务' }}。请勿在自由文本中填写其他学生的姓名等个人信息。</label>
   <small>个人版发送学习内容、表现和老师建议；群发版仅发送学习内容。姓名字段、作业、照片和班群提醒不发送。</small>
   <p>本站今日剩余 {{ status?.remaining ?? '未知' }} 次共享额度。每次润色使用 1 次，失败也计数；采用和恢复普通版不调用模型。</p>
   <p v-if="status && !status.configured" class="polish-warning">尚未配置模型，普通整理仍可使用。</p>
   <div class="editor-actions"><button class="primary-action" :disabled="!canGenerate" @click="generate">{{ busy ? '处理中…' : '生成润色预览 · 使用 1 次额度' }}</button>
    <button v-if="feedback?.ai_audiences.includes(audience)" :disabled="busy || dirty" @click="adopt(true)">将这一份恢复为普通版</button></div>
   <p v-if="busy" role="status" class="generation-status">正在处理，请稍候。已有内容保留，结果需由你核对。</p>
   <p v-if="notice" role="alert">{{ notice }}</p>
   <div v-if="proposal?.status === 'needs_input'" class="polish-warning"><strong>请先补充课堂事实</strong><ul><li v-for="question in proposal.questions_for_teacher" :key="question">{{ question }}</li></ul></div>
   <section v-if="proposal?.status === 'ready'" class="polish-result stage-arrival">
    <h3>润色预览 · 尚未采用</h3>
    <details><summary>对照普通版</summary><pre>{{ original }}</pre></details>
    <pre class="polish-report">{{ proposal.report }}</pre>
    <p>作业清单按原文保留；个人作业图片继续使用已选择的附件。群发版不附个人图片，也不自动宣称消息已发送。</p>
    <details><summary>逐段核对原始事实</summary><article v-for="item in proposal.paragraphs" :key="item.evidence_id"><p><strong>原始记录：</strong>{{ proposal.evidence[item.evidence_id] }}</p><p><strong>润色：</strong>{{ item.text }}</p></article></details>
    <label><input v-model="reviewed" type="checkbox" />我已核对表现条件、教学事实和措辞，确认没有夸大或遗漏。</label>
    <div class="editor-actions"><button class="primary-action" :disabled="busy || dirty || !reviewed" @click="adopt()">采用并保存为反馈草稿</button><button :disabled="busy" @click="proposal=null">放弃，保留原稿</button></div>
   </section>
  </div>
 </section>
</template>
<style scoped>
.feedback-polish { padding:24px; margin:22px 0; background:#f5f7ed; border:1px solid #d8e1ce; border-radius:14px; }
.polish-mode { display:flex; gap:12px; flex-wrap:wrap; }
.polish-mode button { display:grid; text-align:left; gap:7px; background:white; border:1px solid #d2ddc8; border-radius:9px; padding:14px 20px; color:#234937; }
.polish-mode button[aria-pressed=true] { background:#244d39; color:white; }
.polish-mode small { font-size:11px; opacity:.8; }
.feedback-polish p { font-size:14px; line-height:1.85; }
.feedback-polish label { display:block; margin:16px 0; font-size:14px; line-height:1.8; }
.feedback-polish select { margin-left:12px; padding:8px; }
.feedback-polish small { line-height:1.8; }
.polish-warning { padding:14px; background:#faf0dc; border-radius:7px; }
.polish-result { margin-top:22px; background:#fffefa; border:1px solid #d8dfce; padding:24px; border-radius:10px; }
.polish-result pre { white-space:pre-wrap; font-family:inherit; font-size:15px; line-height:2; overflow-wrap:anywhere; }
.polish-report { color:#274637; padding:16px 0; }
.polish-result summary { cursor:pointer; color:#587653; padding:12px 0; }
.polish-result article { border-bottom:1px solid #e3e8dd; }
</style>
