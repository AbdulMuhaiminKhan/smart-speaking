import type { Issue } from '../api/client'

type Tk = (key: string, fallback: string, vars?: Record<string, string | number | null | undefined>) => string

/** Issue text in the app language, built from its kind and number; the server text is the fallback. */
export function issueMessage(issue: Issue, tk: Tk): string {
  const kind = issue.kind === 'mispronounced' && issue.value === 0 ? 'unclear' : issue.kind
  const msg = tk(`issue.${kind}`, issue.message, { text: issue.text ?? '', value: issue.value ?? '' })
  if (msg === issue.message) return msg
  const secs = issue.end - issue.start
  const timed = issue.category === 'eye_contact' || issue.category === 'posture' || issue.category === 'body_language'
  return timed && secs >= 2 ? tk('issue.with_secs', msg, { msg, secs: Math.round(secs) }) : msg
}
