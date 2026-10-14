import { useEffect, useRef, useState } from 'react'
import { Portrait } from '../agents'
import type { Stalemate } from '../useRun'

const STALEMATE_MS = 9000

/** Megatron pushes back on Optimus: two forces of nature, locked. */
export function StalemateOverlay({ stalemate, onDone }: { stalemate: Stalemate; onDone: () => void }) {
  const [shown, setShown] = useState(0)
  const [left, setLeft] = useState(STALEMATE_MS)
  const lines = stalemate.pushback
  const done = useRef(onDone)
  done.current = onDone  // the board re-renders every couple of seconds; don't restart the clock

  useEffect(() => {
    const reveal = window.setInterval(() => setShown((n) => Math.min(n + 1, lines.length)), 1500)
    const countdown = window.setInterval(() => setLeft((ms) => Math.max(0, ms - 100)), 100)
    const finish = window.setTimeout(() => done.current(), STALEMATE_MS)
    return () => { window.clearInterval(reveal); window.clearInterval(countdown); window.clearTimeout(finish) }
  }, [lines.length])

  return (
    <div className="stalemate" role="dialog" aria-label="Stalemate between Optimus Prime and Megatron" onClick={onDone}>
      <div className="sm-half sm-left" />
      <div className="sm-half sm-right" />
      <div className="sm-flash" />

      <div className="sm-title">
        <div className="sm-kicker">Megatron pushes back</div>
        <h2>STALEMATE</h2>
        <div className="sm-sub">The energon reserves can't fund both visions</div>
      </div>

      <div className="sm-arena">
        <div className="sm-fighter prime">
          <div className="sm-portrait"><Portrait role="boss" size={190} speaking /></div>
          <div className="sm-name">Optimus Prime</div>
          <div className="sm-quote">"We serve the people who come to us."</div>
        </div>

        <svg className="sm-bolt" viewBox="0 0 120 300" aria-hidden>
          <defs>
            <linearGradient id="boltGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0" stopColor="#ff4b55" />
              <stop offset=".5" stopColor="#fff" />
              <stop offset="1" stopColor="#a983ff" />
            </linearGradient>
          </defs>
          <path d="M70 0 L36 128 L66 128 L28 300 L98 106 L64 106 L92 0 Z" fill="url(#boltGrad)" />
        </svg>

        <div className="sm-fighter megatron">
          <div className="sm-portrait"><Portrait role="accounting" size={190} speaking /></div>
          <div className="sm-name">Megatron</div>
          <div className="sm-quote">"The ledger does not bend, Prime."</div>
        </div>
      </div>

      <div className="sm-tug" aria-hidden>
        <div className="sm-tug-red" />
        <div className="sm-tug-knot" />
      </div>

      <div className="sm-pushback">
        {lines.slice(0, Math.max(shown, 1)).map((p, i) => (
          <div key={i} className="sm-line">⚡ {p}</div>
        ))}
      </div>

      <div className="sm-foot">
        Optimus weighs the numbers… <span className="sm-timer">{Math.max(0, Math.ceil(left / 1000))}s</span>
        <button className="btn ghost" onClick={(e) => { e.stopPropagation(); onDone() }}>Let Prime rule</button>
      </div>
    </div>
  )
}

/** Optimus settles it. */
export function RulingBanner({ ruling, onClose }: { ruling: string[]; onClose: () => void }) {
  return (
    <div className="ruling" role="status">
      <div className="ruling-portrait"><Portrait role="boss" size={64} /></div>
      <div className="ruling-body">
        <div className="ruling-kicker">Prime's ruling · the stalemate is broken</div>
        {ruling.map((r, i) => <p key={i}>{r}</p>)}
      </div>
      <button className="icon-btn" onClick={onClose} aria-label="Dismiss">✕</button>
    </div>
  )
}

/** "Autobots, roll out!" as the run starts. */
export function RollOut({ ticketId, onDone }: { ticketId: number; onDone: () => void }) {
  const done = useRef(onDone)
  done.current = onDone
  useEffect(() => {
    const t = window.setTimeout(() => done.current(), 2600)
    return () => window.clearTimeout(t)
  }, [])
  return (
    <div className="rollout" onClick={onDone} aria-live="polite">
      <div className="rollout-streaks" />
      <div className="rollout-text">
        <span>AUTOBOTS,</span>
        <span className="accent">ROLL OUT!</span>
      </div>
      <div className="rollout-sub">Ticket #{ticketId} · Campus Customs operations desk</div>
    </div>
  )
}
