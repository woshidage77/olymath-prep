# 一朵教学

帮助教师围绕题目组织教学逻辑的备课平台，从小学奥数起步，长期面向小学、初中、高中及更广泛的题目与备课场景。核心流程是“题目引入 → 理解概念与方法 → 回到原题 → 关联与迁移题”。

当前原型按人教版五年级上下册的 15 个单元组织专题目录，共提供 136 道题：36 道原创教学题和 100 道 CC BY 4.0 的 CMATH 五年级开放数据题。教师先选择年级和课题，再从题目进入“先做原题 → 理解概念与方法 → 回到原题 → 关联题”的备课链。观察物体题保留小正方体模型与三视图，其他专题使用文本、关系图或表格建议。

当前 A5 展示版在 A4 本地单用户闭环上继续完善题目排序、难度筛选、四字题名、关联题匹配和正式入口页；原有闭环已支持备课草稿持久化、题组编辑与审核、教师版/学生版导出、单题照片安全上传与人工校对。可选的模型入口能读取题目信息、识别知识点，并由 LangGraph 整理成结构化备课资料和题目问答。尚未完成 OCR、登录与多人权限、PostgreSQL、语义 embedding 或模型质量评测；CMATH 的单元归类和原创题教学质量仍需教师逐题复核。

## 产品方向与下一步

- [产品反馈、功能范围与验收](docs/PRODUCT_ROADMAP.md)
- [AI 应用开发排期：Quickstart → LangGraph → RAG → 功能补齐 → 前端 → 模型评测](docs/APP_DEVELOPMENT_PLAN.md)
- [题库来源核查与内容引入规则](docs/QUESTION_SOURCES.md)

产品名称为“一朵教学”；现有目录和包标识保留，避免影响本地运行。

## 当前能做什么

- 选择年级，再按人教版五年级上下册单元进入题目文件夹。
- 在 15 个单元、136 道题中浏览或按题型、概念和方法搜索。
- 围绕同一道题依次完成先做、理解概念和回题，并进入下一道对比或迁移题。
- 查看题目来源与审核状态；开放数据和原创内容分别标记。
- 对空间题旋转小正方体并查看三视图；其他题显示板书与变式建议。
- 保存、重排、增删和编辑备课草稿，确认后导出教师版或无答案学生版 Markdown。
- 上传单题照片到本地私有目录，人工校对题目文字，再检索题库中的相近题。
- 配置模型后，由结构化输出识别知识点、难点、易错点和变式，再通过 Graph 生成三阶段备课内容；可继续围绕当前题实时问答。

当前不抓取教学网站，不生成视频，照片识别也没有伪装成已经完成的 OCR。代码使用 MIT；CMATH 数据继续遵守 CC BY 4.0，详情见[题库来源说明](docs/QUESTION_SOURCES.md)。第三方教材、竞赛试卷及用户资料不因进入系统而自动获得公开再分发许可。

备课草稿由 LangGraph 编排：校验需求、取得题目、检索上下文、可选模型分析、编排关联题、整理讲解、检查引用，最后停在等待教师确认。业务草稿由 SQLite 持久化，详见 [A2 LangGraph 实现说明](docs/A2_LANGGRAPH_NOTES.md)、[A3 RAG 实现说明](docs/A3_RAG_NOTES.md)和 [A4 基本功能说明](docs/A4_BASIC_FEATURES.md)。

## 本地运行

需要 Python 3.12+ 和 Node.js 20+。

后端：

~~~bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m uvicorn app.main:app --reload --env-file ../.env
~~~

前端另开终端：

~~~bash
cd frontend
npm install
npm run dev
~~~

访问 http://localhost:5173。API 文档位于 http://localhost:8000/docs。

模型是可选能力。把仓库根目录的 `.env.example` 复制为本地 `.env`，填写 `OPENAI_API_KEY`，并按需调整 `YIDUO_OPENAI_MODEL`；上面的启动命令会显式加载这个文件。也可以直接使用操作系统环境变量。密钥只由后端读取；仓库、前端和草稿数据库都不保存密钥。模型调用使用 Responses API 的结构化输出，并设置 `store=false`；实现依据见[官方 Responses API](https://developers.openai.com/api/reference/cli/resources/responses/methods/create)。没有密钥时，题库、基础备课、草稿和导出仍可使用。

## 验证

~~~bash
cd backend
.venv/Scripts/python -m compileall app tests
.venv/Scripts/python -m pytest

cd ../frontend
npm run build
~~~

最近一次实际验证结果见 [Demo Verification Evidence](docs/DEMO_EVIDENCE.md)。

## 为什么先做互动模型

对组合体观察题，几何关系必须稳定。可旋转模型可以暂停、换视角并让教师现场提问；由坐标计算投影也容易回归测试。后续可以把教师操作录制为确定性的镜头路径并导出讲解视频。生成式视频只适合补充情境，不作为几何事实来源。

## 开源与数据

代码采用 [MIT License](LICENSE)。CMATH 数据的 CC BY 4.0 署名与变更记录见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。私有题库、教材图片、学生资料、模型密钥和运行产物不得提交到仓库。经来源与数学审核的原创或明确允许分发的种子题可以单独纳入公开样例，并保留各自许可。安全问题请按 [SECURITY.md](SECURITY.md) 的方式私下报告。
