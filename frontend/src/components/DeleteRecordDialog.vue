<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
defineProps<{ title:string; kind:string; busy:boolean; error:string }>()
const emit=defineEmits<{ cancel:[]; confirm:[] }>()
const dialog=ref<HTMLDialogElement>()
const prior=document.activeElement as HTMLElement|null
onMounted(() => dialog.value?.showModal())
onBeforeUnmount(() => { dialog.value?.close(); if(prior?.isConnected) prior.focus() })
</script>
<template>
 <dialog ref="dialog" class="delete-record-dialog" aria-labelledby="delete-record-title" @cancel.prevent="!busy && emit('cancel')">
  <span>记录管理 / {{ kind }}</span>
  <h2 id="delete-record-title">确定删除这份记录？</h2>
  <strong class="delete-record-name">{{ title }}</strong>
  <p>删除后无法恢复。若这是正在编辑的记录，未保存内容也会一起关闭。</p>
  <p v-if="kind === '课后反馈'">这份反馈的 AI 润色记录也会删除，已上传的图片保留。</p>
  <p v-if="kind === '拍照记录'">被备课或反馈引用的图片不能直接删除，请先解除引用。</p>
  <p v-if="error" role="alert" class="error-message">{{ error }}</p>
  <footer><button autofocus :disabled="busy" @click="emit('cancel')">取消，保留记录</button><button class="confirm-delete" :disabled="busy" @click="emit('confirm')">{{ busy ? '正在删除…' : '确认删除' }}</button></footer>
 </dialog>
</template>
<style scoped>
.delete-record-dialog { width:min(470px,92vw); padding:28px; border:1px solid #dacfc3; border-radius:16px; color:#293e30; box-shadow:0 24px 80px #172f3940; }
.delete-record-dialog::backdrop { background:#19332a88; backdrop-filter:blur(4px); }
span { font-size:12px; color:#8c7967; } h2 { font-size:23px; margin:12px 0 20px; }
.delete-record-name { display:block; padding:15px; background:#f5f0e8; border-radius:8px; overflow-wrap:anywhere; }
p { font-size:14px; line-height:1.8; color:#66715f; }
footer { display:flex; justify-content:flex-end; gap:10px; margin-top:24px; flex-wrap:wrap; }
button { padding:11px 16px; border:1px solid #d4d9cf; border-radius:7px; background:#fff; color:#345139; }
.confirm-delete { background:#9e5144; border-color:#9e5144; color:white; }
button:disabled { opacity:.5; } button:focus-visible { outline:3px solid #92af81; outline-offset:2px; }
</style>
