<script setup lang="ts">
import { computed, ref } from 'vue'
const emit = defineEmits<{ enter: []; topic: [unitId: string]; destination: [mode: 'library' | 'drafts' | 'photo'] }>()
const selected = ref(0)
const examples = [
 { topic: '简易方程', title: '从年龄关系，讲清数量关系', question: '爸爸今年38岁，比小明年龄的3倍多2岁。小明今年多少岁？', tag: '年龄关系', formula: '3x + 2 = 38', concept: '先找到等量关系，再设未知数。', prompt: '“多2岁”对应的是谁的年龄？', answer: 'x = 12，小明今年12岁。', next: ['年龄和差', '年龄倍数'], unit: '第5单元' },
 { topic: '植树问题', title: '用一条线，看懂点与间隔', question: '一条240米的小路，每隔15米栽一棵树，两端都栽，一共栽多少棵？', tag: '两端都栽', formula: '240 ÷ 15 + 1', concept: '两端都栽时，棵数比间隔数多1。', prompt: '先画3个间隔，需要几个点？', answer: '16 + 1 = 17，一共栽17棵。', next: ['封闭路线', '楼梯计数'], unit: '第7单元' },
 { topic: '多边形面积', title: '从一块梯形，理解面积公式', question: '一个梯形上底6厘米、下底10厘米、高5厘米，面积是多少？', tag: '梯形面积', formula: '(6 + 10) × 5 ÷ 2', concept: '两个相同梯形可以拼成平行四边形。', prompt: '拼成的新图形，面积与原来是什么关系？', answer: '40平方厘米。', next: ['等积变形', '组合图形'], unit: '第6单元' },
]
const current = computed(() => examples[selected.value]!)
</script>

<template>
<div class="home-site">
  <section class="home-hero" aria-labelledby="home-title">
    <div class="home-shell hero-layout">
      <div class="hero-editorial">
        <p class="home-kicker"><span></span> 为每一堂有准备的课</p>
        <h1 id="home-title">好课，从一道<br><span>好问题</span>开始。</h1>
        <p class="home-lead">找到值得讲的题，串起值得想的问题。<br>把选题、讲解与练习，整理成你的教学思路。</p>
        <div class="home-actions">
          <button class="home-primary" @click="emit('enter')">开始我的备课 <span aria-hidden="true">↗</span></button>
          <a class="home-text-link" href="#lesson-preview">看看如何备一节课 <span aria-hidden="true">↓</span></a>
        </div>
        <div class="hero-footnote"><span class="tiny-book" aria-hidden="true">▤</span><span>从五年级数学起步</span><i></i><span>题目 · 概念 · 迁移</span></div>
      </div>
      <div id="lesson-preview" class="lesson-preview">
        <div class="preview-heading"><span><i></i> 一朵 · 备课手记</span><small>教学场景示例</small></div>
        <div class="preview-tabs" aria-label="切换备课示例">
          <button v-for="(example, index) in examples" :key="example.topic" :class="{ active: selected === index }" :aria-pressed="selected === index" @click="selected = index">{{ example.topic }}</button>
        </div>
        <div class="preview-body" aria-live="polite">
          <div class="preview-breadcrumb">五年级 · 上册 <span>/</span> {{ current.unit }}</div>
          <h2>{{ current.title }}</h2>
          <div class="sample-question"><span class="sample-label">起始题 · {{ current.tag }}</span><p>{{ current.question }}</p></div>
          <div class="lesson-thread">
            <div class="thread-node"><span>01</span><div><small>把问题说清楚</small><p>{{ current.prompt }}</p></div></div>
            <div class="thread-node"><span>02</span><div><small>让概念看得见</small><p>{{ current.concept }}</p><div class="sample-formula">{{ current.formula }}</div></div></div>
            <div class="thread-node"><span>03</span><div><small>回到原题，验证理解</small><p>{{ current.answer }}</p></div></div>
          </div>
          <div class="preview-next"><span>下一步可以讲</span><b v-for="title in current.next" :key="title">{{ title }}</b></div>
        </div>
        <div class="preview-bottom"><span>每一道题，都有教学的来处与去处。</span><span aria-hidden="true">✳</span></div>
      </div>
    </div>
    <div class="hero-bottom home-shell"><span>让备课有章法，让教学有自己的风格。</span><a href="#preparation">向下探索 <span aria-hidden="true">↓</span></a></div>
  </section>

  <section id="preparation" class="home-preparation home-shell">
    <div class="section-intro"><div><p class="home-kicker">从备课到课堂</p><h2>备课的每一步，<br>都围绕学生如何理解。</h2></div><p>题目不只是练习的终点。<br>它也可以是概念的起点、讨论的线索，<br>以及检查理解的方式。</p></div>
    <div class="preparation-grid">
      <button @click="emit('enter')"><span class="feature-index">01 / 选题</span><h3>先找到合适的起点 <span>↗</span></h3><p>按年级、专题与难度浏览。从基础例题出发，再安排巩固和挑战。</p><div class="mini-tags"><span>基础</span><span>进阶</span><span>挑战</span></div></button>
      <button @click="emit('destination', 'drafts')"><span class="feature-index">02 / 备课</span><h3>把题目串成教学思路 <span>↗</span></h3><p>组织题目顺序，补充课堂追问。保存自己的备课稿，下次继续完善。</p><div class="mini-sequence"><span>原题</span> → <span>概念</span> → <span>迁移</span></div></button>
      <button @click="emit('destination', 'photo')"><span class="feature-index">03 / 积累</span><h3>留住手边的好题 <span>↗</span></h3><p>上传单题照片，校对题干后检索相关题目，把零散材料带回备课流程。</p><div class="mini-tags"><span>照片录入</span><span>题干校对</span></div></button>
    </div>
  </section>

  <section id="subjects" class="home-subjects">
    <div class="home-shell subjects-layout"><div><p class="home-kicker">当前开放 · 五年级数学</p><h2>从一个专题，<br>延伸出一整节课。</h2><p>按人教版上下册单元组织，<br>覆盖计算、数量关系、图形与数学思维。</p><button class="home-text-link" @click="emit('enter')">浏览全部专题 <span>↗</span></button></div>
    <div class="subject-links">
      <button v-for="(name, index) in ['小数乘法', '简易方程', '观察物体（三）', '植树问题']" :key="name" @click="emit('topic', ['5a-1', '5a-5', '5b-1', '5a-7'][index]!)"><span>0{{ index + 1 }}</span><strong>{{ name }}</strong><small>{{ ['小数计算 · 估算 · 购物方案', '数量关系 · 年龄 · 盈亏', '三视图 · 遮挡 · 立体还原', '间隔数 · 封闭路线 · 锯木'][index] }}</small><b aria-hidden="true">↗</b></button>
    </div></div>
  </section>

  <section id="questions" class="home-faq home-shell">
    <div><p class="home-kicker">开始之前</p><h2>你可能想了解</h2></div>
    <div class="faq-items">
      <details><summary>现在适合哪些老师使用？</summary><p>当前从五年级数学与小学培优备课开始，按照人教版单元组织内容。其他年级仍在建设中。</p></details>
      <details><summary>备课资料可以修改和导出吗？</summary><p>可以保存为草稿、调整题组顺序、编辑课堂追问与讲解。审核后可以导出教师版或学生版资料。</p></details>
      <details><summary>题目和建议可以直接用于课堂吗？</summary><p>请先复核题干、答案、难度与教学顺序。开放题保留来源信息，建议由老师结合学生情况决定是否采用。</p></details>
    </div>
  </section>
  <footer class="home-footer"><div class="home-shell"><div><strong>一朵教学<span> YIDUO</span></strong><p>让每一道题，成为理解的开始。</p></div><button @click="emit('enter')">进入备课工作台 ↗</button><small>面向教师的备课平台 · MIT 开源</small></div></footer>
</div>
</template>

<style scoped>
.home-site{--ink:#183e33;--muted:#63746a;--paper:#f8f9f4;color:var(--ink);background:var(--paper);font-family:"Microsoft YaHei",sans-serif}
.home-shell{width:min(1400px,90%);margin-inline:auto}
.home-hero{background:radial-gradient(ellipse at 80% 30%,#dcebdc88,transparent 52%),#f4f6ed;border-bottom:1px solid #d9e0d4}
.hero-layout{display:grid;grid-template-columns:1fr 1fr;gap:clamp(40px,7vw,110px);align-items:center;min-height:calc(100svh - 138px);padding-block:65px}
.home-kicker{display:flex;align-items:center;gap:10px;font-size:12px;letter-spacing:.14em;font-weight:600;color:#647c5b;margin:0 0 27px}
.home-kicker>span{width:7px;height:7px;background:#6f8c53;border-radius:50%}
.hero-editorial h1{font-size:clamp(42px,4.6vw,76px);line-height:1.28;letter-spacing:-.055em;font-weight:650;margin:0;white-space:nowrap}
.hero-editorial h1>span{color:#738649;position:relative}
.hero-editorial h1>span:after{content:"";position:absolute;bottom:-5px;left:0;right:0;height:5px;border-bottom:2px solid #a1ac78;border-radius:50%;transform:rotate(-3deg)}
.home-lead{color:var(--muted);line-height:2;font-size:16px;margin:28px 0 33px}
.home-actions{display:flex;gap:24px;align-items:center;flex-wrap:wrap}
.home-primary{background:#224c3c;color:white;border:1px solid #224c3c;padding:16px 23px;border-radius:6px;font-weight:600;font-size:15px;display:flex;gap:30px;align-items:center;transition:background .2s,transform .2s}
.home-primary:hover{background:#35664b;transform:translateY(-2px)}
.home-text-link{font-size:13px;color:var(--ink);text-decoration:none;border:0;background:none;padding:10px 0;display:inline-flex;gap:16px;align-items:center}
.home-text-link:hover{text-decoration:underline;text-underline-offset:5px}
.hero-footnote{display:flex;align-items:center;gap:12px;color:#7b8677;font-size:11px;margin-top:40px}
.hero-footnote i{width:3px;height:3px;background:#899680;border-radius:50%}
.tiny-book{font-size:18px}
.lesson-preview{background:#fff;border:1px solid #dce3d8;border-radius:10px;box-shadow:0 30px 65px -35px #3a55394d,0 3px 12px #384e3510;overflow:hidden;scroll-margin-top:100px;transform:rotate(1deg)}
.preview-heading{padding:17px 23px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #edf0e9;font-size:13px;font-weight:600}
.preview-heading>span{display:flex;align-items:center;gap:8px}
.preview-heading i{display:inline-block;width:8px;height:8px;background:#98ad75;border-radius:50%}
.preview-heading small{font-size:10px;color:#8a9286;font-weight:400}
.preview-tabs{display:flex;gap:4px;background:#f6f8f3;padding:10px 20px;border-bottom:1px solid #e8ede2}
.preview-tabs button{flex:1;background:none;border:0;border-radius:4px;padding:9px 4px;color:#74816d;font-size:12px}
.preview-tabs button.active{background:#fff;color:#28513b;box-shadow:0 1px 4px #19342014;font-weight:700}
.preview-body{padding:24px 27px}
.preview-breadcrumb{font-size:10px;color:#8c9685;display:flex;gap:10px}
.preview-body h2{font-size:18px;margin:13px 0 18px;line-height:1.5}
.sample-question{padding:15px 17px;background:#f4f6ed;border-left:3px solid #93a36d}
.sample-label{font-size:10px;color:#6b7d4e}
.sample-question p{font-size:12px;line-height:1.9;margin:7px 0 0;color:#4e5e47}
.lesson-thread{margin:23px 0 12px}
.thread-node{display:flex;gap:15px;position:relative;padding-bottom:17px}
.thread-node:not(:last-child):before{content:"";position:absolute;left:12px;top:25px;bottom:0;border-left:1px solid #dde4d6}
.thread-node>span{width:25px;height:25px;background:#eef2e7;border-radius:50%;flex-shrink:0;display:grid;place-items:center;font-size:9px;color:#6c7f56}
.thread-node small{font-size:11px;font-weight:600}
.thread-node p{font-size:11px;line-height:1.8;color:#7b8473;margin:5px 0}
.sample-formula{font:500 22px/1.5 Georgia,serif;color:#476542;margin-top:8px;letter-spacing:1px}
.preview-next{display:flex;gap:8px;align-items:center;padding-top:14px;border-top:1px dashed #dce3d6;flex-wrap:wrap}
.preview-next>span{font-size:10px;color:#8b9281;margin-right:auto}
.preview-next b{font-size:10px;font-weight:500;color:#698053;background:#f0f4e9;padding:5px 9px;border-radius:3px}
.preview-bottom{padding:12px 23px;border-top:1px solid #edf0e9;display:flex;justify-content:space-between;align-items:center;color:#86927c;font-size:10px}
.preview-bottom>span:last-child{font-size:20px;color:#7c9463}
.hero-bottom{display:flex;justify-content:space-between;align-items:center;padding-block:21px;border-top:1px solid #dce3d3;font-size:11px;color:#819074}
.hero-bottom a{color:inherit;text-decoration:none;display:flex;gap:18px}
.home-preparation{padding-block:100px}
.section-intro{display:flex;justify-content:space-between;align-items:flex-end;gap:30px;margin-bottom:45px}
.home-site h2{letter-spacing:-.03em}
.section-intro h2,.subjects-layout h2{font-size:32px;line-height:1.5;margin:0}
.section-intro>p,.subjects-layout>div>p:not(.home-kicker){color:var(--muted);font-size:14px;line-height:1.9}
.preparation-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:0;border-block:1px solid #dfe4d9}
.preparation-grid>button{text-align:left;border:0;background:transparent;padding:35px 32px;transition:background .2s;color:inherit}
.preparation-grid>button:first-child{padding-left:0}
.preparation-grid>button+button{border-left:1px solid #dfe4d9}
.preparation-grid>button:hover{background:#eef2e7}
.feature-index{font-size:11px;color:#7c8a6a;letter-spacing:.08em}
.preparation-grid h3{font-size:18px;margin:25px 0 12px;display:flex;justify-content:space-between;gap:12px}
.preparation-grid h3 span{font-weight:400;color:#819667}
.preparation-grid p{font-size:13px;line-height:1.9;color:var(--muted)}
.mini-tags,.mini-sequence{display:flex;gap:9px;margin-top:27px;color:#72825e;font-size:11px}
.mini-tags span{padding:6px 10px;border:1px solid #dce3d3;border-radius:3px}
.home-subjects{background:#e9eee2;padding-block:75px}
.subjects-layout{display:grid;grid-template-columns:1fr 1.3fr;gap:80px;align-items:center}
.subject-links>button{display:flex;align-items:center;width:100%;gap:25px;text-align:left;padding:25px 8px;background:transparent;border:0;border-bottom:1px solid #cfd9c6;color:inherit}
.subject-links>button:hover{background:#e0e8d7}
.subject-links>button>span{font:italic 16px Georgia;color:#8a9b78}
.subject-links strong{font-size:17px;font-weight:500}
.subject-links small{font-size:11px;color:#7c8a70}
.subject-links b{margin-left:auto;font-weight:400}
.home-faq{display:grid;grid-template-columns:1fr 1.3fr;gap:80px;padding-block:90px}
.home-faq h2{font-size:29px;margin:0}
.faq-items details{border-bottom:1px solid #dfe4d9;padding:20px 0}
.faq-items summary{cursor:pointer;font-size:14px;line-height:1.7}
.faq-items p{font-size:13px;line-height:1.9;color:var(--muted)}
.home-footer{background:#183e33;color:#e1e9db;padding-block:40px}
.home-footer>.home-shell{display:flex;align-items:center;justify-content:space-between;gap:24px;flex-wrap:wrap}
.home-footer strong{font-size:20px}
.home-footer strong span{font-size:10px;letter-spacing:.15em;font-weight:400;margin-left:15px;color:#a7b99b}
.home-footer p{font-size:11px;color:#a7b99b}
.home-footer button{background:transparent;border:1px solid #54715b;color:#e1e9db;border-radius:4px;padding:12px 18px;font-size:12px}
.home-footer small{font-size:10px;color:#a7b99b}
.home-site :is(button,a,summary):focus-visible{outline:3px solid #b88c39;outline-offset:5px}
@media(min-width:1800px){.hero-layout{min-height:800px}}
@media(max-width:1000px){.hero-layout{gap:35px}.hero-editorial h1{font-size:46px}.home-actions{gap:12px}.preview-body{padding:20px}.subjects-layout,.home-faq{gap:40px}.subject-links>button{gap:13px}.subject-links small{display:none}.preparation-grid>button{padding:25px 20px}.preparation-grid h3{font-size:16px}}
@media(max-width:720px){.home-shell{width:88%}.hero-layout{grid-template-columns:1fr;padding-block:48px;gap:42px;min-height:auto}.hero-editorial h1{font-size:clamp(38px,8.5vw,56px);line-height:1.3}.home-kicker{margin-bottom:20px;font-size:10px}.home-lead{font-size:14px;margin:23px 0}.hero-footnote{margin-top:25px}.lesson-preview{transform:none}.hero-bottom>span{max-width:65%;line-height:1.7}.home-preparation{padding-block:58px}.section-intro{display:block;margin-bottom:25px}.section-intro h2,.subjects-layout h2{font-size:26px}.section-intro>p{margin-top:20px;font-size:13px}.preparation-grid{grid-template-columns:1fr}.preparation-grid>button,.preparation-grid>button:first-child{padding:25px 0}.preparation-grid>button+button{border-left:0;border-top:1px solid #dfe4d9}.preparation-grid h3{margin-top:16px;font-size:18px}.mini-tags,.mini-sequence{margin-top:16px}.subjects-layout,.home-faq{grid-template-columns:1fr;gap:24px}.home-subjects,.home-faq{padding-block:52px}.subject-links small{display:block;font-size:9px}.subject-links strong{font-size:14px}.subject-links>button{gap:10px}.home-footer small{width:100%}}
@media(prefers-reduced-motion:reduce){.home-site *{transition:none!important;scroll-behavior:auto!important}}
</style>
