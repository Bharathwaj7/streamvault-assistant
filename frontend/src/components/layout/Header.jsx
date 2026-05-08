import { LogOut, Activity } from 'lucide-react'
import { useAuthStore } from '../../store/chatStore'

export default function Header() {
  const { user, logout } = useAuthStore()

  return (
    <header className="h-14 bg-gray-900 border-b border-gray-700 flex items-center px-6 justify-between shrink-0">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
          <Activity size={16} className="text-white" />
        </div>
        <span className="text-white font-semibold text-sm tracking-wide">
          StreamVault Analytics
        </span>
        <span className="text-blue-400 text-xs bg-blue-900/40 px-2 py-0.5 rounded-full">
          Internal
        </span>
      </div>

      <div className="flex items-center gap-4">
        <span className="text-gray-300 text-xs">
          {user?.username} · <span className="capitalize">{user?.role}</span>
        </span>
        <button
          onClick={logout}
          className="text-gray-400 hover:text-white flex items-center gap-1.5 text-xs transition-colors"
        >
          <LogOut size={13} />
          Sign out
        </button>
      </div>
    </header>
  )
}