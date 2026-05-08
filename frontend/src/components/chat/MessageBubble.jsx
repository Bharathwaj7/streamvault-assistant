import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import SourceBadge from './SourceBadge'
import ToolTrace from './ToolTrace'
import { Bot, User, ThumbsUp, ThumbsDown, CheckCircle, Copy, Check } from 'lucide-react'
import { feedbackAPI } from '../../api/client'

// ── Confidence badge — only shown for high and medium ─────────────────────────
const CONFIDENCE_STYLES = {
  high:   { badge: 'bg-emerald-900/60 text-emerald-300 border border-emerald-700/50', dot: 'bg-emerald-400' },
  medium: { badge: 'bg-yellow-900/60 text-yellow-300 border border-yellow-700/50',   dot: 'bg-yellow-400' },
}

function ConfidenceBadge({ confidence }) {
  if (!confidence || confidence === 'low') return null
  const style = CONFIDENCE_STYLES[confidence]
  if (!style) return null
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${style.badge}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
      {confidence} confidence
    </span>
  )
}

// ── Escalation badge ──────────────────────────────────────────────────────────
function EscalationBadge({ level }) {
  if (!level || level === 'low') return null
  const isHigh = level === 'high'
  return (
    <div className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs
                     border-l-2 bg-gray-800/80
                     ${isHigh
                       ? 'border-red-500 text-red-300'
                       : 'border-orange-500 text-orange-300'
                     }`}>
      <span>⚠</span>
      <span>This answer required {level} sensitivity data</span>
    </div>
  )
}

// ── Copy button ───────────────────────────────────────────────────────────────
function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Clipboard API unavailable — fail silently
    }
  }

  return (
    <button
      onClick={handleCopy}
      className="p-1.5 rounded-lg text-gray-600 hover:text-gray-300
                 hover:bg-gray-700/50 transition-all"
      title="Copy to clipboard"
    >
      {copied
        ? <Check size={12} className="text-emerald-400" />
        : <Copy  size={12} />
      }
    </button>
  )
}

// ── Follow-up chips ───────────────────────────────────────────────────────────
function FollowUpChips({ followUps, onAsk }) {
  if (!followUps?.length) return null
  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {followUps.map((q, i) => (
        <button
          key={i}
          onClick={() => onAsk(q)}
          className="text-xs text-blue-300 bg-blue-900/30 border border-blue-700/40
                     hover:bg-blue-800/40 hover:border-blue-600/60 rounded-lg px-2.5 py-1.5
                     transition-all text-left"
        >
          {q}
        </button>
      ))}
    </div>
  )
}

// ── Feedback buttons ──────────────────────────────────────────────────────────
function FeedbackButtons({ message }) {
  const [voted,   setVoted]   = useState(null)
  const [loading, setLoading] = useState(false)

  const handleVote = async (rating) => {
    if (voted || loading) return
    setLoading(true)
    try {
      await feedbackAPI.submit(
        message.queryId || 'unknown',
        rating,
        {
          tools_used:  message.sources    || [],
          confidence:  message.confidence || '',
          model_used:  message.model      || '',
          iterations:  message.toolTraces?.length || 0,
        }
      )
      setVoted(rating)
    } catch (e) {
      console.error('Feedback failed:', e)
    } finally {
      setLoading(false)
    }
  }

  if (voted) {
    return (
      <div className="flex items-center gap-1.5 px-1">
        <CheckCircle size={12} className="text-emerald-400" />
        <span className="text-xs text-emerald-400">Thanks for your feedback</span>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-1 px-1">
      <span className="text-gray-600 text-xs mr-1">Helpful?</span>
      <button
        onClick={() => handleVote('positive')}
        disabled={loading}
        className="p-1.5 rounded-lg text-gray-500 hover:text-emerald-400
                   hover:bg-emerald-900/30 transition-all disabled:opacity-50"
        title="Helpful"
      >
        <ThumbsUp size={13} />
      </button>
      <button
        onClick={() => handleVote('negative')}
        disabled={loading}
        className="p-1.5 rounded-lg text-gray-500 hover:text-red-400
                   hover:bg-red-900/30 transition-all disabled:opacity-50"
        title="Not helpful"
      >
        <ThumbsDown size={13} />
      </button>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────
export default function MessageBubble({ message, onFollowUp }) {
  const isUser    = message.role === 'user'
  const [hovered, setHovered] = useState(false)

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>

      {/* Avatar */}
      <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5
        ${isUser ? 'bg-blue-600' : 'bg-gray-700'}`}>
        {isUser
          ? <User size={14} className="text-white" />
          : <Bot  size={14} className="text-blue-300" />
        }
      </div>

      {/* Bubble */}
      <div className={`max-w-[78%] flex flex-col gap-1
        ${isUser ? 'items-end' : 'items-start'}`}>

        {/* Message content with hover copy button */}
        <div
          className="relative w-full"
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
        >
          <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed
            ${isUser
              ? 'bg-blue-600 text-white rounded-tr-sm'
              : 'bg-gray-800 text-gray-100 rounded-tl-sm'
            }`}>
            {isUser ? (
              <p>{message.content}</p>
            ) : (
              <ReactMarkdown
                components={{
                  p:      ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                  ul:     ({ children }) => <ul className="list-disc list-inside space-y-1 mb-2">{children}</ul>,
                  ol:     ({ children }) => <ol className="list-decimal list-inside space-y-1 mb-2">{children}</ol>,
                  li:     ({ children }) => <li className="text-gray-200">{children}</li>,
                  strong: ({ children }) => <strong className="text-white font-semibold">{children}</strong>,
                  code:   ({ children }) => <code className="bg-gray-900 px-1.5 py-0.5 rounded text-blue-300 text-xs font-mono">{children}</code>,
                }}
              >
                {message.content}
              </ReactMarkdown>
            )}
          </div>

          {/* Copy button — assistant messages only, shown on hover */}
          {!isUser && hovered && (
            <div className="absolute top-2 right-2">
              <CopyButton text={message.content} />
            </div>
          )}
        </div>

        {/* Sources */}
        {message.sources?.length > 0 && (
          <div className="flex flex-wrap gap-1 px-1">
            {message.sources.map((s) => <SourceBadge key={s} source={s} />)}
          </div>
        )}

        {/* Confidence badge — only visible for high/medium */}
        {!isUser && message.confidence && (
          <div className="px-1">
            <ConfidenceBadge confidence={message.confidence} />
          </div>
        )}

        {/* Escalation badge */}
        {!isUser && message.escalationLevel && (
          <div className="px-1">
            <EscalationBadge level={message.escalationLevel} />
          </div>
        )}

        {/* Feedback buttons */}
        {!isUser && (
          <FeedbackButtons message={message} />
        )}

        {/* Tool Trace */}
        {message.toolTraces?.length > 0 && (
          <div className="w-full px-1">
            <ToolTrace traces={message.toolTraces} />
          </div>
        )}

        {/* Follow-up chips */}
        {!isUser && message.followUps?.length > 0 && (
          <div className="px-1 w-full">
            <FollowUpChips
              followUps={message.followUps}
              onAsk={onFollowUp}
            />
          </div>
        )}

        {/* Timestamp */}
        <span className="text-gray-600 text-[10px] px-1">
          {new Date(message.timestamp).toLocaleTimeString([], {
            hour: '2-digit', minute: '2-digit'
          })}
        </span>
      </div>
    </div>
  )
}