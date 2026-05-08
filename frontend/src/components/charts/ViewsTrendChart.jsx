import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-gray-400 mb-1">{label}</p>
      <p className="text-blue-300">Views: <span className="text-white font-medium">{payload[0]?.value?.toLocaleString()}</span></p>
    </div>
  )
}

export default function ViewsTrendChart({ data = [] }) {
  // Find the Stellar Run surge month (biggest jump)
  const maxIdx = data.reduce((mi, d, i) => d.views > (data[mi]?.views || 0) ? i : mi, 0)
  const surgeMonth = data[maxIdx]?.month

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data} margin={{ top: 4, right: 8, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
        <XAxis dataKey="month" tick={{ fill: '#9ca3af', fontSize: 10 }} axisLine={false}
               tickLine={false} tickFormatter={(v) => v?.slice(5)} />
        <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false}
               tickFormatter={(v) => `${(v/1000).toFixed(0)}k`} />
        <Tooltip content={<CustomTooltip />} />
        {surgeMonth && (
          <ReferenceLine x={surgeMonth} stroke="#f59e0b" strokeDasharray="4 2"
                         label={{ value: 'Surge', fill: '#f59e0b', fontSize: 10, position: 'top' }} />
        )}
        <Line type="monotone" dataKey="views" stroke="#3b82f6" strokeWidth={2}
              dot={{ fill: '#3b82f6', r: 3 }} activeDot={{ r: 5, fill: '#60a5fa' }} />
      </LineChart>
    </ResponsiveContainer>
  )
}
