import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

// Attach JWT on every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('sv_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Auto-logout on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('sv_token')
      localStorage.removeItem('sv_user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export const authAPI = {
  login: (username, password) =>
    api.post('/auth/token', { username, password }),
}

// SSE-based chat — returns async generator of events
export const chatAPI = {
  stream: async function* (message, history) {
    const token    = localStorage.getItem('sv_token')
    const response = await fetch('/api/chat', {
      method:  'POST',
      headers: {
        'Content-Type':  'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ message, history }),
    })

    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.detail || 'Chat request failed')
    }

    const reader  = response.body.getReader()
    const decoder = new TextDecoder()
    let   buffer  = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() // keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.slice(6))
            yield event
          } catch {
            // skip malformed line
          }
        }
      }
    }
  },
}

// Analytics API — supports period and genre filters
export const analyticsAPI = {
  getInsights: (params = {}) => api.get('/analytics/insights', { params }),
}

export const ingestAPI = {
  run: () => api.post('/ingest'),
}

export const feedbackAPI = {
  submit: (queryId, rating, context) =>
    api.post('/feedback', {
      query_id: queryId,
      rating,
      context,
    }),
}

export default api