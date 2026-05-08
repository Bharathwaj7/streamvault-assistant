import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-gray-300 font-medium mb-1">{label}</p>
      <p className="text-purple-300">Engagement: <span className="text-white">{payload[0]?.value?.toFixed(1)}</span></p>
      {payload[0]?.payload?.views && (
        <p className="text-gray-400">Views: <span className="text-white">{payload[0].payload.views?.toLocaleString()}</span></p>
      )}
    </div>
  )
}

const getColor = (score) => {
  if (score >= 88) return '#6366f1'
  if (score >= 80) return '#3b82f6'
  if (score >= 72) return '#0ea5e9'
  return '#67e8f9'
}

export default function RegionalHeatmap({ data = [] }) {
  const maxCityLen = Math.max(...data.map(d => (d.city || '').length), 8)
  const yAxisWidth = Math.min(Math.max(maxCityLen * 7, 80), 120)
  const chartHeight = Math.max(data.length * 28, 220)  // 28px per city row

  return (
    <ResponsiveContainer width="100%" height={chartHeight}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 0, right: 24, left: 4, bottom: 0 }}
      >
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="#1f2937"
          horizontal={false}
        />
        <XAxis
          type="number"
          domain={[60, 100]}
          tick={{ fill: '#6b7280', fontSize: 10 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="city"
          tick={{ fill: '#d1d5db', fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          width={yAxisWidth}
        />
        <Tooltip
          content={<CustomTooltip />}
          cursor={{ fill: 'rgba(99,102,241,0.08)' }}
        />
        <Bar dataKey="engagement" radius={[0, 4, 4, 0]} barSize={16}>
          {data.map((d, i) => (
            <Cell key={i} fill={getColor(d.engagement)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}