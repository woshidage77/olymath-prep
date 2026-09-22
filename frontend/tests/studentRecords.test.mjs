import test from 'node:test'
import assert from 'node:assert/strict'
import { groupStudentRecords } from '../src/studentRecords.ts'
const record=(id,name,date,extra={})=>({id,student_name:name,lesson_date:date,grade:5,topic:'观察',updated_at:date,...extra})
test('same trimmed name groups lessons while preserving individual record ids',()=>{
 const rows=[record('a',' 小林 ','2026-09-20'),record('b','小林','2026-09-22'),record('c','小周','2026-09-21')]
 const snapshot=JSON.stringify(rows)
 const groups=groupStudentRecords(rows)
 assert.equal(groups.length,2)
 assert.equal(groups[0].name,'小林')
 assert.deepEqual(groups[0].records.map(r=>r.id),['b','a'])
 assert.equal(JSON.stringify(rows),snapshot)
})
test('latest lesson supplies date and grade, not insertion order',()=>{
 const groups=groupStudentRecords([record('a','小林','2026-09-22',{grade:6}),record('b','小林','2025-01-01',{grade:5})])
 assert.equal(groups[0].grade,6)
 assert.equal(groups[0].latestDate,'2026-09-22')
})
test('distinct identity labels and internal spaces are not silently merged',()=>{
 assert.equal(groupStudentRecords([record('a','小林 A班','2026-09-20'),record('b','小林 B班','2026-09-20')]).length,2)
})
test('same-date lessons remain separate; deleting last lesson removes group',()=>{
 const rows=[record('a','小林','2026-09-20'),record('b','小林','2026-09-20')]
 assert.equal(groupStudentRecords(rows)[0].records.length,2)
 assert.equal(groupStudentRecords(rows.slice(1))[0].records.length,1)
 assert.deepEqual(groupStudentRecords([]),[])
})
