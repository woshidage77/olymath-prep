<script setup lang="ts">
import type { TeachingStep } from '../types'
defineProps<{ steps: TeachingStep[] }>()
</script>

<template>
  <div class="lesson-reading">
    <div class="reading-caption"><span>课堂讲解手记</span><span>{{ steps.length }} 个教学动作 · 按顺序展开</span></div>
    <ol class="teaching-step-cards">
      <li v-for="(step, index) in steps" :key="index">
        <div class="step-rail"><span>{{ String(index + 1).padStart(2, '0') }}</span></div>
        <div class="step-content">
          <span class="question-eyebrow">这样问学生</span>
          <blockquote>{{ step.teacher_question }}</blockquote>
          <div class="step-support">
            <div class="student-action"><span class="support-label">学生动手 / 表达</span><p>{{ step.student_action }}</p></div>
            <div class="understanding-check"><span class="support-label">观察是否理解</span><p>{{ step.checkpoint }}</p></div>
          </div>
        </div>
      </li>
    </ol>
  </div>
</template>
