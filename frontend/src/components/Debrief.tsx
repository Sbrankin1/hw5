import { AGENTS, Portrait, ROLES } from '../agents'
import type { AgentEvent, AgentReport, DeskReport, Role, TicketDetail } from '../types'

interface AgentSummary {
  role: Role
  summary: string
  tools: string[]
  handedTo: Role[]
  pushback: string[]
  approvals: number[]
  drafts: number[]
  facts: string[]
  steps: number
  voice: string
}

/** One card per agent who took part in the run: what they did, in a sentence or two. */
function summarize(events: AgentEvent[], ticketId: number | null): AgentSummary[] {
  const by = new Map<Role, AgentSummary>()
  const get = (r: Role) => {
    if (!by.has(r)) by.set(r, { role: r, summary: '', tools: [], handedTo: [], pushback: [], approvals: [], drafts: [], facts: [], steps: 0, voice: '' })
    return by.get(r)!
  }
  for (const e of events) {
    if (e.event === 'agent_start') get(e.agent)
    if (e.event === 'tool_call' && e.target) {
      const s = get(e.agent)
      if (!s.tools.includes(e.target)) s.tools.push(e.target)
    }
    if (e.event === 'delegate' && e.target) get(e.agent).handedTo.push(e.target as Role)
    if (e.event === 'agent_end') {
      const s = get(e.agent)
      s.steps += e.detail?.steps ?? 0
      const out = e.detail?.output ?? {}
      if (e.agent === 'boss') {
        const desk = out as DeskReport
        const mine = desk.tickets?.find((t) => t.ticket_id === ticketId) ?? desk.tickets?.[0]
        s.summary = [mine?.summary, mine?.decision].filter(Boolean).join(' ')
        s.voice = desk.message_to_the_team ?? ''
        s.approvals = desk.approvals_waiting_on_human ?? []
        s.drafts = mine?.drafts_created ?? []
        s.pushback = desk.disagreements_settled ?? []
      } else {
        const rep = out as AgentReport
        s.summary = rep.summary ?? ''
        s.voice = rep.in_character ?? ''
        s.pushback = rep.pushback ?? []
        s.approvals = rep.approvals_requested ?? []
        s.drafts = rep.drafts_created ?? []
        s.facts = rep.facts ?? []
      }
    }
  }
  return ROLES.filter((r) => by.has(r)).map((r) => by.get(r)!)
}

export function Debrief({ events, ticket, output }: { events: AgentEvent[]; ticket: TicketDetail | null; output: DeskReport | null }) {
  const cards = summarize(events, ticket?.id ?? null)
  const benched = ROLES.filter((r) => !cards.some((c) => c.role === r))
  const drafts = ticket?.draft_messages ?? []

  return (
    <section className="debrief">
      <div className="section-title">
        <h2>Mission debrief{ticket ? ` · #${ticket.id}` : ''}</h2>
        <p>What each agent did on this ticket, from the latest run.</p>
      </div>

      {cards.length === 0 ? (
        <div className="empty-note big">No run yet for this ticket. Roll out the team and each agent's work shows up here.</div>
      ) : (
        <div className="debrief-grid">
          {cards.map((c) => {
            const a = AGENTS[c.role]
            return (
              <article key={c.role} className="debrief-card" style={{ ['--agent' as string]: a.color }}>
                <header>
                  <Portrait role={c.role} size={52} />
                  <div>
                    <div className="db-name">{a.name}</div>
                    <div className="db-title">{a.title}</div>
                  </div>
                </header>
                <p className="db-summary">{c.summary || 'Still working…'}</p>
                {(c.voice || (c.role === 'boss' && output?.message_to_the_team)) && (
                  <blockquote className="db-quote" style={{ borderLeftColor: a.color }}>“{c.voice || output?.message_to_the_team}”</blockquote>
                )}
                {c.pushback.length > 0 && (
                  <div className={`db-pushback ${c.role === 'boss' ? 'db-ruling' : ''}`}>
                    <div className="db-label">{c.role === 'boss' ? 'Disagreements settled' : 'Pushback'}</div>
                    {c.pushback.map((p, i) => <div key={i}>⚡ {p}</div>)}
                  </div>
                )}
                <div className="db-chips">
                  {c.tools.map((t) => <code key={t}>{t}</code>)}
                  {c.handedTo.map((r, i) => <span key={i} className="chip-hand">➜ {AGENTS[r].short}</span>)}
                  {c.approvals.length > 0 && <span className="chip-appr">⏳ approvals {c.approvals.map((x) => `A-${x}`).join(', ')}</span>}
                  {c.drafts.length > 0 && <span className="chip-draft">📻 drafts {c.drafts.join(', ')}</span>}
                </div>
              </article>
            )
          })}
          {benched.length > 0 && (
            <article className="debrief-card benched">
              <div className="db-label">Not needed on this ticket</div>
              <div className="benched-row">
                {benched.map((r) => (
                  <div key={r} className="benched-agent"><Portrait role={r} size={36} /> {AGENTS[r].short}</div>
                ))}
              </div>
            </article>
          )}
        </div>
      )}

      {drafts.length > 0 && (
        <div className="transmissions">
          <div className="tx-title">
            <img className="tx-bee" src="/agents/customer_service_full.png" alt="" onError={(e) => (e.currentTarget.style.display = 'none')} />
            <h3>📻 Bumblebee's transmissions <span>drafts only, never sent</span></h3>
          </div>
          <div className="tx-grid">
            {drafts.map((d) => (
              <div key={d.id} className="tx">
                <div className="tx-head"><b>To {d.recipient}</b><span>{d.subject}</span></div>
                <pre>{d.body}</pre>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
