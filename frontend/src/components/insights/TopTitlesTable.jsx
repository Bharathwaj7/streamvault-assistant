import { useState } from 'react'
import { ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react'

const GENRE_COLORS = {
  'Sci-Fi':   'bg-blue-900/60 text-blue-300',
  'Action':   'bg-red-900/60 text-red-300',
  'Drama':    'bg-purple-900/60 text-purple-300',
  'Thriller': 'bg-yellow-900/60 text-yellow-300',
  'Comedy':   'bg-green-900/60 text-green-300',
  'Romance':  'bg-pink-900/60 text-pink-300',
}

function SortIcon({ column, sortKey, sortDir }) {
  if (sortKey !== column) return <ChevronsUpDown size={10} className="text-gray-600 ml-1 inline" />
  return sortDir === 'asc'
    ? <ChevronUp   size={10} className="text-blue-400 ml-1 inline" />
    : <ChevronDown size={10} className="text-blue-400 ml-1 inline" />
}

export default function TopTitlesTable({ titles = [] }) {
  const [sortKey, setSortKey] = useState('views')
  const [sortDir, setSortDir] = useState('desc')

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  const sorted = [...titles].sort((a, b) => {
    const aVal = a[sortKey] ?? ''
    const bVal = b[sortKey] ?? ''
    if (typeof aVal === 'number' && typeof bVal === 'number') {
      return sortDir === 'asc' ? aVal - bVal : bVal - aVal
    }
    return sortDir === 'asc'
      ? String(aVal).localeCompare(String(bVal))
      : String(bVal).localeCompare(String(aVal))
  })

  const thClass = "text-left text-gray-500 font-medium py-2 pr-3 cursor-pointer hover:text-gray-300 select-none transition-colors"
  const thClassRight = "text-right text-gray-500 font-medium py-2 pr-3 cursor-pointer hover:text-gray-300 select-none transition-colors"

  return (
    <div className="overflow-hidden">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-gray-700">
            <th className="text-left text-gray-500 font-medium py-2 pr-3">#</th>
            <th className={thClass} onClick={() => handleSort('title')}>
              Title <SortIcon column="title" sortKey={sortKey} sortDir={sortDir} />
            </th>
            <th className={thClass} onClick={() => handleSort('genre')}>
              Genre <SortIcon column="genre" sortKey={sortKey} sortDir={sortDir} />
            </th>
            <th className={thClassRight} onClick={() => handleSort('views')}>
              Views <SortIcon column="views" sortKey={sortKey} sortDir={sortDir} />
            </th>
            <th className={thClassRight} onClick={() => handleSort('avg_completion')}>
              Completion <SortIcon column="avg_completion" sortKey={sortKey} sortDir={sortDir} />
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((t, i) => (
            <tr key={t.title} className="border-b border-gray-800/60 hover:bg-gray-800/30 transition-colors">
              <td className="py-2 pr-3 text-gray-600 font-mono">{i + 1}</td>
              <td className="py-2 pr-3 text-gray-200 font-medium max-w-[120px] truncate">{t.title}</td>
              <td className="py-2 pr-3">
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${GENRE_COLORS[t.genre] || 'bg-gray-700 text-gray-300'}`}>
                  {t.genre}
                </span>
              </td>
              <td className="py-2 pr-3 text-right text-gray-300 font-mono">
                {t.views?.toLocaleString()}
              </td>
              <td className="py-2 text-right text-gray-400 font-mono">
                {t.avg_completion?.toFixed(0)}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}