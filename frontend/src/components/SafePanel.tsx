import { Component, type ReactNode } from 'react'

/** Keeps one broken panel from blanking the whole board. */
export class SafePanel extends Component<{ name: string; children: ReactNode }, { error: string | null }> {
  state = { error: null as string | null }
  static getDerivedStateFromError(e: Error) { return { error: e.message } }
  render() {
    if (this.state.error) {
      return (
        <div className="panel safe-error">
          <b>{this.props.name} hit a snag.</b> <span>{this.state.error}</span>
          <button className="btn ghost" onClick={() => this.setState({ error: null })}>Retry</button>
        </div>
      )
    }
    return this.props.children
  }
}
