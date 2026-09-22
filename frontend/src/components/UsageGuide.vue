<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
const props = defineProps<{ introductory?: boolean }>()
const emit = defineEmits<{ close: [] }>()
const dialog = ref<HTMLDialogElement>()
const index = ref(0)
const quiet = ref(false)
const storageNotice = ref('')
const previousFocus = document.activeElement as HTMLElement | null
const chapters = [
 { name:'从这里开始', title:'一堂课的准备，可以很有章法。', intro:'一朵教学帮助老师把题目、概念、讲解和反馈连起来。你始终决定教什么、怎么教。', flow:['找到起始题','整理教学思路','保存与课后反馈'], steps:['先进入「题库备课」，选年级、单元和难度。当前内容主要覆盖五年级数学。','打开题目即可得到基础方案；不必配置或调用模型，也能查看、整理和保存。','需要针对学生调整时，再主动使用 AI。先预览，由老师核对和采用。'], tip:'本窗口是操作示意，切换章节不会调用模型，也不会修改你的备课稿。' },
 { name:'题库与检索', title:'先找到值得讲的那道题。', intro:'按教学专题组织材料，从基础起点逐步走向巩固与挑战。', flow:['年级 / 单元','难度 / 关键词','打开基础方案'], steps:['进入「题库备课」，选择年级和上下册单元；未开放年级会显示整理中。','在专题内选择基础、进阶或挑战，也可以输入关键词搜索。推荐起点置顶，便于快速开始。','点击题目进入备课页。查看题干、来源和审核状态；关联题目可从「接下来可以讲什么」继续打开。'], tip:'相近题目只是备选材料，老师仍需检查题意、难度和前后衔接。' },
 { name:'讲解与演示', title:'从原题出发，再回到原题。', intro:'每道题沿着三个教学环节组织，避免只看答案而忽略学生怎么理解。', flow:['先做原题','理解概念','回到原题'], steps:['点教学环节切换内容，查看本环节目标、课堂追问与讲解动作。','支持组合体模型的题目可以旋转观察，并对照三视图；其他专题主要提供文字讲解建议。','用追问引出概念，再回到原题检查学生是否能解释方法。完整分析与核对事项可按需展开。'], tip:'当前并非所有专题都有交互演示；图示建议不等于已生成动画、建模或视频。' },
 { name:'AI 局部调整', title:'描述学生的困难，不必编写提示词。', intro:'把教学意图交给平台组织，保留老师自己的判断。', flow:['选困难与方式','生成 → 预览','采用 / 放弃 / 撤销'], steps:['在题目页点「AI 帮我调整」，选择学生的困难、教学方式和目标环节。普通选项无需补充文字；自定义教学设计需要填写。','确认使用平台服务后，点击「生成调整建议」。等待期间原稿保留；结果按提问、学生动作和理解检查展示。','检查建议后点「采用到这个环节」，或放弃保留原稿。可以撤销上次采用；采用后再保存草稿。','「围绕这道题问助教」可继续追问。每次发送也调用模型，不会自动把回答写入备课稿。'], tip:'生成和追问消耗共享额度；采用、放弃、撤销不额外调用模型。失败尝试也计数；不足时仍能使用基础功能。' },
 { name:'草稿与导出', title:'把好思路留成下一次的起点。', intro:'备课稿是可以反复修改的教学材料，而不是一次性的生成结果。', flow:['保存为草稿','编辑题序与追问','确认 / 导出'], steps:['在题目页点击「保存为备课草稿」，再到「我的备课」打开记录。','修改标题、整节课备注、课堂追问、讲解动作和题间作用；可加入同课题题目、上移下移或移除。每份草稿最多 12 道题。','点击「保存修改」再导出。核对后可标记为已确认，也可以改回待确认。','教师版用于讲解准备，学生版用于练习。可在左侧记录列表搜索并直接删除，也可用当前记录顶部的管理栏；删除前会显示名称并要求确认。离开前保存编辑内容。'], tip:'点击采用不等于已经保存。导出前先保存，确保文件包含最新修改。' },
 { name:'拍照录题', title:'把手边的题目带进备课流程。', intro:'先留存材料，再校对题干，最后查找同类题。', flow:['上传单题照片','人工录入 / 校对','检索相近题目'], steps:['进入「拍照录题」，选择 JPG、PNG 或 WebP 单题照片，文件不超过 8 MB。','当前版本需要老师手动输入完整题干和问题，不会自动识别照片中的文字或图形。','点击「保存并查找同类题」，从相近题目进入基础备课。历史记录可以重新选择、校对或删除。'], tip:'上传的照片保存在当前部署的私有存储中，不会自动成为公开题库或进入开源仓库。' },
 { name:'课后反馈', title:'先记录事实，再组织给家长的话。', intro:'平台帮助规范格式；表现、困难和建议必须来自老师真实观察。', flow:['填写课堂事实','附作业与任务','核对 / 导出反馈'], steps:['进入「课后反馈」，左侧按姓名归组，点开学生查看历次课堂；可为这位学生新建反馈并自动填写姓名、最近年级。也可直接新建记录，填写日期、专题及实际教学内容。同名不同人请添加区分标记。','根据表单记录表现、困难、订正情况和老师建议；不要用泛泛评价代替具体事实。','添加课后作业，可上传课堂作业图片或选择已有图片，作为个人反馈附件。','保存后得到普通版；也可打开「AI 润色」，选择个人反馈或班群通知、确认使用模型后生成预览。核对原始事实再采用并保存；修改事实后旧润色失效。确认无误再导出，由老师自行发送。'], tip:'当前反馈按老师填写的内容整理，不自动诊断图片中的学生弱点，也不会自动发送给家长。' },
 { name:'额度与常见问题', title:'知道什么时候调用，使用更安心。', intro:'基础备课随时可用，模型服务由你主动触发。', flow:['基础功能不调用模型','主动生成 / 追问','查看剩余额度'], steps:['浏览、搜索、基础方案、演示、草稿编辑和普通反馈整理不调用模型；反馈 AI 润色每次生成使用 1 次共享额度。使用指南内的动画也不调用模型。','AI 服务需要后端已配置模型且有剩余额度，并勾选确认。本站为部署共享额度，并非每位老师各自拥有一份。','请求失败先看页面提示。失败尝试也计数，不要连续重复提交；原稿不会因为失败被覆盖。','不要在 AI 补充说明中填写学生姓名等个人信息。题目与建议须由老师审核；开源许可证不等于第三方题目可任意传播。','当前没有跨设备账号同步保证。私有记录依赖当前部署保存，重要材料建议导出留存。'], tip:'勾选下方「不再自动提醒」只影响当前浏览器；仍可随时从首页或导航打开完整指南。' }
]
const current = computed(() => chapters[index.value]!)
function remember() {
  try { localStorage.setItem('yiduo.guide.quiet.v1', String(quiet.value)); storageNotice.value = '' }
  catch { storageNotice.value = '浏览器无法保存偏好，本次关闭仍有效。' }
}
function move(delta: number) { index.value = Math.max(0, Math.min(chapters.length - 1, index.value + delta)) }
onMounted(async () => {
  try { quiet.value = localStorage.getItem('yiduo.guide.quiet.v1') === 'true' } catch { storageNotice.value = '当前浏览器不支持保存提醒偏好。' }
  await nextTick()
  dialog.value?.showModal()
})
onBeforeUnmount(() => { dialog.value?.close(); if (previousFocus?.isConnected) previousFocus.focus() })
</script>

<template>
 <dialog ref="dialog" class="usage-guide" aria-labelledby="usage-guide-title" @cancel.prevent="emit('close')">
  <header class="guide-header"><div><span>一朵教学 / FIELD GUIDE</span><h2 id="usage-guide-title">{{ props.introductory ? '欢迎，先用一分钟认识工作台' : '使用指南' }}</h2></div><button type="button" aria-label="关闭使用指南" @click="emit('close')">关闭 ×</button></header>
  <div class="guide-layout">
   <nav aria-label="使用指南章节"><button v-for="(chapter, i) in chapters" :key="chapter.name" :aria-current="index === i ? 'step' : undefined" :class="{ active:index === i }" @click="index=i"><span>{{ String(i+1).padStart(2,'0') }}</span>{{ chapter.name }}</button></nav>
   <article :key="index" class="guide-chapter stage-arrival">
    <span class="guide-eyebrow">使用手册 · {{ index + 1 }} / {{ chapters.length }}</span><h3>{{ current.title }}</h3><p class="guide-intro">{{ current.intro }}</p>
    <div class="guide-animation" aria-label="流程示意"><span class="guide-demo-label">操作示意 · 不调用模型</span><div class="guide-flow"><div v-for="(label,i) in current.flow" :key="label" :style="{ '--beat': i }"><span>{{ i+1 }}</span><strong>{{ label }}</strong></div></div><div class="guide-track" aria-hidden="true"><i /></div></div>
    <ol class="guide-instructions"><li v-for="step in current.steps" :key="step">{{ step }}</li></ol>
    <aside class="guide-tip"><strong>使用时留意</strong><p>{{ current.tip }}</p></aside>
   </article>
  </div>
  <footer class="guide-footer"><div><label><input v-model="quiet" type="checkbox" @change="remember" /> 不再自动提醒</label><small v-if="storageNotice" role="status">{{ storageNotice }}</small></div><div class="guide-controls"><button :disabled="index === 0" @click="move(-1)">上一章</button><button v-if="index < chapters.length-1" class="primary-action" @click="move(1)">下一章 →</button><button v-else class="primary-action" @click="emit('close')">完成，回到平台</button><button v-if="props.introductory" @click="emit('close')">跳过引导</button></div></footer>
 </dialog>
</template>

<style scoped>
.usage-guide { padding:0; width:min(1020px,94vw); max-height:90dvh; border:1px solid #c4d0bc; border-radius:20px; background:#fafbf6; color:#223e32; box-shadow:0 32px 100px #102e3655; overflow:auto; }
.usage-guide::backdrop { background:#102d36a6; backdrop-filter:blur(7px); }
.guide-header { padding:25px 30px; display:flex; justify-content:space-between; gap:20px; border-bottom:1px solid #dce3d4; background:#f2f5e9; }
.guide-header span,.guide-eyebrow { font-size:11px; letter-spacing:.13em; color:#6c8066; }
.guide-header h2 { margin:8px 0 0; font-size:22px; }
button { border:1px solid #cfdbca; background:#fff; color:#294b38; padding:10px 14px; border-radius:8px; }
button:focus-visible { outline:3px solid #9eb46e; outline-offset:3px; }
button:disabled { opacity:.4; cursor:default; }
.guide-header button { align-self:center; }
.guide-layout { display:grid; grid-template-columns:195px minmax(0,1fr); }
nav { padding:22px 14px; border-right:1px solid #dce3d4; background:#f4f6ee; display:flex; flex-direction:column; gap:7px; }
nav button { text-align:left; background:transparent; border-color:transparent; font-size:14px; }
nav button span { margin-right:12px; font-size:11px; opacity:.6; }
nav button.active { background:#244d39; color:white; box-shadow:0 5px 14px #234a391c; }
.guide-chapter { padding:30px 36px; min-width:0; }
.guide-chapter h3 { font-size:27px; line-height:1.4; margin:12px 0; letter-spacing:-.03em; }
.guide-intro { font-size:14px; line-height:1.8; color:#6a7869; }
.guide-animation { margin:22px 0; padding:18px; background:linear-gradient(125deg,#163c32,#386348); border-radius:14px; color:#f5fae9; overflow:hidden; }
.guide-demo-label { font-size:10px; opacity:.65; letter-spacing:.08em; }
.guide-flow { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; margin:20px 0; }
.guide-flow > div { border:1px solid #aabe9166; border-radius:9px; padding:13px 10px; background:#ffffff0a; animation:guide-card .55s both; animation-delay:calc(var(--beat) * .16s); }
.guide-flow span { display:block; font:italic 22px Georgia,serif; color:#d4db9a; margin-bottom:12px; }
.guide-flow strong { font-size:12px; line-height:1.7; display:block; }
.guide-track { height:3px; background:#ffffff20; border-radius:3px; }
.guide-track i { display:block; height:100%; background:#d3df9b; transform-origin:left; animation:guide-progress 1.3s ease-out both; }
.guide-instructions { padding-left:22px; margin:24px 0; }
.guide-instructions li { padding-left:8px; margin:13px 0; font-size:14px; line-height:1.9; }
.guide-instructions li::marker { color:#789359; font-weight:700; }
.guide-tip { padding:15px 18px; background:#f0eedf; border-left:3px solid #b6a36c; border-radius:0 7px 7px 0; font-size:12px; line-height:1.8; }
.guide-tip p { margin:4px 0 0; }
.guide-footer { position:sticky; bottom:0; z-index:2; box-shadow:0 -8px 24px #244d3908; padding:18px 26px; border-top:1px solid #dce3d4; display:flex; align-items:center; justify-content:space-between; gap:18px; background:#fafbf6; }
.guide-footer label { font-size:12px; }
.guide-footer small { display:block; font-size:11px; color:#95623d; }
.guide-controls { display:flex; gap:8px; flex-wrap:wrap; }
.primary-action { background:#244d39; color:white; }
@keyframes guide-card { from { opacity:0; transform:translateY(14px) scale(.97); } to { opacity:1; transform:none; } }
@keyframes guide-progress { from { transform:scaleX(0); } to { transform:scaleX(1); } }
@media(max-width:700px) { .guide-layout { display:block; } nav { flex-direction:row; overflow-x:auto; padding:12px; border-right:0; } nav button { white-space:nowrap; } .guide-chapter { padding:22px; } .guide-chapter h3 { font-size:23px; } .guide-header { padding:20px; } .guide-header h2 { font-size:18px; } .guide-footer { flex-direction:column; align-items:stretch; padding:18px; } .guide-flow { gap:6px; } }
@media(prefers-reduced-motion:reduce) { .guide-flow > div,.guide-track i { animation:none; } }
</style>
