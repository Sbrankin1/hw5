import { useState } from 'react'
import type { Role } from './types'

export interface AgentMeta {
  role: Role
  name: string
  short: string
  title: string
  faction: 'Autobot' | 'Decepticon'
  color: string     // primary (cards, beams)
  glow: string      // speaking glow
  tagline: string
  idCode: string
}

export const AGENTS: Record<Role, AgentMeta> = {
  boss: {
    role: 'boss', name: 'Optimus Prime', short: 'Optimus', title: 'Boss · Leader of the desk', faction: 'Autobot',
    color: '#d6202b', glow: 'rgba(214, 32, 43, .45)', tagline: 'Leads from the front.', idCode: 'YCC-001',
  },
  inventory: {
    role: 'inventory', name: 'Ratchet', short: 'Ratchet', title: 'Inventory · Stockroom medic', faction: 'Autobot',
    color: '#3f9a35', glow: 'rgba(63, 154, 53, .45)', tagline: 'This aisle is flatlining.', idCode: 'YCC-014',
  },
  accounting: {
    role: 'accounting', name: 'Megatron', short: 'Megatron', title: 'Accounting · Keeper of the energon', faction: 'Decepticon',
    color: '#7a4fd6', glow: 'rgba(122, 79, 214, .45)', tagline: 'The ledger is mine.', idCode: 'YCC-666',
  },
  facilities: {
    role: 'facilities', name: 'Ironhide', short: 'Ironhide', title: 'Facilities · Guardian of the base', faction: 'Autobot',
    color: '#c25a22', glow: 'rgba(194, 90, 34, .45)', tagline: "Nobody touches the base.", idCode: 'YCC-007',
  },
  customer_service: {
    role: 'customer_service', name: 'Bumblebee', short: 'Bumblebee', title: 'Customer service · Scout on the radio', faction: 'Autobot',
    color: '#c99700', glow: 'rgba(245, 197, 24, .6)', tagline: '📻 "Message received."', idCode: 'YCC-042',
  },
}

export const ROLES: Role[] = ['boss', 'inventory', 'accounting', 'facilities', 'customer_service']

export const agent = (role: string | null | undefined): AgentMeta =>
  AGENTS[(role as Role) ?? 'boss'] ?? AGENTS.boss

/* ── Portraits: original geometric robot heads, one per character ─────────────────────────── */

export function Avatar({ role, size = 72, speaking = false }: { role: Role; size?: number; speaking?: boolean }) {
  const eye = speaking ? 'url(#eyeHot)' : 'url(#eye)'
  const common = (
    <defs>
      <radialGradient id="eye" cx="50%" cy="50%" r="60%">
        <stop offset="0%" stopColor="#e6fbff" />
        <stop offset="60%" stopColor="#5fd3ff" />
        <stop offset="100%" stopColor="#1478c8" />
      </radialGradient>
      <radialGradient id="eyeHot" cx="50%" cy="50%" r="60%">
        <stop offset="0%" stopColor="#ffffff" />
        <stop offset="50%" stopColor="#9ff0ff" />
        <stop offset="100%" stopColor="#2aa7ff" />
      </radialGradient>
      <radialGradient id="eyeRed" cx="50%" cy="50%" r="60%">
        <stop offset="0%" stopColor="#fff1f1" />
        <stop offset="55%" stopColor="#ff4d4d" />
        <stop offset="100%" stopColor="#9c0d0d" />
      </radialGradient>
      <linearGradient id="chrome" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#f4f7fa" />
        <stop offset="55%" stopColor="#b9c3cf" />
        <stop offset="100%" stopColor="#7d8896" />
      </linearGradient>
    </defs>
  )

  const heads: Record<Role, React.ReactNode> = {
    boss: (
      <>
        <rect x="14" y="10" width="7" height="34" rx="3" fill="#2a5fc4" />
        <rect x="79" y="10" width="7" height="34" rx="3" fill="#2a5fc4" />
        <path d="M24 28 Q50 6 76 28 L78 60 Q50 70 22 60 Z" fill="#1d4fa8" stroke="#0d2c66" strokeWidth="2" />
        <path d="M44 14 L50 8 L56 14 L54 30 L46 30 Z" fill="#2a5fc4" stroke="#0d2c66" strokeWidth="1.5" />
        <path d="M30 40 H70 L68 52 H32 Z" fill="#0d1b2e" />
        <rect x="34" y="43" width="12" height="6" rx="2" fill={eye} />
        <rect x="54" y="43" width="12" height="6" rx="2" fill={eye} />
        <path d="M32 56 H68 L64 84 Q50 90 36 84 Z" fill="url(#chrome)" stroke="#5b6573" strokeWidth="1.5" />
        {[40, 45, 50, 55, 60].map((x) => <rect key={x} x={x - 1} y="62" width="2" height="16" fill="#6b7685" />)}
      </>
    ),
    accounting: (
      <>
        <path d="M18 34 Q20 8 50 6 Q80 8 82 34 L84 64 Q50 74 16 64 Z" fill="#6f7884" stroke="#2c323a" strokeWidth="2" />
        <path d="M44 6 H56 L58 40 H42 Z" fill="#9aa3ae" stroke="#2c323a" strokeWidth="1.5" />
        <path d="M18 40 L8 30 L12 60 L20 62 Z" fill="#4e5661" />
        <path d="M82 40 L92 30 L88 60 L80 62 Z" fill="#4e5661" />
        <path d="M28 42 H72 L70 54 H30 Z" fill="#14171c" />
        <path d="M33 45 L46 46 L45 51 L34 50 Z" fill="url(#eyeRed)" />
        <path d="M67 45 L54 46 L55 51 L66 50 Z" fill="url(#eyeRed)" />
        <path d="M32 58 H68 L62 86 Q50 92 38 86 Z" fill="url(#chrome)" stroke="#4e5661" strokeWidth="1.5" />
        <path d="M40 70 H60" stroke="#4e5661" strokeWidth="3" strokeLinecap="round" />
        <circle cx="50" cy="20" r="4" fill="#7a4fd6" />
      </>
    ),
    customer_service: (
      <>
        <circle cx="26" cy="16" r="6" fill="#1b1b1b" />
        <circle cx="74" cy="16" r="6" fill="#1b1b1b" />
        <rect x="23" y="16" width="6" height="18" fill="#1b1b1b" />
        <rect x="71" y="16" width="6" height="18" fill="#1b1b1b" />
        <path d="M20 34 Q50 12 80 34 L80 66 Q50 78 20 66 Z" fill="#f5c518" stroke="#8a6d00" strokeWidth="2" />
        <path d="M44 16 H56 V36 H44 Z" fill="#1b1b1b" />
        <circle cx="37" cy="46" r="8" fill="#0d1b2e" />
        <circle cx="63" cy="46" r="8" fill="#0d1b2e" />
        <circle cx="37" cy="46" r="5.5" fill={eye} />
        <circle cx="63" cy="46" r="5.5" fill={eye} />
        <path d="M32 60 H68 L64 82 Q50 88 36 82 Z" fill="url(#chrome)" stroke="#6b7685" strokeWidth="1.5" />
        <rect x="40" y="66" width="20" height="8" rx="3" fill="#2b2f36" />
        {[43, 47, 51, 55].map((x) => <rect key={x} x={x} y="68" width="2" height="4" fill={speaking ? '#f5c518' : '#5b6573'} />)}
      </>
    ),
    inventory: (
      <>
        <path d="M22 30 Q50 8 78 30 L78 62 Q50 72 22 62 Z" fill="#eef2f4" stroke="#7d8896" strokeWidth="2" />
        <path d="M22 36 L14 30 L16 58 L22 60 Z" fill="#d6202b" />
        <path d="M78 36 L86 30 L84 58 L78 60 Z" fill="#d6202b" />
        <rect x="45" y="13" width="10" height="20" rx="1.5" fill="#d6202b" />
        <rect x="40" y="18" width="20" height="10" rx="1.5" fill="#d6202b" />
        <path d="M30 40 H70 L68 52 H32 Z" fill="#163020" />
        <rect x="34" y="43" width="12" height="6" rx="2" fill={eye} />
        <rect x="54" y="43" width="12" height="6" rx="2" fill={eye} />
        <path d="M32 56 H68 L64 82 Q50 88 36 82 Z" fill="#cfd8de" stroke="#7d8896" strokeWidth="1.5" />
        <path d="M40 70 Q50 76 60 70" stroke="#5b6573" strokeWidth="2.5" fill="none" strokeLinecap="round" />
        <rect x="26" y="60" width="6" height="14" rx="2" fill="#7bc96f" />
        <rect x="68" y="60" width="6" height="14" rx="2" fill="#7bc96f" />
      </>
    ),
    facilities: (
      <>
        <rect x="16" y="18" width="68" height="50" rx="10" fill="#33373e" stroke="#15171b" strokeWidth="2" />
        <rect x="10" y="30" width="10" height="28" rx="3" fill="#8e1b1f" />
        <rect x="80" y="30" width="10" height="28" rx="3" fill="#8e1b1f" />
        <rect x="30" y="10" width="40" height="12" rx="4" fill="#8e1b1f" />
        <rect x="24" y="38" width="52" height="10" rx="3" fill="#0b0c0f" />
        <rect x="28" y="41" width="44" height="4" rx="2" fill={eye} />
        <path d="M28 58 H72 L68 84 Q50 90 32 84 Z" fill="url(#chrome)" stroke="#4e5661" strokeWidth="1.5" />
        <rect x="36" y="66" width="28" height="10" rx="2" fill="#4e5661" />
        <rect x="38" y="68" width="24" height="2" fill="#8e1b1f" />
      </>
    ),
  }

  return (
    <svg viewBox="0 0 100 100" width={size} height={size} role="img" aria-label={AGENTS[role].name}>
      {common}
      {heads[role]}
    </svg>
  )
}

/* Insignia: a Yale shield with a mechanical "Y" — the board's mark. */
export function Insignia({ size = 44 }: { size?: number }) {
  return (
    <svg viewBox="0 0 64 64" width={size} height={size} aria-hidden>
      <defs>
        <linearGradient id="insChrome" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#f6f8fb" />
          <stop offset="1" stopColor="#8d99a8" />
        </linearGradient>
      </defs>
      <path d="M32 3 58 13v20c0 15-11 24-26 28C17 57 6 48 6 33V13z" fill="#00356b" stroke="url(#insChrome)" strokeWidth="3" />
      <path d="M32 9 52 17v15c0 11-8 18-20 22-12-4-20-11-20-22V17z" fill="none" stroke="#d6202b" strokeWidth="1.5" opacity=".8" />
      <path d="M19 19h9l4 9 4-9h9l-9 16v12h-8V35z" fill="url(#insChrome)" />
      <path d="M28 41h8M28 44h8" stroke="#00356b" strokeWidth="1.2" />
    </svg>
  )
}

/* Portrait: uses a cut-out image from public/agents/<role>.png when one is there (transparent
   background), otherwise the drawn portrait above. Drop images in without touching code. */

const missingImages = new Set<Role>()  // tried once per page load; no image → drawn portrait from then on

export function Portrait({ role, size = 72, speaking = false }: { role: Role; size?: number; speaking?: boolean }) {
  const [failed, setFailed] = useState(missingImages.has(role))
  if (failed) return <Avatar role={role} size={size} speaking={speaking} />
  return (
    <img
      className="portrait-img"
      src={`/agents/${role}.png`}
      width={size}
      height={size}
      alt={AGENTS[role].name}
      onError={() => { missingImages.add(role); setFailed(true) }}
      draggable={false}
    />
  )
}
