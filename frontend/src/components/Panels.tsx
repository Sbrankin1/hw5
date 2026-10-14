import { useEffect, useRef, useState } from 'react'
import { AGENTS, Portrait } from '../agents'
import type { Approval, Cash, Role } from '../types'

const money = (n: number) =>
  (n < 0 ? '−$' : '$') + Math.abs(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

/* ── Synergy: a gauge for how well the team is working together ─────────────────────────── */

export function SynergyMeter({ value, mood, trail, live }: { value: number; mood: string; trail: number[]; live: boolean }) {
  const angle = -90 + (value / 100) * 180
  const tone = value >= 75 ? 'good' : value >= 45 ? 'mid' : 'bad'
  const pts = trail.map((v, i) => `${(i / Math.max(trail.length - 1, 1)) * 100},${30 - (v / 100) * 28}`).join(' ')
  return (
    <div className={`panel synergy tone-${tone}`}>
      <div className="panel-head">
        <h3>Team synergy</h3>
        <span className="panel-meta">{live ? 'live' : 'last run'}</span>
      </div>
      <div className="gauge">
        <svg viewBox="0 0 200 112" aria-hidden>
          <defs>
            <linearGradient id="synGrad" x1="0" x2="1">
              <stop offset="0" stopColor="#e5484d" />
              <stop offset=".5" stopColor="#f5c518" />
              <stop offset="1" stopColor="#3ccf7a" />
            </linearGradient>
          </defs>
          <path d="M20 100 A80 80 0 0 1 180 100" fill="none" stroke="rgba(0,53,107,.1)" strokeWidth="16" strokeLinecap="round" />
          <path d="M20 100 A80 80 0 0 1 180 100" fill="none" stroke="url(#synGrad)" strokeWidth="16" strokeLinecap="round"
                strokeDasharray={`${(value / 100) * 251.3} 999`} className="gauge-arc" />
          <g className="needle" style={{ transform: `rotate(${angle}deg)` }}>
            <line x1="100" y1="100" x2="100" y2="34" stroke="#00356b" strokeWidth="3" strokeLinecap="round" />
            <circle cx="100" cy="100" r="7" fill="#00356b" />
          </g>
        </svg>
        <div className="gauge-value">{Math.round(value)}<small>%</small></div>
      </div>
      <div className="mood">{mood}</div>
      <svg className="spark" viewBox="0 0 100 32" preserveAspectRatio="none" aria-hidden>
        <polyline points={pts} fill="none" stroke="currentColor" strokeWidth="1.6" vectorEffect="non-scaling-stroke" />
      </svg>
      <div className="synergy-legend">Teamwork & clean reports lift it · refusals, guardrails and pushback drain it</div>
    </div>
  )
}

/* ── Checking balance: live, animates on every payment ─────────────────────────────────── */

function useCountUp(target: number) {
  const [shown, setShown] = useState(target)
  const from = useRef(target)
  useEffect(() => {
    const start = performance.now()
    const a = from.current
    let raf = 0
    const step = (t: number) => {
      const k = Math.min(1, (t - start) / 900)
      const eased = 1 - Math.pow(1 - k, 3)
      setShown(a + (target - a) * eased)
      if (k < 1) raf = requestAnimationFrame(step)
      else from.current = target
    }
    raf = requestAnimationFrame(step)
    // Background tabs pause animation frames: always land on the true figure.
    const settle = window.setTimeout(() => { setShown(target); from.current = target }, 1000)
    return () => { cancelAnimationFrame(raf); window.clearTimeout(settle) }
  }, [target])
  return shown
}

export function CashPanel({ cash, ledger }: { cash: Cash | null; ledger: Approval[] }) {
  const balance = cash?.balance ?? 0
  const shown = useCountUp(balance)
  const [delta, setDelta] = useState<{ amount: number; key: number } | null>(null)
  const prev = useRef<number | null>(null)

  useEffect(() => {
    if (cash == null) return
    if (prev.current != null && prev.current !== cash.balance) setDelta({ amount: cash.balance - prev.current, key: Date.now() })
    prev.current = cash.balance
  }, [cash])

  const projected = cash?.balance_if_all_pending_approved ?? 0
  const pct = cash && cash.balance > 0 ? Math.max(0, Math.min(100, (projected / cash.balance) * 100)) : 0

  return (
    <div className="panel cash">
      <div className="panel-head">
        <h3>Checking</h3>
        <span className="panel-meta">cash_accounts · as of {cash?.as_of ?? '—'}</span>
      </div>
      <div className="cash-figure">
        <span className="cash-amount">{cash ? money(shown) : '—'}</span>
        {delta && <span key={delta.key} className={`cash-delta ${delta.amount < 0 ? 'out' : 'in'}`}>{money(delta.amount)}</span>}
      </div>
      {cash && (
        <>
          <div className="cash-bar" title="Balance left if every pending approval goes through">
            <div className={`cash-bar-fill ${projected < 0 ? 'neg' : ''}`} style={{ width: `${pct}%` }} />
          </div>
          <div className="cash-row">
            <span>Waiting to go out</span><b>{money(cash.pending_cash_out)}</b>
          </div>
          <div className={`cash-row ${projected < 0 ? 'neg' : ''}`}>
            <span>If all pending approved</span><b>{money(projected)}</b>
          </div>
        </>
      )}
      <div className="ledger">
        <div className="ledger-title">Payments</div>
        {ledger.length === 0 && <div className="empty-note">No money has moved yet.</div>}
        {ledger.map((a) => (
          <div key={a.id} className="ledger-row">
            <span className={`kind-badge k-${a.kind}`}>{KIND[a.kind]}</span>
            <span className="ledger-who">#{a.ticket_id ?? '—'} · by {a.decided_by}</span>
            <b>−{money(a.amount)}</b>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ── Approvals: the human's desk. Nothing moves money except a click here. ─────────────── */

const KIND: Record<Approval['kind'], string> = {
  invoice: 'Invoice', rent: 'Rent', purchase_order: 'Purchase order', discount: 'Discount',
}

interface ApprovalsProps {
  approvals: Approval[]
  busy: boolean
  onDecide: (a: Approval, decision: 'approve' | 'reject', name: string) => Promise<void>
}

export function ApprovalsPanel({ approvals, busy, onDecide }: ApprovalsProps) {
  const [name, setName] = useState(() => localStorage.getItem('cc.approver') ?? '')
  const [working, setWorking] = useState<number | null>(null)
  const open = approvals.filter((a) => a.status === 'pending' || a.status === 'awaiting_signoff')
  const decided = approvals.filter((a) => a.status === 'approved' || a.status === 'rejected').slice(-4).reverse()
  const needsHuman = open.some((a) => a.status === 'pending')

  useEffect(() => { localStorage.setItem('cc.approver', name) }, [name])

  const decide = async (a: Approval, d: 'approve' | 'reject') => {
    setWorking(a.id)
    try { await onDecide(a, d, name.trim()) } finally { setWorking(null) }
  }

  return (
    <div className={`panel approvals ${needsHuman ? 'needs-human' : ''}`}>
      <div className="panel-head">
        <h3>Human approvals</h3>
        <span className="panel-meta">{needsHuman ? 'Your call' : open.length ? 'Waiting on Megatron' : 'All clear'}</span>
      </div>
      <label className="approver">
        <span>Approving as</span>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" />
      </label>
      {open.length === 0 && <div className="empty-note">Nothing waiting. Agents only prepare payments; you decide them here.</div>}
      {open.map((a) => {
        const who = AGENTS[a.requested_by as Role] ?? AGENTS.boss
        const awaiting = a.status === 'awaiting_signoff'
        return (
          <div key={a.id} className={`approval ${awaiting ? 'awaiting' : 'pending'}`}>
            <div className="approval-top">
              <span className={`kind-badge k-${a.kind}`}>{KIND[a.kind]}</span>
              <span className="approval-ticket">#{a.ticket_id ?? '—'} · A-{a.id}</span>
              <b className="approval-amount">{a.amount ? money(a.amount) : 'no cash'}</b>
            </div>
            <div className="approval-details">{a.details}</div>
            <div className="approval-by">
              <Portrait role={a.requested_by as Role} size={22} /> prepared by {who.short}
              {a.signed_off_by && a.kind === 'discount' && <span className="signed"> · ✔ signed off by Megatron</span>}
            </div>
            {awaiting ? (
              <div className="awaiting-note">⏳ Waiting on Megatron's sign-off before it reaches you</div>
            ) : (
              <div className="approval-actions">
                <button className="btn approve" disabled={busy || !name.trim() || working === a.id} onClick={() => decide(a, 'approve')}>
                  ✔ Approve{a.amount ? ` ${money(a.amount)}` : ''}
                </button>
                <button className="btn reject" disabled={busy || !name.trim() || working === a.id} onClick={() => decide(a, 'reject')}>
                  ✕ Reject
                </button>
              </div>
            )}
          </div>
        )
      })}
      {busy && open.some((a) => a.status === 'pending') && <div className="hint">Decisions unlock when the current run finishes.</div>}
      {!name.trim() && needsHuman && <div className="hint">Enter your name; it's recorded on the payment.</div>}
      {decided.length > 0 && (
        <div className="decided">
          {decided.map((a) => (
            <div key={a.id} className={`decided-row ${a.status}`}>
              <span>{a.status === 'approved' ? '✔' : '✕'} {KIND[a.kind]} · #{a.ticket_id}</span>
              <span>{a.amount ? money(a.amount) : '—'} · {a.decided_by}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export { money, KIND }
