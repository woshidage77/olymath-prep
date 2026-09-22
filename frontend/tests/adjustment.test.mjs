import test from 'node:test'
import assert from 'node:assert/strict'
import { stageWithProposal, replaceStage } from '../src/adjustment.ts'

const before = { id: 'understand-method', problem_id: 'p1', purpose: 'original', teacher_prompt: 'question', teaching_note: 'note', teaching_steps: [], geometry: { cubes: [1] } }
const other = { id: 'return-to-problem', problem_id: 'p1' }
const plan = { selected_problem: { id: 'p1' }, stages: [before, other] }
const proposal = { objective: 'new objective', steps: [{ teacher_question: 'ask', student_action: 'draw', checkpoint: 'check' }], teacher_check: 'review' }

test('adopt changes only the selected stage without mutating the original', () => {
  const after = stageWithProposal(before, proposal)
  const result = replaceStage(plan, before, after)
  assert.equal(result.stages[1], other)
  assert.equal(plan.stages[0].purpose, 'original')
  assert.equal(after.geometry, before.geometry)
  assert.notEqual(after.teaching_steps[0], proposal.steps[0])
  assert.match(after.teaching_note, /draw/)
  assert.match(after.teacher_prompt, /ask/)
})
test('undo restores the exact previous stage', () => {
  const after = stageWithProposal(before, proposal)
  const adopted = replaceStage(plan, before, after)
  assert.deepEqual(replaceStage(adopted, after, before), plan)
})
test('stale stage and cross-question updates are rejected', () => {
  const after = stageWithProposal(before, proposal)
  assert.equal(replaceStage({ ...plan, stages: [{ ...before, teaching_note: 'new edit' }, other] }, before, after), null)
  assert.equal(replaceStage({ ...plan, selected_problem: { id: 'p2' } }, before, after), null)
  assert.equal(replaceStage(plan, before, { ...after, id: 'other' }), null)
})
test('undo cannot overwrite a subsequent manual change', () => {
  const after = stageWithProposal(before, proposal)
  assert.equal(replaceStage({ ...plan, stages: [{ ...after, purpose: 'later edit' }, other] }, after, before), null)
})
