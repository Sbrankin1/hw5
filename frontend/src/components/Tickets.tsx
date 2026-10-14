import { useState } from 'react'
import type { Ticket } from '../types'

const TYPE: Record<string, { label: string; icon: string }> = {
  customer_order: { label: 'Customer order', icon: '👕' },
  rent_notice: { label: 'Rent notice', icon: '🏛️' },
  price_override: { label: 'Bulk discount', icon: '🧥' },
}

const STATUS: Record<Ticket['status'], string> = {
  open: 'Open',
  in_progress: 'Back with the team',
  awaiting_approval: 'Awaiting approval',
  blocked: 'Blocked',
  resolved: 'Resolved',
}

interface Props {
  tickets: Ticket[]
  selected: number | null
  runningTicket: number | null
  onSelect: (id: number) => void
  onRun: (id: number, fresh: boolean) => void
  canRun: boolean
}

export function TicketRail({ tickets, selected, runningTicket, onSelect, onRun, canRun }: Props) {
  const current = tickets.find((t) => t.id === selected) ?? null
  const [fresh, setFresh] = useState(false)
  return (
    <aside className="rail">
      <div className="panel-head">
        <h3>Desk tickets</h3>
        <span className="panel-meta">{tickets.filter((t) => t.state === 'resolved').length}/{tickets.length} resolved</span>
      </div>
      <div className="ticket-list">
        {tickets.map((t) => {
          const type = TYPE[t.type] ?? { label: t.type, icon: '📄' }
          const resolved = t.state === 'resolved'
          return (
            <button
              key={t.id}
              className={`ticket ${selected === t.id ? 'selected' : ''} ${resolved ? 'resolved' : ''} s-${t.status}`}
              onClick={() => onSelect(t.id)}
            >
              <div className="ticket-top">
                <span className="ticket-id">#{t.id}</span>
                <span className="ticket-type">{type.icon} {type.label}</span>
                {resolved ? <span className="check" aria-label="Resolved">✔</span> : runningTicket === t.id ? <span className="spinner" /> : null}
              </div>
              <div className="ticket-subject">{t.subject}</div>
              <div className="ticket-req">{t.requester}</div>
              <div className="ticket-foot">
                <span className={`status-pill p-${t.status}`}>{STATUS[t.status]}</span>
                {t.open_approvals > 0 && <span className="mini">⏳ {t.open_approvals}</span>}
                {t.drafts > 0 && <span className="mini">📻 {t.drafts}</span>}
                {t.stock_held > 0 && <span className="mini">📦 {t.stock_held} held</span>}
              </div>
            </button>
          )
        })}
      </div>

      {current && (
        <div className="launch">
          <div className="launch-notes">{current.notes?.split('\n')[0]}</div>
          <label className="fresh">
            <input type="checkbox" checked={fresh} onChange={(e) => setFresh(e.target.checked)} /> Reset the DB to its original values first
          </label>
          <button
            className="btn rollout-btn"
            disabled={!canRun || current.state === 'resolved'}
            onClick={() => { onRun(current.id, fresh); setFresh(false) }}
          >
            {current.state === 'resolved'
              ? '✔ Mission complete'
              : current.status === 'in_progress'
                ? 'Continue the mission ▸'
                : 'Autobots, roll out ▸'}
          </button>
          {current.status === 'awaiting_approval' && (
            <div className="hint">Waiting on you: decide the approvals on the right, then continue the mission.</div>
          )}
        </div>
      )}
    </aside>
  )
}
