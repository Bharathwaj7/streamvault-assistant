import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

const TREND_ICON = {
  up:      <TrendingUp  size={12} className="text-emerald-400" />,
  down:    <TrendingDown size={12} className="text-red-400" />,
  neutral: <Minus       size={12} className="text-gray-500" />,
}

export default function KPICard({ label, value, change, trend = 'neutral' }) {
  const formattedChange = change && !change.includes('%')
    ? `${change}%`
    : change

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
      <p className="text-gray-500 text-xs mb-1.5">{label}</p>
      <p className="text-white text-2xl font-bold leading-none mb-2">{value}</p>
      {formattedChange && (
        <div className="flex items-center gap-1">
          {TREND_ICON[trend]}
          <span className={`text-xs ${
            trend === 'up'   ? 'text-emerald-400' :
            trend === 'down' ? 'text-red-400'     : 'text-gray-500'
          }`}>
            {formattedChange}
          </span>
        </div>
      )}
    </div>
  )
}