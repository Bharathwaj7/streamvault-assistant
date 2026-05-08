import { useAuthStore } from './store/chatStore'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'

export default function App() {
  const { token } = useAuthStore()
  return token ? <Dashboard /> : <Login />
}
