import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-gray-300 font-medium mb-1">{label}</p>
      <p className="text-amber-300">Spend: <span className="text-white">${(d?.spend/1_000_000)?.toFixed(1)}M</span></p>
      <p className="text-emerald-300">Conversions: <span className="text-white">{d?.conversions?.toLocaleString()}</span></p>
      {d?.cpa && <p className="text-blue-300">CPA: <span className="text-white">${d.cpa}</span></p>}
    </div>
  )
}

const CHANNEL_COLORS = {
  'Social Media': '#f59e0b',
  'Influencer':   '#a78bfa',
  'TV Ads':       '#60a5fa',
  'Search Ads':   '#34d399',
  'Email':        '#fb7185',
  'Billboards':   '#94a3b8',
}

export default function MarketingROAS({ data = [] }) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
        <XAxis dataKey="channel" tick={{ fill: '#9ca3af', fontSize: 9 }} axisLine={false}
               tickLine={false} interval={0} />
        <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false}
               tickFormatter={(v) => `$${(v/1_000_000).toFixed(0)}M`} />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(245,158,11,0.08)' }} />
        <Bar dataKey="spend" radius={[4, 4, 0, 0]}>
          {data.map((d, i) => (
            <Cell key={i} fill={CHANNEL_COLORS[d.channel] || '#6b7280'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
