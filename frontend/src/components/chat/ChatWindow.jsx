import { useEffect, useRef } from 'react'
import { useChatStore } from '../../store/chatStore'
import MessageBubble from './MessageBubble'
import ChatInput from './ChatInput'
import ToolTrace from './ToolTrace'
import { Bot, Trash2, PlusCircle } from 'lucide-react'

export default function ChatWindow({ onSendMessage, liveEvents = [], isStreaming = false }) {
  const {
    messages, isLoading,
    clearChat, clearHistory,
  } = useChatStore()

  const bottomRef = useRef(null)

  const lastModel = messages
    .filter(m => m.role === 'assistant' && m.model)
    .at(-1)?.model || 'llama-3.3-70b'

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading, liveEvents])

  const handleFollowUp = (text) => {
    if (onSendMessage) onSendMessage(text)
  }

  return (
    <div className="flex flex-col h-full">

      {/* Chat header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-800 shrink-0">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full animate-pulse ${
            isStreaming ? 'bg-blue-400' : 'bg-green-400'
          }`} />
          <span className="text-sm text-gray-300 font-medium">Analytics Assistant</span>
          <span className="text-xs text-gray-600">· {lastModel}</span>
        </div>

        {messages.length > 0 && (
          <div className="flex items-center gap-3">
            <button
              onClick={clearHistory}
              className="flex items-center gap-1.5 text-xs text-blue-400
                         hover:text-blue-300 transition-colors"
              title="New chat"
            >
              <PlusCircle size={12} /> New Chat
            </button>
            <button
              onClick={clearChat}
              className="flex items-center gap-1.5 text-xs text-gray-500
                         hover:text-gray-300 transition-colors"
              title="Clear chat"
            >
              <Trash2 size={12} /> Clear
            </button>
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">

        {/* Empty state */}
        {messages.length === 0 && !isStreaming && (
          <div className="flex flex-col items-center justify-center h-full text-center gap-4 pb-10">
            <div className="w-14 h-14 bg-gray-800 rounded-2xl flex items-center justify-center">
              <Bot size={28} className="text-blue-400" />
            </div>
            <div>
              <p className="text-gray-300 font-medium mb-1">Ask anything about StreamVault</p>
              <p className="text-gray-500 text-sm max-w-xs">
                I can query the database, search internal reports, and analyse
                CSV data to answer your business questions.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2 w-full max-w-sm mt-2">
              {[
                "Which titles performed best in 2025?",
                "Why is Stellar Run trending?",
                "What explains weak comedy performance?",
                "Top cities by engagement?",
              ].map((q) => (
                <button
                  key={q}
                  onClick={() => handleFollowUp(q)}
                  className="text-xs text-gray-400 bg-gray-800 hover:bg-gray-700
                             border border-gray-700 rounded-xl px-3 py-2.5 text-left
                             hover:text-gray-200 hover:border-gray-600 transition-all"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Message list */}
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            onFollowUp={handleFollowUp}
          />
        ))}

        {/* Live streaming indicator */}
        {isStreaming && (
          <div className="flex gap-3">
            <div className="w-7 h-7 rounded-full bg-gray-700 flex items-center
                            justify-center shrink-0 mt-0.5">
              <Bot size={14} className="text-blue-300" />
            </div>
            <div className="flex-1 space-y-2">

              {/* Live events timeline */}
              {liveEvents.length > 0 && (
                <ToolTrace liveEvents={liveEvents} traces={[]} />
              )}

              {/* Typing dots */}
              <div className="bg-gray-800 rounded-2xl rounded-tl-sm px-4 py-3 inline-block">
                <div className="flex gap-1.5 items-center h-4">
                  {[0, 1, 2].map((i) => (
                    <div
                      key={i}
                      className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce"
                      style={{ animationDelay: `${i * 150}ms` }}
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <ChatInput onSend={handleFollowUp} isLoading={isLoading} />
    </div>
  )
}