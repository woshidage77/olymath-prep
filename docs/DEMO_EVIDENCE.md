# Demo Verification Evidence
Verified on 2026-09-15. This record covers the deterministic local demo only; it is not a public-deployment security review or a teaching-effect evaluation.

## Automated checks

- Python compile: app and tests compiled successfully.
- Backend tests: 4 passed. One upstream Starlette/AnyIO deprecation warning remains.
- API smoke test: GET /api/health returned status ok and mode demo.
- Frontend type check and production build: passed.
- npm production dependency audit against the official npm registry: 0 vulnerabilities reported.
- Whitespace and sensitive-pattern checks across files intended for the repository: passed.

The production JavaScript bundle is about 570 KB before gzip and triggers Vite's 500 KB advisory. Three.js is the main reason; code splitting is deferred until the product flow is validated.

## Browser checks

- The page loaded from the Vite development server and received the lesson plan from FastAPI.
- The content limit and excluded page appeared correctly.
- All three teaching stages changed the teaching text and cube structure.
- Front, left, top and free camera controls responded.
- Dragging rotated the 3D model.
- The cube model, reference grid and computed 2D projections rendered visibly.

## Data boundary

No supplied textbook photo, QR code, student data, external video or model credential was copied into the repository. Demo cube coordinates and teaching copy are original fixtures.

## Quickstart update — 2026-09-16

Scope: AI implemented and locally verified the deterministic question-driven path. This does not prove developer mastery or teacher acceptance.

- Added a three-question original fixture catalog with stable problem/revision IDs, full statements, answers, source status and explicit teaching relations.
- Selecting a problem now controls the returned problem, geometry, three teaching phases and next related problem. All phases reference the same problem ID.
- Added `GET /api/demo/problems`; unknown problem IDs return a distinct HTTP 404 contract instead of an empty plan.
- Added a regression invariant for the contrast pair: the two arrangements have the same front silhouette and different top projections. Their hidden overlap counts are deliberately different.
- Python compile passed; backend test suite: 9 passed with one upstream Starlette/AnyIO deprecation warning.
- Frontend TypeScript check and Vite production build passed. The existing bundle-size advisory remains (about 573 KB before gzip).
- Live API smoke checks returned the three-problem catalog and a valid plan for `cube-view-002`.

Not yet verified at the Quickstart checkpoint: independent startup and explanation by the developer, fresh browser interaction after this update, teacher review of the question wording and teaching chain, searchable question bank, persistence, RAG, OCR or model quality.

## LangGraph update — 2026-09-16

Scope: AI implemented and locally verified deterministic orchestration. It is not evidence of an LLM agent, durable execution, developer mastery or teacher approval.

- Locked and installed `langgraph==1.2.11`; `pip check` reported no broken requirements.
- Added a compiled six-node `StateGraph`: validate brief → retrieve candidate → propose sequence → draft teaching notes → validate output → await teacher review.
- Added conditional exits for invalid input, missing candidate and invalid output. A successful run ends in `waiting_teacher_review`; no code path marks a lesson approved.
- Graph state is JSON-serializable and exposes an ordered trace in the API and UI.
- Python compile passed; backend test suite: 13 passed with one upstream Starlette/AnyIO deprecation warning.
- Frontend TypeScript check and Vite production build passed. The existing bundle-size advisory remains (about 573 KB before gzip).
- Live API smoke test returned `engine=langgraph`, `review_required=true` and all six trace entries.

Not implemented: model calls, RAG, checkpointer/thread persistence, interrupt/resume, approval endpoint, database or teacher evaluation.

The sentence above records the A2 checkpoint. A3 subsequently added the retrieval baseline described below; model calls and semantic embeddings remain unimplemented.

## RAG retrieval baseline — 2026-09-16

Scope: AI implemented and locally verified the knowledge-base, retrieval and context-building path. It is not evidence of semantic retrieval, generated-answer quality, developer mastery or teacher acceptance.

- Expanded the original seed catalog from 3 to 8 question revisions, each with grade/topic/concept/method/tag metadata and deterministic cube coordinates.
- Added LangChain `Document` conversion and an in-memory keyword/tag retriever with field weights, metadata filtering, explainable integer scores and stable tie-breaking.
- Added `POST /api/demo/problems/search`; no results return `[]`, while blank input returns 422.
- Added a LangGraph `retrieve_context` node. The API returns the query, ranked candidates and context items carrying problem ID, revision ID and source.
- The explicit teaching relation remains first; retrieval candidates are marked separately and require teacher judgment.
- Python compile passed; backend test suite: 19 passed with one upstream Starlette/AnyIO deprecation warning.
- Frontend TypeScript check and Vite production build passed. The existing bundle-size advisory remains (about 576 KB before gzip).
- Live smoke test for “上视图 高度” returned `cube-view-006` first with matched fields and score; the catalog returned all 8 IDs.

Not implemented: embedding model, vector store, semantic/hybrid evaluation, persistent index, external corpus ingestion, generated answer or teacher retrieval evaluation.

## Curriculum and teacher-interface revision — 2026-09-16

Scope: AI implemented and locally verified the three product corrections raised after viewing A3. This is not evidence that all题目分类正确或教师已经认可界面。

- Added a 15-unit grade-five curriculum catalog following the People’s Education Press upper/lower-book structure. Every unit opens as a question folder and contains at least two questions.
- Expanded the catalog to 136 questions: 36 original teaching fixtures and 100 grade-five CMATH records distributed under CC BY 4.0. Attribution, extraction and modification notes are stored with the data.
- Added curriculum and folder-filtered question APIs. Grades other than five return an explicit unavailable catalog instead of pretending to have content.
- Removed lesson duration, content cutoff and excluded-page fields from the request and teacher UI.
- Replaced the previous sidebar/dashboard with the sequence “choose grade → open unit folder → browse/search questions → prepare selected question”.
- Removed RAG, LangGraph trace, internal strategy, matched fields and scores from the teacher-facing page. The backend retains them for engineering tests and later evaluation.
- Non-spatial questions no longer render an empty cube tool; they receive text-oriented board-plan and variation suggestions. Spatial questions retain the interactive cube model.
- Python compile passed; backend test suite: 23 passed with one upstream Starlette/AnyIO deprecation warning.
- Frontend TypeScript check and Vite production build passed. The initial application chunk is 79.21 KB before gzip; the cube workbench is loaded on demand as a separate 499.88 KB chunk, removing the previous Vite size warning.
- Live API smoke check returned 15 units and a total of 136 questions; the “可能性” folder returned its two expected questions.
- Desktop (1440×1200) and mobile (390×844) headless-browser captures confirmed that the landing page renders the grade selector, upper/lower-book filters and unit folders without overlap. The temporary captures were deleted after inspection.

Still pending: teacher-by-teacher interaction testing, manual review of all 100 CMATH unit assignments, authored step-by-step solutions for imported records, persistence/editing, photo recognition and model evaluation.

## A4 local workspace and optional model path — 2026-09-16

Scope: AI implemented and locally verified a single-user working loop. This is not evidence of OCR, production authorization, a successful external model call, model quality, developer mastery or teacher acceptance.

- Added SQLite migrations for durable lesson drafts, ordered draft items and private photo records. Draft updates use optimistic versions; editing resets approval to pending review.
- Added same-topic question insertion, removal, reordering, teaching-copy editing, approval, deletion and distinct teacher/student Markdown exports.
- Added private single-photo upload with an 8 MB limit, 20 million pixel limit, actual image decode, EXIF orientation handling, PNG re-encoding, server-generated filenames, path-boundary checks and file deletion. There is no public image route.
- Photo text is explicitly manual in this checkpoint. Saving the verified text can search the existing question bank; this is not called OCR.
- Added an optional OpenAI Responses adapter. Structured problem analysis is Pydantic-validated and runs as an optional LangGraph node before sequence/draft generation. Teacher Q&A is limited to the selected problem and at most 12 prior messages; calls set `store=false`.
- Without `OPENAI_API_KEY`, model status reports unavailable, ordinary lesson generation remains usable, and AI plan requests return a distinct HTTP 503 response.
- Python compile passed; backend suite: 31 passed. `pip check` reported no broken requirements after pinning the OpenAI SDK to the version compatible with the existing LangChain packages.
- Frontend TypeScript check and Vite production build passed. The initial application chunk is 95.12 KB before gzip; the cube workbench remains a lazy 499.88 KB chunk.
- Browser interaction verified “open unit → choose problem → generate three-stage plan → save draft → open editable draft” and the photo-entry screen. No browser console errors were reported; the temporary browser-test draft was deleted afterward.

Still pending: live external model call, fixed-set model evaluation, OCR, PostgreSQL migration, login and per-user/per-organization access control, teacher usability test and deployment review.

## A5 formal teacher interface and question ordering — 2026-09-17

Scope: AI implemented and locally verified the frontend changes requested after reviewing the A4 demo. This is engineering evidence, not teacher adoption or portfolio review evidence.

- Added a restrained “一朵教学” entry page before the workspace, with a direct path into lesson preparation.
- Replaced folder illustrations with numbered curriculum cards and kept grade, semester and unit selection as the primary navigation.
- Marked one reviewed original problem in every unit as the featured basic starting point; remaining questions sort by 基础、进阶、挑战 and can be filtered within the unit.
- Replaced numbered imported titles with four-character content names. Added topic-scoped naming rules and corrected representative misclassifications involving interval problems, equations, factors/multiples, volume and division.
- Changed default related-question retrieval to use the selected question’s title and statement. Browser verification for an age problem returned 年龄关系 and 年龄倍数 before broader same-unit candidates.
- Kept implementation terms out of the teacher UI and retained the existing draft, photo and optional-model functions behind the main navigation.
- Python compile passed; backend suite: 35 passed. Frontend TypeScript check and Vite production build passed; the initial application chunk is 97.77 KB and the cube workbench remains a lazy 499.88 KB chunk.
- Browser interaction verified the entry page, 15 numbered units, featured-first sorting, a one-result difficulty filter and distinct related-question titles.

Still pending: teacher task observation, manual review of all imported classifications and solutions, mobile and keyboard accessibility audit, real model evaluation, OCR, multi-user authorization and deployment review.
