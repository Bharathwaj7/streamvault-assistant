import { useState } from 'react'
import { Send, Loader2 } from 'lucide-react'

export default function ChatInput({ onSend, isLoading }) {
  const [text, setText] = useState('')

  const handleSend = () => {
    const trimmed = text.trim()
    if (!trimmed || isLoading) return
    onSend(trimmed)
    setText('')
  }

  return (
    <div className="border-t border-gray-800 p-4 bg-gray-900">
      <div className="flex gap-3 items-end">
        <textarea
          className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-4 py-3
                     text-sm text-gray-100 placeholder-gray-500 resize-none
                     focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500
                     transition-colors min-h-[44px] max-h-32"
          placeholder="Ask a business question…"
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSend()
            }
          }}
          disabled={isLoading}
        />
        <button
          onClick={handleSend}
          disabled={isLoading || !text.trim()}
          className="w-10 h-10 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700
                     disabled:cursor-not-allowed rounded-xl flex items-center justify-center
                     transition-colors shrink-0"
        >
          {isLoading
            ? <Loader2 size={16} className="text-white animate-spin" />
            : <Send size={16} className="text-white" />
          }
        </button>
      </div>
      <p className="text-gray-600 text-[10px] mt-2 text-center">
        Shift+Enter for new line · Sources cited automatically
      </p>
    </div>
  )
}
