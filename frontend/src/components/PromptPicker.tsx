import type { Lang } from '../api/client'
import { useI18n } from '../i18n'
import { randomPrompt, type PromptMode } from '../lib/prompts'

interface Props {
  mode: PromptMode
  lang: Lang
  value: string
  onChange: (v: string) => void
  className?: string
}

/** The topic or question for a practice mode: a random pick you can reshuffle or rewrite. */
export function PromptPicker({ mode, lang, value, onChange, className = '' }: Props) {
  const { t } = useI18n()
  return (
    <div className={className}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium">{t(mode === 'interview' ? 'modes.question' : 'modes.topic')}</span>
        <button
          type="button"
          onClick={() => onChange(randomPrompt(mode, lang, value))}
          className="rounded-md px-2 py-1 text-sm text-brand-600 hover:bg-brand-50 dark:hover:bg-slate-800"
        >
          ↻ {t('modes.shuffle')}
        </button>
      </div>
      <textarea
        dir="auto"
        lang={lang}
        rows={2}
        value={value}
        maxLength={1000}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-md border border-slate-300 bg-transparent px-3 py-2 text-base dark:border-slate-700"
      />
    </div>
  )
}
