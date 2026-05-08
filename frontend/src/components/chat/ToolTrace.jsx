import { useState } from 'react'
import { ChevronDown, ChevronRight, Zap } from 'lucide-react'

const TOOL_COLORS = {
  query_database:   'text-emerald-400',
  search_documents: 'text-amber-400',
  analyze_csv_data: 'text-blue-400',
}

const TOOL_LABELS = {
  query_database:   'SQL Query',
  search_documents: 'PDF Search',
  analyze_csv_data: 'CSV Analysis',
}

const EVENT_STYLES = {
  tool_call:       { color: 'text-emerald-400', bg: 'bg-emerald-900/20', icon: '🔧' },
  rag_retrieval:   { color: 'text-amber-400',   bg: 'bg-amber-900/20',   icon: '📄' },
  rag_escalation:  { color: 'text-orange-400',  bg: 'bg-orange-900/20',  icon: '⬆' },
  retry:           { color: 'text-red-400',     bg: 'bg-red-900/20',     icon: '🔄' },
  cap_hit:         { color: 'text-yellow-400',  bg: 'bg-yellow-900/20',  icon: '⚠' },
  sub_query_start: { color: 'text-blue-400',    bg: 'bg-blue-900/20',    icon: '🔀' },
  sub_query_done:  { color: 'text-blue-300',    bg: 'bg-blue-900/20',    icon: '✓'  },
  decomposing:     { color: 'text-purple-400',  bg: 'bg-purple-900/20',  icon: '✂'  },
  synthesizing:    { color: 'text-purple-400',  bg: 'bg-purple-900/20',  icon: '🔗' },
  default:         { color: 'text-gray-400',    bg: 'bg-gray-800',       icon: '•'  },
}

function formatEvent(event) {
  switch (event.type) {
    case 'tool_call':
      return `Called ${event.tool_name}${
        event.latency_ms ? ` (${event.latency_ms}ms)` : ''
      }${event.outputs_summary === 'served from cache' ? ' — cached' : ''}`
    case 'rag_retrieval':
      return `Searched documents [${event.sensitivity_level}] — ${event.chunks_found} chunks found`
    case 'rag_escalation':
      return `Escalated sensitivity: ${event.from_level} → ${event.to_level}`
    case 'retry':
      return `Retrying (attempt ${event.attempt}) — ${event.error}`
    case 'cap_hit':
      return `Reached max iterations — partial answer`
    case 'sub_query_start':
      return `Part ${event.index}/${event.total}: ${event.query}`
    case 'sub_query_done':
      return `Part ${event.index} complete — ${event.sources?.join(', ')}`
    case 'decomposing':
      return event.message || 'Decomposing question...'
    case 'synthesizing':
      return event.message || 'Synthesizing answers...'
    default:
      return event.type
  }
}

export default function ToolTrace({ traces = [], liveEvents = [] }) {
  const [open, setOpen] = useState(false)

  const hasLive = liveEvents.length > 0

  // Filter to displayable live events
  const liveItems = liveEvents.filter(e =>
    ['tool_call', 'rag_retrieval', 'rag_escalation', 'retry',
     'cap_hit', 'sub_query_start', 'sub_query_done',
     'decomposing', 'synthesizing'].includes(e.type)
  )

  const totalCalls = traces.length ||
    liveItems.filter(e => e.type === 'tool_call').length

  // Build collapsed label
  const toolNames = hasLive
    ? [...new Set(liveItems.filter(e => e.type === 'tool_call').map(e => e.tool_name))]
    : [...new Set(traces.map(t => t.tool_name))]

  const collapseLabel = toolNames
    .map(n => TOOL_LABELS[n] || n)
    .join(' → ')

  const displayItems = hasLive ? liveItems : []

  if (!hasLive && !traces?.length) return null

  return (
    <div className="mt-2 border border-gray-700 rounded-lg overflow-hidden">

      {/* Header */}
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-3 py-2 bg-gray-800/60
                   hover:bg-gray-800 text-xs text-gray-400 transition-colors"
      >
        <Zap size={11} className="text-yellow-500" />
        <span>{totalCalls} tool call{totalCalls !== 1 ? 's' : ''}</span>
        {collapseLabel && (
          <span className="text-gray-600">· {collapseLabel}</span>
        )}
        <span className="ml-auto">
          {open
            ? <ChevronDown  size={12} />
            : <ChevronRight size={12} />
          }
        </span>
      </button>

      {open && (
        <div className="divide-y divide-gray-800">

          {/* Live event timeline */}
          {hasLive && displayItems.map((event, i) => {
            const style = EVENT_STYLES[event.type] || EVENT_STYLES.default
            return (
              <div
                key={i}
                className={`flex items-start gap-2 px-3 py-2 text-xs
                            border-b border-gray-700/30 last:border-0 ${style.bg}`}
              >
                <span className="shrink-0 mt-0.5">{style.icon}</span>
                <span className={style.color}>{formatEvent(event)}</span>
                {event.type === 'tool_call' && event.latency_ms > 0 && (
                  <span className="ml-auto text-gray-600 shrink-0">
                    {event.latency_ms}ms
                  </span>
                )}
              </div>
            )
          })}

          {/* Static trace details (after response) */}
          {!hasLive && traces.map((trace, i) => (
            <div key={i} className="px-3 py-2.5 bg-gray-900/40 text-xs">
              <div className="flex items-center gap-2 mb-1.5">
                <span className={`font-mono font-semibold ${
                  TOOL_COLORS[trace.tool_name] || 'text-gray-300'
                }`}>
                  {TOOL_LABELS[trace.tool_name] || trace.tool_name}
                </span>
                <span className="text-gray-600">{trace.duration_ms}ms</span>
              </div>
              <div className="font-mono text-gray-500 text-[10px] bg-gray-950/60
                              rounded p-2 mb-1.5 overflow-x-auto">
                {JSON.stringify(trace.arguments, null, 2)}
              </div>
              <div className="font-mono text-gray-600 text-[10px] bg-gray-950/60
                              rounded p-2 overflow-x-auto max-h-28">
                {typeof trace.result === 'object'
                  ? JSON.stringify(trace.result, null, 2).slice(0, 500)
                  : String(trace.result).slice(0, 300)}
                {JSON.stringify(trace.result).length > 500 ? '…' : ''}
              </div>
            </div>
          ))}

        </div>
      )}
    </div>
  )
}