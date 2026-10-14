import { AGENTS, Portrait, ROLES } from '../agents'
import type { CardState, Scene } from '../useRun'
import type { Role, Ticket } from '../types'

// Seats around the briefing table (percent of the stage). Optimus at the head.
const SEAT: Record<Role, { x: number; y: number }> = {
  boss: { x: 50, y: 17 },
  inventory: { x: 15, y: 44 },
  accounting: { x: 85, y: 44 },
  customer_service: { x: 28, y: 82 },
  facilities: { x: 72, y: 82 },
}

const STATE_LABEL: Record<CardState, string> = {
  standby: 'Standby',
  active: 'In the room',
  speaking: 'Speaking',
  listening: 'Listening',
  working: 'Working',
  done: 'Signed off',
  error: 'Alert',
}

function seatFor(role: Role, scene: Scene): { x: number; y: number } {
  const home = SEAT[role]
  // The speaker leans in toward whoever they're talking to.
  if (scene.from === role && scene.to && SEAT[scene.to] && (scene.kind === 'delegate' || scene.kind === 'report')) {
    const target = SEAT[scene.to]
    return { x: home.x + (target.x - home.x) * 0.24, y: home.y + (target.y - home.y) * 0.24 }
  }
  return home
}

interface Props {
  ticket: Ticket | null
  scene: Scene
  cards: Record<Role, CardState>
  running: boolean
  finished: boolean
}

export function Bridge({ ticket, scene, cards, running, finished }: Props) {
  const speaker = scene.from ? AGENTS[scene.from] : null
  const from = scene.from ? seatFor(scene.from, scene) : null
  const to = scene.to && SEAT[scene.to] ? SEAT[scene.to] : null
  const resolved = ticket?.status === 'resolved'

  return (
    <div className={`bridge ${running ? 'is-live' : ''}`}>
      <div className="bridge-grid" aria-hidden />

      {/* Who is talking to whom: an energy beam from speaker to listener. */}
      <svg className="beams" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden>
        {ROLES.map((r) => (
          <line key={r} x1={50} y1={52} x2={SEAT[r].x} y2={SEAT[r].y} className={`spoke ${cards[r] !== 'standby' ? 'on' : ''}`} />
        ))}
        {from && to && speaker && (
          <g key={`${scene.from}-${scene.to}-${scene.bubble?.length}`}>
            <line x1={from.x} y1={from.y} x2={to.x} y2={to.y} className="beam-glow" style={{ stroke: speaker.color }} />
            <line x1={from.x} y1={from.y} x2={to.x} y2={to.y} className={`beam ${scene.kind}`} style={{ stroke: speaker.color }} />
            <circle r="1.3" className="beam-pulse" style={{ fill: speaker.color }}>
              <animateMotion dur="1.1s" repeatCount="indefinite" path={`M${from.x},${from.y} L${to.x},${to.y}`} />
            </circle>
          </g>
        )}
      </svg>

      {/* The briefing table: which ticket is on it. */}
      <div className={`table-hex ${resolved ? 'resolved' : ''} ${running ? 'live' : ''}`}>
        {ticket ? (
          <>
            <div className="table-id">#{ticket.id}</div>
            <div className="table-subject">{ticket.subject}</div>
            {resolved ? (
              <div className="table-done"><span className="big-check">✔</span> Mission complete</div>
            ) : (
              <div className="table-status">{running ? 'Mission in progress' : ticket.status.replace('_', ' ')}</div>
            )}
          </>
        ) : (
          <div className="table-subject">Pick a ticket</div>
        )}
      </div>

      {ROLES.map((role) => {
        const a = AGENTS[role]
        const state = cards[role]
        const pos = seatFor(role, scene)
        const isSpeaker = scene.from === role
        return (
          <div
            key={role}
            className={`id-card state-${state} ${a.faction === 'Decepticon' ? 'decepticon' : 'autobot'} ${isSpeaker ? 'is-speaker' : ''}`}
            style={{ left: `${pos.x}%`, top: `${pos.y}%`, ['--agent' as string]: a.color, ['--glow' as string]: a.glow }}
          >
            <div className="id-strip">
              <span>{a.faction}</span>
              <span className="id-code">{a.idCode}</span>
            </div>
            <div className="id-body">
              <div className="id-portrait"><Portrait role={role} size={58} speaking={state === 'speaking'} /></div>
              <div className="id-text">
                <div className="id-name">{a.name}</div>
                <div className="id-title">{a.title}</div>
                <div className="id-state"><i className="led" /> {STATE_LABEL[state]}</div>
              </div>
            </div>
            {isSpeaker && scene.kind === 'tool' && scene.tool && <div className="tool-chip">⚙ {scene.tool}</div>}
            {isSpeaker && scene.bubble && (
              <div className={`bubble ${scene.kind} ${pos.y > 60 ? 'above' : 'below'}`}>
                {scene.to && AGENTS[scene.to] && (
                  <div className="bubble-to">
                    {scene.kind === 'report' ? 'reports to' : scene.kind === 'delegate' ? 'to' : '→'} {AGENTS[scene.to].short}
                  </div>
                )}
                {role === 'customer_service' ? <span className="radio">📻 </span> : null}
                {scene.bubble}
              </div>
            )}
          </div>
        )
      })}

      {!running && !finished && ticket && (
        <div className="bridge-hint">Press <b>Autobots, roll out</b> to put the team on #{ticket.id}</div>
      )}
    </div>
  )
}
