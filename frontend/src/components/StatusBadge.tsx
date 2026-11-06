import type { SessionStatus } from '../api/client'

const styles: Record<SessionStatus, string> = {
  uploaded: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  queued: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
  processing: 'bg-brand-100 text-brand-700 dark:bg-brand-700/30 dark:text-brand-100',
  completed: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
  failed: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
}

const labels: Record<SessionStatus, string> = {
  uploaded: 'Uploaded',
  queued: 'Waiting',
  processing: 'Analyzing',
  completed: 'Done',
  failed: 'Failed',
}

export function StatusBadge({ status }: { status: SessionStatus }) {
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[status]}`}>
      {labels[status]}
    </span>
  )
}
