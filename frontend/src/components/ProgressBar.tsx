interface Props {
  value: number // 0..1
  label?: string
  indeterminate?: boolean
}

export function ProgressBar({ value, label, indeterminate }: Props) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100)
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span className="text-slate-600 dark:text-slate-300">{label}</span>
        {!indeterminate && <span className="tabular-nums text-slate-500">{pct}%</span>}
      </div>
      <div
        className="h-2.5 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800"
        role="progressbar"
        aria-valuenow={indeterminate ? undefined : pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label}
      >
        <div
          className={`h-full rounded-full bg-brand-600 transition-[width] duration-500 ${
            indeterminate ? 'w-1/3 animate-pulse' : ''
          }`}
          style={indeterminate ? undefined : { width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
