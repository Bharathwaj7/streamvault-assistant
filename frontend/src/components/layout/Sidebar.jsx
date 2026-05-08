import { MessageSquare, BarChart2, ChevronRight } from 'lucide-react'
import { useChatStore } from '../../store/chatStore'

const SUGGESTED = [
  "Which titles performed best in 2025?",
  "Why is Stellar Run trending recently?",
  "Compare Dark Orbit vs Last Kingdom performance",
  "Which city had the strongest engagement in April 2025?",
  "What explains the weak comedy performance?",
  "What should leadership prioritise next quarter?",
  "How many total reviews and what is the average score?",
  "What does the content roadmap say about Stellar Universe?",
  "Show me the marketing spend breakdown by channel",
]

export default function Sidebar({ activeTab, setActiveTab, onSendMessage }) {
  const { isLoading } = useChatStore()

  const sendSuggested = (question) => {
    if (isLoading) return
    onSendMessage(question)
  }

  return (
    <aside className="w-60 bg-gray-900 border-r border-gray-800 flex flex-col shrink-0">
      {/* Nav tabs */}
      <div className="p-3 space-y-1">
        {[
          { id: 'chat',      icon: MessageSquare, label: 'Chat Assistant' },
          { id: 'dashboard', icon: BarChart2,     label: 'Dashboard'      },
        ].map(({ id, icon: Icon, label }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
              activeTab === id
                ? 'bg-blue-600 text-white'
                : 'text-gray-400 hover:bg-gray-800 hover:text-white'
            }`}
          >
            <Icon size={15} />
            {label}
          </button>
        ))}
      </div>

      <div className="border-t border-gray-800 mt-2 pt-4 px-3 flex-1 overflow-y-auto">
        <p className="text-gray-500 text-xs font-medium uppercase tracking-wider mb-2 px-1">
          Suggested Questions
        </p>
        <div className="space-y-1">
          {SUGGESTED.map((q) => (
            <button
              key={q}
              onClick={() => sendSuggested(q)}
              className="w-full text-left px-3 py-2.5 rounded-lg text-xs text-gray-300
                         hover:bg-gray-800 hover:text-white transition-colors
                         flex items-start gap-2 group"
            >
              <ChevronRight size={12} className="mt-0.5 text-gray-600 group-hover:text-blue-400 shrink-0" />
              <span>{q}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="p-3 border-t border-gray-800">
        <p className="text-gray-600 text-xs text-center">
          Data: SQL · PDF · CSV
        </p>
      </div>
    </aside>
  )
}