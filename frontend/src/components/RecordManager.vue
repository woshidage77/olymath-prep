<script setup lang="ts">
import { computed, ref } from 'vue'
const props = defineProps<{ title:string; items:{id:string; title:string; detail:string}[]; activeId?:string; busy:boolean }>()
const emit = defineEmits<{ select:[id:string]; remove:[id:string,title:string] }>()
const query = ref('')
const filtered = computed(() => props.items.filter(item => (item.title + item.detail).toLocaleLowerCase().includes(query.value.trim().toLocaleLowerCase())))
</script>
<template>
 <aside class="record-manager" :aria-label="title">
  <header><h2>{{ title }}</h2><span>{{ items.length }} 份</span></header>
  <input v-model="query" type="search" :aria-label="'搜索' + title" placeholder="搜索名称、日期…" />
  <p class="manager-hint">点击名称查看，右侧可直接删除。</p>
  <div class="manager-records">
   <div v-for="item in filtered" :key="item.id" class="manager-row" :class="{ selected:activeId === item.id }">
    <button class="record-open" :disabled="busy" :aria-current="activeId === item.id ? 'true' : undefined" @click="emit('select',item.id)"><strong>{{ item.title }}</strong><small>{{ item.detail }}</small></button>
    <button class="record-delete" :disabled="busy" :aria-label="'删除：' + item.title" @click="emit('remove',item.id,item.title)">删除</button>
   </div>
   <p v-if="!filtered.length">{{ busy ? '正在读取…' : items.length ? '没有匹配的记录。' : '还没有记录，先新建并保存一份。' }}</p>
  </div>
 </aside>
</template>
<style scoped>
.record-manager { min-width:0; align-self:start; border:1px solid #dae2d7; background:#f7f9f3; border-radius:12px; padding:16px; }
header { display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:14px; }
h2 { font-size:16px; margin:0; } header span,.manager-hint { font-size:12px; color:#6b7b6c; }
input { width:100%; min-width:0; border:1px solid #d3ddce; border-radius:7px; padding:10px; background:white; font:inherit; }
.manager-hint { line-height:1.6; }
.manager-records { display:grid; gap:9px; max-height:65vh; overflow:auto; }
.manager-row { display:flex; border:1px solid #dce4d7; border-radius:8px; background:white; }
.manager-row.selected { border-color:#51836a; background:#edf4e9; box-shadow:inset 3px 0 #51836a; }
button { background:transparent; border:0; }
.record-open { flex:1; min-width:0; text-align:left; padding:14px 10px; display:grid; gap:7px; color:#254b37; }
.record-open strong { overflow-wrap:anywhere; font-size:14px; }
.record-open small { font-size:11px; color:#73816f; line-height:1.6; }
.record-delete { flex-shrink:0; align-self:center; color:#a05243; padding:12px 8px; font-size:12px; }
button:focus-visible { outline:2px solid #42735b; outline-offset:-2px; } button:disabled { opacity:.45; cursor:default; }
@media(min-width:901px) { .record-manager { position:sticky; top:20px; } }
@media(max-width:900px) { .manager-records { max-height:230px; } }
</style>
