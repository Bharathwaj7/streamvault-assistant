import { create } from 'zustand'

const STORAGE_KEY = 'sv_chat_messages'

function loadMessages() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    return saved ? JSON.parse(saved) : []
  } catch {
    return []
  }
}

function saveMessages(messages) {
  try {
    // Strip large tool results before saving to avoid localStorage size limits
    const toSave = messages.map(m => ({
      ...m,
      toolTraces: (m.toolTraces || []).map(t => ({
        tool_name:   t.tool_name,
        arguments:   t.arguments,
        duration_ms: t.duration_ms,
        result:      null,  // ← don't persist large results to localStorage
      })),
    }))
    localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave))
  } catch {
    // Storage full or unavailable — fail silently
  }
}

export const useChatStore = create((set, get) => ({
  messages:  loadMessages(),
  isLoading: false,
  error:     null,

  addMessage: (role, content, sources = [], toolTraces = [], extras = {}) =>
    set((state) => {
      const updated = [...state.messages, {
        id:              Date.now(),
        role,
        content:         content || '',   // ← ensure never undefined
        sources,
        toolTraces,
        queryId:         extras.queryId         || null,
        confidence:      extras.confidence      || null,
        followUps:       extras.followUps       || [],
        model:           extras.model           || null,
        escalationLevel: extras.escalationLevel || null,
        timestamp:       new Date().toISOString(),
      }]
      saveMessages(updated)
      return { messages: updated }
    }),

  setLoading: (isLoading) => set({ isLoading }),
  setError:   (error)     => set({ error }),

  clearChat: () => {
    localStorage.removeItem(STORAGE_KEY)
    set({ messages: [], error: null })
  },

  clearHistory: () => {
    localStorage.removeItem(STORAGE_KEY)
    set({ messages: [], error: null })
  },

  getHistory: () => {
    const msgs = get().messages
    return msgs.slice(-20).map((m) => ({
      role:    m.role,
      content: m.content,
    }))
  },
}))

export const useAuthStore = create((set) => ({
  token: localStorage.getItem('sv_token') || null,
  user:  JSON.parse(localStorage.getItem('sv_user') || 'null'),

  login: (token, user) => {
    localStorage.setItem('sv_token', token)
    localStorage.setItem('sv_user', JSON.stringify(user))
    set({ token, user })
  },

  logout: () => {
    localStorage.removeItem('sv_token')
    localStorage.removeItem('sv_user')
    localStorage.removeItem(STORAGE_KEY)
    set({ token: null, user: null })
  },
}))