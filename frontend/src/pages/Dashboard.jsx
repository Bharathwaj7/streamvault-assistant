import { useState, useCallback, useRef } from 'react'
import Header from '../components/layout/Header'
import Sidebar from '../components/layout/Sidebar'
import ChatWindow from '../components/chat/ChatWindow'
import InsightsPanel from '../components/insights/InsightsPanel'
import { useChatStore } from '../store/chatStore'
import { chatAPI } from '../api/client'

export default function Dashboard() {
  const [activeTab,   setActiveTab]   = useState('chat')
  const [liveEvents,  setLiveEvents]  = useState([])
  const [isStreaming, setIsStreaming] = useState(false)

  const {
    addMessage, setLoading, setError, getHistory,
  } = useChatStore()

  const isLoadingRef = useRef(false)

  const handleSend = useCallback(async (text) => {
    if (isLoadingRef.current) return

    setActiveTab('chat')
    isLoadingRef.current = true

    addMessage('user', text)
    setLoading(true)
    setError(null)
    setLiveEvents([])
    setIsStreaming(true)

    const capturedEvents = []

    try {
      const history    = getHistory()
      let   finalEvent = null

      for await (const event of chatAPI.stream(text, history)) {
        if (event.type === 'response') {
          finalEvent = event
          break
        }
        capturedEvents.push(event)
        setLiveEvents([...capturedEvents])
      }

      if (finalEvent) {
        addMessage(
          'assistant',
          finalEvent.answer || '',
          finalEvent.sources || [],
          (finalEvent.tool_traces || []).map(t => ({
            tool_name:   t.tool_name   || '',
            arguments:   t.arguments  || {},
            result:      t.result     || {},
            duration_ms: t.duration_ms || 0,
          })),
          {
            queryId:         finalEvent.query_id         || '',
            confidence:      finalEvent.confidence       || 'low',
            followUps:       finalEvent.follow_ups       || [],
            model:           'llama-3.3-70b-versatile',
            escalationLevel: finalEvent.escalation_level || null,
          }
        )
      } else {
        addMessage(
          'assistant',
          'No response received. Please try again.',
          [], []
        )
      }
    } catch (e) {
      const msg = e.message || 'Something went wrong. Please try again.'
      setError(msg)
      addMessage('assistant', `⚠️ ${msg}`, [], [])
    } finally {
      setLoading(false)
      setIsStreaming(false)
      setLiveEvents([])
      isLoadingRef.current = false
    }
  }, [addMessage, setLoading, setError, getHistory])

  return (
    <div className="h-screen flex flex-col bg-gray-950 text-gray-100 overflow-hidden">
      <Header />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          onSendMessage={handleSend}
        />

        <main className="flex-1 flex overflow-hidden">
          {activeTab === 'chat' ? (
            <>
              <div className="flex-1 flex flex-col overflow-hidden border-r border-gray-800 min-w-0">
                <ChatWindow
                  onSendMessage={handleSend}
                  liveEvents={liveEvents}
                  isStreaming={isStreaming}
                />
              </div>

              <div className="w-80 shrink-0 overflow-hidden bg-gray-900/50">
                <div className="h-full">
                  <div className="px-4 py-3 border-b border-gray-800">
                    <h2 className="text-sm font-semibold text-gray-300">Live Insights</h2>
                    <p className="text-xs text-gray-600 mt-0.5">Real-time from all data sources</p>
                  </div>
                  <div className="h-[calc(100%-57px)]">
                    <InsightsPanel />
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 overflow-y-auto bg-gray-950 p-6">
              <div className="max-w-6xl mx-auto">
                <h1 className="text-xl font-bold text-white mb-1">Analytics Dashboard</h1>
                <p className="text-gray-500 text-sm mb-6">StreamVault Entertainment · Q1 2025 Overview</p>
                <InsightsPanel />
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}