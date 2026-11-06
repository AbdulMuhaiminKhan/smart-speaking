import type { Category } from '../api/client'

export const CATEGORY_LABELS: Record<Category, string> = {
  voice: 'Voice',
  pacing: 'Pacing',
  language: 'Language',
  pronunciation: 'Pronunciation',
  eye_contact: 'Eye contact',
  posture: 'Posture',
  body_language: 'Body language',
}

export function scoreColor(score: number | null): string {
  if (score === null) return 'text-slate-400'
  if (score >= 80) return 'text-emerald-600 dark:text-emerald-400'
  if (score >= 60) return 'text-amber-600 dark:text-amber-400'
  return 'text-red-600 dark:text-red-400'
}

export const CATEGORY_ORDER: Category[] = [
  'voice',
  'pacing',
  'language',
  'pronunciation',
  'eye_contact',
  'posture',
  'body_language',
]
