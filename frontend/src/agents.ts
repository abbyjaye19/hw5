import type { AgentEvent, AgentName } from './types'

export interface AgentMeta {
  name: AgentName
  title: string
  role: string
  monogram: string
  /** CSS class that gives each agent its own typographic "voice" in the minutes */
  voice: string
}

export const AGENTS: Record<AgentName, AgentMeta> = {
  boss: { name: 'boss', title: 'The Boss', role: 'Chair · final calls', monogram: 'B', voice: 'voice-boss' },
  inventory: { name: 'inventory', title: 'Inventory', role: 'Stock & vendors', monogram: 'In', voice: 'voice-inventory' },
  accounting: { name: 'accounting', title: 'Accounting', role: 'Cash & margins', monogram: 'Ac', voice: 'voice-accounting' },
  facilities: { name: 'facilities', title: 'Facilities', role: 'Lease & space', monogram: 'Fa', voice: 'voice-facilities' },
  customer_service: { name: 'customer_service', title: 'Customer Service', role: 'Drafts & replies', monogram: 'CS', voice: 'voice-cs' },
}

export const SPECIALISTS: AgentName[] = ['inventory', 'accounting', 'facilities', 'customer_service']

export const isAgent = (n: string): n is AgentName => n in AGENTS

export type SeatState = 'idle' | 'working' | 'done' | 'alert'

export interface AgentActivity {
  state: SeatState
  line: string
  tools: Record<string, number>
  delegatedTo: string[]
  summary: string | null
  calls: number
}

const emptyActivity = (): AgentActivity => ({ state: 'idle', line: '', tools: {}, delegatedTo: [], summary: null, calls: 0 })

/** PydanticAI's structured-output step, not a shop tool; hidden from the board. */
export const isOutputTool = (t: string) => t.startsWith('final_result')

export function prettyTool(t: string): string {
  return t.replace(/_/g, ' ')
}

/** Fold one run's events into a per-agent picture: state, latest line, tools used, summary. */
export function activityByAgent(events: AgentEvent[]): Record<AgentName, AgentActivity> {
  const out = Object.fromEntries(Object.keys(AGENTS).map((a) => [a, emptyActivity()])) as Record<AgentName, AgentActivity>
  for (const e of events) {
    if (!isAgent(e.agent)) continue
    const a = out[e.agent]
    switch (e.event) {
      case 'run_start':
        a.state = 'working'
        a.line = e.agent === 'boss' ? 'Opening the file…' : 'Taking the brief…'
        break
      case 'model_response':
        a.calls += 1
        if (e.said) a.line = e.said
        else {
          const tools = (e.tool_calls ?? []).filter((c) => !isOutputTool(c.tool) && c.tool !== 'delegate')
          if (tools.length) a.line = `Consulting ${tools.map((c) => prettyTool(c.tool)).join(', ')}…`
        }
        break
      case 'tool_result':
        if (e.tool) a.tools[e.tool] = (a.tools[e.tool] || 0) + 1
        break
      case 'delegation':
        if (e.to_agent) {
          a.delegatedTo.push(e.to_agent)
          a.line = `Briefing ${AGENTS[e.to_agent as AgentName]?.title ?? e.to_agent}…`
        }
        break
      case 'run_end': {
        a.state = 'done'
        const o = e.output || {}
        a.summary = String(o.summary ?? o.decision ?? '')
        a.line = a.summary || 'Report filed.'
        break
      }
      case 'guard_block':
      case 'error':
        a.state = 'alert'
        a.line = String(e.details?.reason ?? e.details?.error ?? 'Blocked by a guardrail')
        break
    }
  }
  return out
}

/** Delegations whose target hasn't filed its report yet (drawn as live gold lines). */
export function liveDelegations(events: AgentEvent[]): { from: AgentName; to: AgentName }[] {
  const open: { from: AgentName; to: AgentName }[] = []
  for (const e of events) {
    if (e.event === 'delegation' && isAgent(e.agent) && e.to_agent && isAgent(e.to_agent)) {
      open.push({ from: e.agent, to: e.to_agent })
    }
    if (e.event === 'run_end' && isAgent(e.agent)) {
      const i = open.findIndex((d) => d.to === e.agent)
      if (i >= 0) open.splice(i, 1)
    }
  }
  return open
}

export function allDelegations(events: AgentEvent[]): { from: AgentName; to: AgentName }[] {
  return events
    .filter((e) => e.event === 'delegation' && isAgent(e.agent) && e.to_agent && isAgent(e.to_agent))
    .map((e) => ({ from: e.agent as AgentName, to: e.to_agent as AgentName }))
}
