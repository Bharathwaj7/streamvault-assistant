import { useState } from 'react'
import { useAuthStore } from '../store/chatStore'
import { authAPI } from '../api/client'
import { Activity, Eye, EyeOff, Loader2 } from 'lucide-react'

export default function Login() {
  const { login }              = useAuthStore()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPw,   setShowPw]   = useState(false)
  const [error,    setError]    = useState('')
  const [loading,  setLoading]  = useState(false)

  const handleLogin = async (e) => {
    e.preventDefault()
    if (!username || !password) return
    setLoading(true)
    setError('')
    try {
      const res = await authAPI.login(username, password)
      const { access_token, username: user, role } = res.data
      login(access_token, { username: user, role })
    } catch (e) {
      setError(e.response?.data?.detail || 'Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">

        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-14 h-14 bg-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Activity size={28} className="text-white" />
          </div>
          <h1 className="text-white text-xl font-bold">StreamVault</h1>
          <p className="text-gray-500 text-sm mt-1">Analytics Assistant · Internal</p>
        </div>

        {/* Card */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
          <h2 className="text-gray-200 font-semibold mb-5">Sign in</h2>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="text-gray-400 text-xs mb-1.5 block">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="admin"
                className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5
                           text-sm text-gray-100 placeholder-gray-600
                           focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500
                           transition-colors"
              />
            </div>

            <div>
              <label className="text-gray-400 text-xs mb-1.5 block">Password</label>
              <div className="relative">
                <input
                  type={showPw ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 pr-10
                             text-sm text-gray-100 placeholder-gray-600
                             focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500
                             transition-colors"
                />
                <button type="button" onClick={() => setShowPw(!showPw)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300">
                  {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {error && (
              <p className="text-red-400 text-xs bg-red-950/40 border border-red-900/50 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading || !username || !password}
              className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700
                         disabled:cursor-not-allowed text-white font-medium py-2.5 rounded-xl
                         text-sm transition-colors flex items-center justify-center gap-2"
            >
              {loading && <Loader2 size={14} className="animate-spin" />}
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <div className="mt-5 pt-4 border-t border-gray-800">
            <p className="text-gray-600 text-xs text-center mb-2">Demo credentials</p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="bg-gray-800/60 rounded-lg p-2 text-center">
                <p className="text-gray-400 font-mono">admin</p>
                <p className="text-gray-600 font-mono">streamvault2025</p>
              </div>
              <div className="bg-gray-800/60 rounded-lg p-2 text-center">
                <p className="text-gray-400 font-mono">analyst</p>
                <p className="text-gray-600 font-mono">analyst123</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
