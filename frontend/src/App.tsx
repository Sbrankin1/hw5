import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, API_URL } from './api'
import { Insignia } from './agents'
import { Bridge } from './components/Bridge'
import { CommsLog } from './components/CommsLog'
import { Debrief } from './components/Debrief'
import { ApprovalsPanel, CashPanel, SynergyMeter } from './components/Panels'
import { RollOut, RulingBanner, StalemateOverlay } from './components/Showdown'
import { SafePanel } from './components/SafePanel'
import { TicketRail } from './components/Tickets'
import type { Approval, Cash, Ticket, TicketDetail } from './types'
import { usePlayback, useRunFeed } from './useRun'

type Toast = { id: number; tone: 'ok' | 'warn' | 'bad'; text: string }

const RUNS_KEY = 'cc.runs'
const loadRuns = (): Record<number, string> => {
  try { return JSON.parse(localStorage.getItem(RUNS_KEY) ?? '{}') } catch { return {} }
}

/** Poll a loader every `ms` while mounted; returns the latest value and a manual refresh. */
function usePoll<T>(load: () => Promise<T>, ms: number, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const refresh = useCallback(async () => {
    try { setData(await load()); setError(null) } catch (e) { setError((e as Error).message) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  useEffect(() => {
    refresh()
    const t = window.setInterval(refresh, ms)
    return () => window.clearInterval(t)
  }, [refresh, ms])
  return { data, error, refresh }
}

export default function App() {
  const [selected, setSelected] = useState<number | null>(101)
  const [runs, setRuns] = useState<Record<number, string>>(loadRuns)
  const [rollOut, setRollOut] = useState<number | null>(null)
  const [toasts, setToasts] = useState<Toast[]>([])
  const [rulingClosed, setRulingClosed] = useState<string | null>(null)

  const health = usePoll(() => api.health(), 4000)
  const tickets = usePoll(() => api.tickets(), 2500)
  const desk = usePoll(() => api.approvals('all'), 2000)
  const detail = usePoll<TicketDetail | null>(() => (selected ? api.ticket(selected) : Promise.resolve(null)), 3000, [selected])

  const runId = (selected && (runs[selected] ?? detail.data?.last_run_id)) || null
  const feed = useRunFeed(runId)
  const play = usePlayback(feed.events, runId)

  const running = feed.run?.status === 'running'
  const runInProgress = Boolean(health.data?.run_in_progress) || running
  const ticketList: Ticket[] = tickets.data ?? []
  const current = ticketList.find((t) => t.id === selected) ?? null
  const approvals: Approval[] = desk.data?.approvals ?? []
  const cash: Cash | null = desk.data?.cash ?? null
  const ledger = useMemo(() => approvals.filter((a) => a.status === 'approved' && a.payment_id && a.amount > 0), [approvals])
  const offline = Boolean(health.error)

  useEffect(() => { localStorage.setItem(RUNS_KEY, JSON.stringify(runs)) }, [runs])

  const toast = useCallback((tone: Toast['tone'], text: string) => {
    const id = Date.now() + Math.random()
    setToasts((t) => [...t, { id, tone, text }])
    window.setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 6000)
  }, [])

  // When a run finishes, refresh everything and say what happened.
  useEffect(() => {
    if (!feed.run || feed.run.status === 'running') return
    tickets.refresh(); desk.refresh(); detail.refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [feed.run?.status])

  useEffect(() => {
    if (!play.finished || !feed.run) return
    if (feed.run.status === 'error') toast('bad', `Run failed: ${feed.run.error}`)
    else if (current?.status === 'resolved') toast('ok', `Ticket #${current.id} resolved. Mission complete.`)
    else if (approvals.some((a) => a.ticket_id === selected && a.status === 'pending')) toast('warn', 'Human approval needed: the team has prepared it, your call.')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [play.finished])

  const startRun = async (id: number, fresh: boolean) => {
    try {
      const info = await api.runTicket(id, fresh)
      setRuns((r) => ({ ...r, [id]: info.run_id }))
      setRollOut(id)
      if (fresh) toast('ok', 'Database reset to its original values for a fresh run.')
      health.refresh()
    } catch (e) {
      toast('bad', (e as Error).message)
    }
  }

  const decide = async (a: Approval, decision: 'approve' | 'reject', name: string) => {
    try {
      const res = await api.decide(a.id, decision, name)
      toast(decision === 'approve' ? 'ok' : 'warn',
        decision === 'approve'
          ? `Approved A-${a.id}${a.amount ? `: −$${a.amount.toFixed(2)} from checking` : ''}.`
          : `Rejected A-${a.id}.`)
      if (res.ticket?.status === 'in_progress') toast('warn', `Ticket #${res.ticket.id} is back with the team. Continue the mission to close it out.`)
      desk.refresh(); tickets.refresh(); detail.refresh()
    } catch (e) {
      toast('bad', (e as Error).message)
    }
  }

  const reset = async () => {
    if (!window.confirm('Reset the database to its original values? This clears approvals, drafts, holds and payments.')) return
    try {
      await api.reset()
      setRuns({})
      toast('ok', 'Database reset. Checking is back to $3,400.00.')
      tickets.refresh(); desk.refresh(); detail.refresh()
    } catch (e) {
      toast('bad', (e as Error).message)
    }
  }

  const showRuling = play.ruling && rulingClosed !== runId && !play.stalemate

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <Insignia size={46} />
          <div>
            <div className="brand-yale">Campus Customs <em>at Yale</em></div>
            <div className="brand-ops">AUTOBOT OPERATIONS DESK</div>
          </div>
        </div>
        <div className="topbar-meta">
          <span className="meta-chip">Shop day <b>{health.data?.shop_today ?? '—'}</b></span>
          <span className={`meta-chip ${offline ? 'bad' : 'ok'}`}>
            <i className="led" /> {offline ? `Backend offline (${API_URL})` : runInProgress ? 'Team deployed' : 'Backend online'}
          </span>
          <button className="btn ghost" onClick={reset} disabled={runInProgress}>⟲ Reset DB</button>
        </div>
      </header>

      {offline && (
        <div className="offline-banner">
          Can't reach the backend at {API_URL}. Start it with <code>cd backend && uvicorn main:app --reload --port 8000</code>.
        </div>
      )}

      <main className="layout">
        <TicketRail
          tickets={ticketList}
          selected={selected}
          runningTicket={running ? selected : null}
          onSelect={setSelected}
          onRun={startRun}
          canRun={!runInProgress && !offline}
        />

        <section className="center">
          <div className="center-head">
            <div>
              <div className="eyebrow">Command bridge</div>
              <h1>{current ? `#${current.id} · ${current.subject}` : 'Select a ticket'}</h1>
              <p className="sub">{current ? `${current.requester} · ${current.notes?.split('\n')[0] ?? ''}` : ''}</p>
            </div>
            <div className="center-actions">
              {running && <span className="progress">Event {play.played}/{play.total}</span>}
              {play.played < play.total && <button className="btn ghost" onClick={play.skip}>Skip to now ⏭</button>}
            </div>
          </div>
          <SafePanel name="The bridge"><Bridge ticket={current} scene={play.scene} cards={play.cards} running={running || play.played < play.total} finished={play.finished} /></SafePanel>
          <SafePanel name="The comms log"><CommsLog lines={play.lines} live={running} /></SafePanel>
        </section>

        <aside className="side">
          <CashPanel cash={cash} ledger={ledger} />
          <SynergyMeter value={play.synergy} mood={play.mood} trail={play.synergyTrail} live={running} />
          <ApprovalsPanel approvals={approvals} busy={runInProgress} onDecide={decide} />
        </aside>
      </main>

      <SafePanel name="The debrief"><Debrief events={feed.events} ticket={detail.data} output={feed.run?.output ?? null} /></SafePanel>

      <footer className="footer">
        Campus Customs · Homework 5 · agents prepare, humans decide · backend {API_URL}
        <div className="credits">
          Character images: <a href="https://wallpapers.com/transformers-png" target="_blank" rel="noreferrer">wallpapers.com</a>
          {' '}(Megatron by voyage4733, Ratchet stand-in by stalkeras96; see public/agents/CREDITS.md). Transformers is a trademark of Hasbro.
        </div>
      </footer>

      {rollOut && <RollOut ticketId={rollOut} onDone={() => setRollOut(null)} />}
      {play.stalemate && <StalemateOverlay key={play.stalemate.seq} stalemate={play.stalemate} onDone={play.dismissStalemate} />}
      {showRuling && <RulingBanner ruling={play.ruling!} onClose={() => setRulingClosed(runId)} />}

      <div className="toasts">
        {toasts.map((t) => <div key={t.id} className={`toast ${t.tone}`}>{t.text}</div>)}
      </div>
    </div>
  )
}
