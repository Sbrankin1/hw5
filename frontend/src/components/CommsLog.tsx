import { useEffect, useRef } from 'react'
import { AGENTS, Portrait } from '../agents'
import type { Line } from '../useRun'

const KIND_LABEL: Record<Line['kind'], string> = {
  talk: 'says',
  report: 'reports',
  tool: 'uses',
  alert: 'alert',
  system: '',
  pushback: 'pushes back',
}

export function CommsLog({ lines, live }: { lines: Line[]; live: boolean }) {
  const box = useRef<HTMLDivElement>(null)
  useEffect(() => {
    // Scroll the log box only; never move the page itself.
    const el = box.current
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [lines.length])

  return (
    <div className="comms">
      <div className="panel-head">
        <h3>Comms log</h3>
        <span className={`live-dot ${live ? 'on' : ''}`}>{live ? 'LIVE' : 'Idle'}</span>
      </div>
      <div className="comms-scroll" ref={box}>
        {lines.length === 0 && <div className="empty-note">Transmissions appear here once the team rolls out.</div>}
        {lines.map((l) => {
          const from = AGENTS[l.from]
          const to = l.to ? AGENTS[l.to] : null
          if (l.kind === 'system') {
            return (
              <div key={l.seq} className="line system" style={{ ['--agent' as string]: from.color }}>
                <span className="sys-name">{from.short}</span> {l.text}
                {l.sub && <div className="line-sub">{l.sub}</div>}
              </div>
            )
          }
          return (
            <div key={l.seq} className={`line ${l.kind}`} style={{ ['--agent' as string]: from.color }}>
              <div className="line-avatar"><Portrait role={l.from} size={34} /></div>
              <div className="line-body">
                <div className="line-head">
                  <b style={{ color: from.color }}>{from.short}</b>
                  {to ? (
                    <>
                      <span className="arrow">➜</span>
                      <b style={{ color: to.color }}>{to.short}</b>
                    </>
                  ) : (
                    <span className="verb">{KIND_LABEL[l.kind]}</span>
                  )}
                  {l.kind === 'tool' && <code className="tool-name">{l.text}</code>}
                  <time>{new Date(l.at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</time>
                </div>
                {l.kind !== 'tool' && <div className="line-text">{l.text}</div>}
                {l.sub && <div className={`line-sub ${l.kind === 'pushback' ? 'pb' : ''}`}>{l.kind === 'pushback' ? '⚡ ' : ''}{l.sub}</div>}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
