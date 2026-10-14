import { useEffect, useRef, useState } from 'react'
import { api } from './api'
import type { AgentEvent, RunInfo, Role } from './types'

/* ── Polling: pull a run's events from the backend as they're written ──────────────────── */

export function useRunFeed(runId: string | null) {
  const [run, setRun] = useState<RunInfo | null>(null)
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setRun(null)
    setEvents([])
    setError(null)
    if (!runId) return
    let cancelled = false
    let lastSeq = 0
    let timer: number | undefined

    const tick = async () => {
      try {
        const fresh = await api.events(runId, lastSeq)
        if (cancelled) return
        if (fresh.length) {
          lastSeq = fresh[fresh.length - 1].seq
          setEvents((prev) => [...prev, ...fresh])
        }
        let info: RunInfo | null = null
        try {
          info = await api.run(runId)
          if (!cancelled) setRun(info)
        } catch {
          /* runs from before a server restart only exist in the audit trail */
        }
        const finished = info ? info.status !== 'running' : fresh.some((e) => e.event === 'run_end')
        if (!finished && !cancelled) timer = window.setTimeout(tick, 1200)
      } catch (e) {
        if (!cancelled) {
          setError((e as Error).message)
          timer = window.setTimeout(tick, 3000)
        }
      }
    }
    tick()
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [runId])

  return { run, events, error }
}

/* ── Playback: turn events into a scene, a transcript and the team's synergy ───────────── */

export type CardState = 'standby' | 'active' | 'speaking' | 'listening' | 'working' | 'done' | 'error'

export interface Line {
  seq: number
  kind: 'talk' | 'report' | 'tool' | 'alert' | 'system' | 'pushback'
  from: Role
  to: Role | null
  text: string
  sub?: string
  status?: string | null
  at: string
}

export interface Scene {
  from: Role | null
  to: Role | null
  kind: 'delegate' | 'report' | 'tool' | 'think' | 'alert' | 'idle'
  bubble: string | null
  tool: string | null
}

export interface Stalemate {
  seq: number
  pushback: string[]
  summary: string
  ruling: string[] | null
}

export interface Playback {
  scene: Scene
  lines: Line[]
  cards: Record<Role, CardState>
  synergy: number
  synergyTrail: number[]
  mood: string
  stalemate: Stalemate | null
  ruling: string[] | null
  played: number
  total: number
  finished: boolean
  dismissStalemate: () => void
  skip: () => void
}

const ROLE_SET = new Set<string>(['boss', 'inventory', 'accounting', 'facilities', 'customer_service'])
/** An event's target is a teammate only for hand-offs and reports; otherwise it's a tool or check name. */
const asRole = (t: string | null | undefined): Role | null => (t && ROLE_SET.has(t) ? (t as Role) : null)

const START_SYNERGY = 72
const clamp = (n: number) => Math.max(4, Math.min(100, n))

export function moodFor(s: number): string {
  if (s >= 90) return 'Unstoppable — rolling out as one'
  if (s >= 75) return 'In sync'
  if (s >= 58) return 'Steady'
  if (s >= 40) return 'Grinding gears'
  if (s >= 22) return 'Sparks flying'
  return 'Stalemate'
}

function pushbackOf(e: AgentEvent): string[] {
  const p = e.detail?.report?.pushback
  return Array.isArray(p) ? p.filter(Boolean) : []
}

/** How each kind of event moves the team's synergy (0–100). */
function synergyDelta(e: AgentEvent): number {
  switch (e.event) {
    case 'delegate': return 3
    case 'report': return pushbackOf(e).length ? (e.agent === 'accounting' ? -22 : -8) : 5
    case 'delegate_refused': return -5
    case 'tool_result': return e.status === 'ok' ? 1 : -4
    case 'guardrail': return e.status === 'refused' ? -8 : -12
    case 'model_request':
      return (e.detail?.parts ?? []).some((p: any) => p.type === 'retry') ? -3 : 0
    case 'agent_end': return 2
    case 'agent_error': return -15
    case 'run_end': {
      if (e.status !== 'ok') return -25
      const settled = e.detail?.output?.disagreements_settled?.length ?? 0
      return 10 + settled * 8
    }
    default: return 0
  }
}

/** How long each event stays on screen, so people can follow the conversation. */
function holdFor(e: AgentEvent): number {
  switch (e.event) {
    case 'delegate': case 'report': return 2200
    case 'model_response': return e.said ? 1800 : 650
    case 'tool_call': return 900
    case 'tool_result': return e.status === 'ok' ? 350 : 1200
    case 'guardrail': case 'delegate_refused': return 1800
    case 'run_start': case 'run_end': return 1400
    case 'model_request': return 60
    default: return 400
  }
}

const clip = (s: string | null | undefined, n = 220) => (!s ? '' : s.length > n ? s.slice(0, n - 1) + '…' : s)

function toLine(e: AgentEvent): Line | null {
  const base = { seq: e.seq, from: e.agent, at: e.at, status: e.status }
  switch (e.event) {
    case 'run_start':
      return { ...base, kind: 'system', to: null, text: 'Autobots, roll out!', sub: clip(e.detail?.prompt, 160) }
    case 'agent_start':
      return { ...base, kind: 'system', to: null, text: 'joins the mission', sub: clip(e.detail?.task, 160) }
    case 'delegate':
      return { ...base, kind: 'talk', to: asRole(e.target), text: clip(e.said, 320) }
    case 'report': {
      const pb = pushbackOf(e)
      return {
        ...base, kind: pb.length ? 'pushback' : 'report', to: asRole(e.target),
        text: clip(e.said, 320), sub: pb.length ? pb.join(' · ') : undefined,
      }
    }
    case 'model_response':
      return e.said ? { ...base, kind: 'talk', to: null, text: clip(e.said, 280) } : null
    case 'tool_call':
      return { ...base, kind: 'tool', to: null, text: e.target ?? 'tool', sub: clip(JSON.stringify(e.detail?.args ?? {}), 140) }
    case 'tool_result':
      return e.status === 'ok' ? null : { ...base, kind: 'alert', to: null, text: `${e.target} refused`, sub: clip(e.did, 200) }
    case 'delegate_refused':
      return { ...base, kind: 'alert', to: asRole(e.target), text: 'Hand-off blocked by the loop guard', sub: clip(e.detail?.reason, 200) }
    case 'guardrail':
      return { ...base, kind: 'alert', to: null, text: 'Guardrail tripped', sub: clip((e.detail?.problems ?? []).join(' · '), 260) }
    case 'agent_end':
      return { ...base, kind: 'system', to: null, text: 'signs off', sub: clip(e.said, 200) }
    case 'agent_error':
      return { ...base, kind: 'alert', to: null, text: 'went down', sub: clip(e.did, 200) }
    case 'run_end':
      return {
        ...base, kind: e.status === 'ok' ? 'system' : 'alert', to: null,
        text: e.status === 'ok' ? 'Mission debrief filed' : 'Mission failed', sub: e.status === 'ok' ? undefined : clip(e.did, 200),
      }
    default:
      return null
  }
}

const IDLE: Scene = { from: null, to: null, kind: 'idle', bubble: null, tool: null }
const ALL_STANDBY = (): Record<Role, CardState> => ({
  boss: 'standby', inventory: 'standby', accounting: 'standby', facilities: 'standby', customer_service: 'standby',
})

export function usePlayback(events: AgentEvent[], runId: string | null): Playback {
  const [played, setPlayed] = useState(0)
  const [scene, setScene] = useState<Scene>(IDLE)
  const [lines, setLines] = useState<Line[]>([])
  const [cards, setCards] = useState<Record<Role, CardState>>(ALL_STANDBY)
  const [synergy, setSynergy] = useState(START_SYNERGY)
  const [trail, setTrail] = useState<number[]>([START_SYNERGY])
  const [stalemate, setStalemate] = useState<Stalemate | null>(null)
  const [ruling, setRuling] = useState<string[] | null>(null)
  const inRoom = useRef<Set<Role>>(new Set())
  const signedOff = useRef<Set<Role>>(new Set())
  const fastForward = useRef(false)
  const hadStalemate = useRef(false)  // one showdown per run; later pushback shows in the log

  // New run → reset the stage.
  useEffect(() => {
    setPlayed(0); setScene(IDLE); setLines([]); setCards(ALL_STANDBY()); setSynergy(START_SYNERGY)
    setTrail([START_SYNERGY]); setStalemate(null); setRuling(null)
    inRoom.current = new Set(); signedOff.current = new Set(); fastForward.current = false; hadStalemate.current = false
  }, [runId])

  // Play the next event once the previous one has had its moment on stage.
  useEffect(() => {
    if (stalemate || played >= events.length) return
    const e = events[played]
    const backlog = events.length - played
    const speed = fastForward.current ? 0.05 : backlog > 25 ? 0.35 : backlog > 10 ? 0.6 : 1
    const wait = played === 0 ? 0 : holdFor(events[played - 1]) * speed

    const t = window.setTimeout(() => {
      apply(e)
      setPlayed((n) => n + 1)
    }, wait)
    return () => window.clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [events, played, stalemate])

  function apply(e: AgentEvent) {
    const line = toLine(e)
    if (line) setLines((prev) => [...prev, line])

    const d = synergyDelta(e)
    if (d) {
      setSynergy((s) => {
        const next = clamp(s + d)
        setTrail((t) => [...t.slice(-59), next])
        return next
      })
    }

    setCards((prev) => {
      const c = { ...prev }
      for (const r of inRoom.current) if (c[r] === 'speaking' || c[r] === 'listening' || c[r] === 'working') c[r] = 'active'
      switch (e.event) {
        case 'agent_start': inRoom.current.add(e.agent); signedOff.current.delete(e.agent); c[e.agent] = 'active'; break
        case 'agent_end': signedOff.current.add(e.agent); c[e.agent] = 'done'; break
        case 'agent_error': c[e.agent] = 'error'; break
        case 'delegate': c[e.agent] = 'speaking'; { const t = asRole(e.target); if (t) c[t] = 'listening' }; break
        case 'report': c[e.agent] = 'speaking'; { const t = asRole(e.target); if (t) c[t] = 'listening' }; break
        case 'model_response': c[e.agent] = e.said ? 'speaking' : 'working'; break
        case 'tool_call': case 'tool_result': c[e.agent] = 'working'; break
        case 'guardrail': case 'delegate_refused': c[e.agent] = 'error'; break
      }
      // Anyone who has signed off goes back to "signed off" once they've finished speaking.
      for (const r of signedOff.current) if (c[r] === 'active') c[r] = 'done'
      return c
    })

    switch (e.event) {
      case 'delegate':
        setScene({ from: e.agent, to: asRole(e.target), kind: 'delegate', bubble: clip(e.said, 180), tool: null }); break
      case 'report':
        setScene({ from: e.agent, to: asRole(e.target), kind: 'report', bubble: clip(e.said, 180), tool: null })
        if (e.agent === 'accounting' && pushbackOf(e).length && !fastForward.current && !hadStalemate.current) {
          hadStalemate.current = true
          setStalemate({ seq: e.seq, pushback: pushbackOf(e), summary: e.said ?? '', ruling: null })
        }
        break
      case 'model_response':
        if (e.said) setScene({ from: e.agent, to: null, kind: 'think', bubble: clip(e.said, 180), tool: null })
        break
      case 'tool_call':
        setScene({ from: e.agent, to: null, kind: 'tool', bubble: null, tool: e.target }); break
      case 'guardrail': case 'delegate_refused':
        setScene({ from: e.agent, to: asRole(e.target), kind: 'alert', bubble: clip(e.did, 160), tool: null }); break
      case 'agent_end':
        if (e.agent === 'boss') {
          const settled = e.detail?.output?.disagreements_settled
          if (Array.isArray(settled) && settled.length) setRuling(settled)
        }
        break
      case 'run_end':
        setScene(IDLE); break
    }
  }

  const finished = events.length > 0 && played >= events.length && events.some((e) => e.event === 'run_end')

  return {
    scene, lines, cards, synergy, synergyTrail: trail, mood: moodFor(synergy), stalemate, ruling,
    played, total: events.length, finished,
    dismissStalemate: () => setStalemate(null),
    skip: () => { fastForward.current = true; setStalemate(null) },
  }
}
