<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { FeedbackSummary } from '../types'
import { groupStudentRecords } from '../studentRecords'
import RecordManager from './RecordManager.vue'
const props = defineProps<{ records:FeedbackSummary[]; activeId?:string; busy:boolean }>()
const emit = defineEmits<{ select:[id:string]; remove:[id:string,title:string]; create:[name:string,grade:number] }>()
const query = ref('')
const selectedName = ref<string | null>(null)
const groups = computed(() => groupStudentRecords(props.records))
const selected = computed(() => groups.value.find(group => group.name === selectedName.value))
const filtered = computed(() => {
 const text=query.value.trim().toLocaleLowerCase()
 return groups.value.filter(group => (group.name + ' ' + group.records.map(item => item.topic + ' ' + item.lesson_date).join(' ')).toLocaleLowerCase().includes(text))
})
watch(() => props.activeId, id => {
 const record=props.records.find(item => item.id === id)
 if(record) selectedName.value=record.student_name.trim()
})
// Reconcile after save/rename/deleting the last record without changing the edited record.
watch(groups, () => {
 if(props.activeId) {
  const record=props.records.find(item => item.id === props.activeId)
  if(record) selectedName.value=record.student_name.trim()
 }
 if(selectedName.value !== null && !groups.value.some(group => group.name === selectedName.value)) selectedName.value=null
})
</script>
<template>
 <aside class="student-archive" aria-label="按学生管理反馈">
  <template v-if="!selected">
   <header><h2>学生反馈档案</h2><small>{{ groups.length }} 个姓名组 · {{ records.length }} 份</small></header>
   <input v-model="query" type="search" aria-label="搜索学生、课题或日期" placeholder="搜索学生、课题或日期…" />
   <p class="archive-hint">同名记录自动收在一起，点击学生查看历次课堂。</p>
   <div class="student-groups">
    <button v-for="group in filtered" :key="group.name" :disabled="busy" class="student-group" @click="selectedName=group.name; emit('select',group.records[0]!.id)">
     <span class="student-avatar" aria-hidden="true">{{ group.name.slice(0,1) }}</span>
     <span><strong>{{ group.name }}</strong><small>{{ group.records.length }} 次课堂记录</small><small>最近 {{ group.latestDate }}</small></span><b aria-hidden="true">›</b>
    </button>
    <p v-if="!filtered.length">{{ busy ? '正在读取…' : records.length ? '没有匹配的学生或课堂。' : '保存第一份反馈后，会自动生成姓名分组。' }}</p>
   </div>
   <details class="archive-hint"><summary>遇到同名学生怎么办？</summary><p>目前按姓名归组，不代表已经识别为同一个人。同名不同人请在姓名中加上班级等区分标记；既有相关记录也需保持一致。这里不会合并或删除课堂记录。</p></details>
  </template>
  <template v-else>
   <button class="archive-back" @click="selectedName=null;query=''">← 全部学生</button>
   <header><h2>{{ selected.name }}</h2><small>{{ selected.records.length }} 次课堂</small></header>
   <button class="archive-create" :disabled="busy" @click="emit('create', selected.name, selected.grade)">＋ 为这位学生新建反馈</button>
   <p class="archive-hint">按上课日期倒序。删除仅影响选中的这一节课。</p>
   <RecordManager title="历次课堂记录" :items="selected.records.map(item => ({id:item.id,title:item.topic,detail:item.lesson_date + ' · ' + item.grade + '年级 · ' + (item.status === 'approved' ? '已确认' : '草稿')}))" :active-id="activeId" :busy="busy" @select="emit('select',$event)" @remove="(id,title) => emit('remove',id,selected!.name + ' · ' + title + ' · ' + selected!.records.find(item => item.id === id)!.lesson_date)" />
  </template>
 </aside>
</template>
<style scoped>
.student-archive { align-self:start; min-width:0; padding:16px; background:#f7f9f3; border:1px solid #d9e3d2; border-radius:12px; }
header { display:flex; flex-wrap:wrap; gap:8px; align-items:center; justify-content:space-between; margin-bottom:16px; }
h2 { font-size:16px; margin:0; overflow-wrap:anywhere; }
small,.archive-hint { font-size:12px; color:#6d7c68; line-height:1.8; }
input { box-sizing:border-box; width:100%; padding:10px; font:inherit; border:1px solid #cfdac5; border-radius:7px; }
.student-groups { display:grid; gap:9px; max-height:60vh; overflow:auto; }
.student-group { display:flex; align-items:center; gap:10px; padding:14px 10px; border:1px solid #dce5d5; border-radius:9px; background:white; text-align:left; color:#2a4e39; }
.student-group > span:nth-child(2) { flex:1; min-width:0; display:grid; gap:3px; overflow-wrap:anywhere; }
.student-group strong { font-size:14px; }
.student-avatar { display:grid; place-items:center; width:34px; height:34px; flex-shrink:0; background:#eaf0df; border-radius:50%; }
.student-group b { font-size:22px; font-weight:400; }
.archive-back { background:none; border:0; color:#557c50; padding:0 0 15px; }
.archive-create { width:100%; border:1px solid #c6d9b5; border-radius:7px; padding:11px; background:#edf4e3; color:#365b38; }
details { margin-top:16px; } summary { cursor:pointer; }
:deep(.record-manager) { position:static; padding:0; border:0; }
button:disabled { opacity:.5; cursor:default; }
button:focus-visible { outline:2px solid #477c56; outline-offset:2px; }
@media(min-width:901px) { .student-archive { position:sticky; top:20px; } }
@media(max-width:900px) { .student-groups { max-height:240px; } }
</style>
