import type { FeedbackSummary } from './types'

export interface StudentGroup {
  name: string
  latestDate: string
  grade: number
  records: FeedbackSummary[]
}
export function groupStudentRecords(records: FeedbackSummary[]): StudentGroup[] {
  const grouped = new Map<string, FeedbackSummary[]>()
  for (const record of records) {
    const name = record.student_name.trim()
    const entries = grouped.get(name) ?? []
    entries.push(record)
    grouped.set(name, entries)
  }
  return [...grouped.entries()].map(([name, entries]) => {
    const ordered = [...entries].sort((a, b) =>
      b.lesson_date.localeCompare(a.lesson_date) || b.updated_at.localeCompare(a.updated_at) || a.id.localeCompare(b.id))
    return { name, latestDate: ordered[0]!.lesson_date, grade: ordered[0]!.grade, records: ordered }
  }).sort((a, b) => b.latestDate.localeCompare(a.latestDate) || a.name.localeCompare(b.name, 'zh-CN'))
}
