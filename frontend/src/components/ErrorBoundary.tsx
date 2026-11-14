import { Component, type ErrorInfo, type ReactNode } from 'react'
import { initialLang, translate } from '../i18n/core'

interface State {
  error: Error | null
}

export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('SmartSpeaking crashed', error, info.componentStack)
  }

  render() {
    if (!this.state.error) return this.props.children
    const lang = initialLang()
    return (
      <div className="mx-auto mt-20 max-w-md text-center">
        <p className="text-lg font-semibold">{translate(lang, 'crash.title')}</p>
        <p className="mt-2 text-sm text-slate-500">{this.state.error.message}</p>
        <button type="button" onClick={() => location.reload()} className="mt-4 btn-primary">
          {translate(lang, 'crash.reload')}
        </button>
      </div>
    )
  }
}
