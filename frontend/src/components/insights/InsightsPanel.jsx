import { useEffect, useState, useCallback } from 'react'
import { analyticsAPI } from '../../api/client'
import KPICard from './KPICard'
import TopTitlesTable from './TopTitlesTable'
import GenreBarChart from '../charts/GenreBarChart'
import ViewsTrendChart from '../charts/ViewsTrendChart'
import RegionalHeatmap from '../charts/RegionalHeatmap'
import MarketingROAS from '../charts/MarketingROAS'
import { RefreshCw, AlertCircle, Filter } from 'lucide-react'

// ── Skeleton components ───────────────────────────────────────────────────────
function KPISkeleton() {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 animate-pulse">
      <div className="h-3 bg-gray-700 rounded w-2/3 mb-3" />
      <div className="h-7 bg-gray-700 rounded w-1/2 mb-3" />
      <div className="h-3 bg-gray-700 rounded w-1/3" />
    </div>
  )
}

function ChartSkeleton({ title }) {
  return (
    <div className="bg-gray-800/50 border border-gray-700/60 rounded-xl p-4">
      <div className="h-3 bg-gray-700 rounded w-1/3 mb-4 animate-pulse" />
      <div className="h-48 bg-gray-700/50 rounded-lg animate-pulse flex items-center justify-center">
        <div className="text-gray-600 text-xs">{title}</div>
      </div>
    </div>
  )
}

function TableSkeleton() {
  return (
    <div className="bg-gray-800/50 border border-gray-700/60 rounded-xl p-4 animate-pulse">
      <div className="h-3 bg-gray-700 rounded w-1/4 mb-4" />
      {[...Array(5)].map((_, i) => (
        <div key={i} className="flex gap-3 mb-3">
          <div className="h-3 bg-gray-700 rounded w-4" />
          <div className="h-3 bg-gray-700 rounded flex-1" />
          <div className="h-3 bg-gray-700 rounded w-12" />
          <div className="h-3 bg-gray-700 rounded w-10" />
        </div>
      ))}
    </div>
  )
}

// ── Section helpers ───────────────────────────────────────────────────────────
function SectionTitle({ children }) {
  return (
    <h3 className="text-gray-300 text-xs font-semibold uppercase tracking-wider mb-3">
      {children}
    </h3>
  )
}

function ChartCard({ title, children }) {
  return (
    <div className="bg-gray-800/50 border border-gray-700/60 rounded-xl p-4">
      <p className="text-gray-200 text-xs font-semibold mb-3">{title}</p>
      {children}
    </div>
  )
}

// ── Filter options ────────────────────────────────────────────────────────────
const PERIOD_OPTIONS = [
  { label: 'All Time', value: 'all' },
  { label: 'Last 30 Days', value: 'last30' },
  { label: 'Q1 2025', value: 'q1_2025' },
  { label: 'Q2 2025', value: 'q2_2025' },
  { label: 'Q3 2025', value: 'q3_2025' },
  { label: 'Q4 2025', value: 'q4_2025' },
]

const GENRE_OPTIONS = [
  { label: 'All Genres', value: 'all' },
  { label: 'Sci-Fi', value: 'Sci-Fi' },
  { label: 'Action', value: 'Action' },
  { label: 'Drama', value: 'Drama' },
  { label: 'Comedy', value: 'Comedy' },
  { label: 'Thriller', value: 'Thriller' },
  { label: 'Romance', value: 'Romance' },
]

export default function InsightsPanel() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [period, setPeriod] = useState('all')
  const [genre, setGenre] = useState('all')

  const fetchData = useCallback(async (selectedPeriod, selectedGenre) => {
    setLoading(true)
    setError(null)
    try {
      const params = {}
      if (selectedPeriod && selectedPeriod !== 'all') params.period = selectedPeriod
      if (selectedGenre && selectedGenre !== 'all') params.genre = selectedGenre
      const res = await analyticsAPI.getInsights(params)
      setData(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load insights')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData(period, genre)
  }, [period, genre, fetchData])

  const hasActiveFilters = period !== 'all' || genre !== 'all'

  // ── Filter bar ────────────────────────────────────────────────────────────
  const FilterBar = () => (
    <div className="border border-gray-700/60 rounded-xl p-3 bg-gray-800/30 mb-2">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5">
          <Filter size={11} className="text-gray-400" />
          <span className="text-gray-300 text-xs font-semibold uppercase tracking-wider">
            Filters
          </span>
          {hasActiveFilters && (
            <span className="bg-blue-600 text-white text-[9px] px-1.5 py-0.5 rounded-full">
              Active
            </span>
          )}
        </div>
        {hasActiveFilters && (
          <button
            onClick={() => { setPeriod('all'); setGenre('all') }}
            className="text-[10px] text-gray-400 hover:text-gray-200 transition-colors"
          >
            Reset
          </button>
        )}
      </div>

      {/* Side by side selectors */}
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-gray-400 text-[10px] uppercase tracking-wider block mb-1">
            Period
          </label>
          <select
            value={period}
            onChange={e => setPeriod(e.target.value)}
            className="w-full bg-gray-900 border border-gray-700 text-gray-200
                       text-xs rounded-lg px-2 py-1.5 focus:outline-none
                       focus:border-blue-500 transition-colors cursor-pointer"
          >
            {PERIOD_OPTIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-gray-400 text-[10px] uppercase tracking-wider block mb-1">
            Genre
          </label>
          <select
            value={genre}
            onChange={e => setGenre(e.target.value)}
            className="w-full bg-gray-900 border border-gray-700 text-gray-200
                       text-xs rounded-lg px-2 py-1.5 focus:outline-none
                       focus:border-blue-500 transition-colors cursor-pointer"
          >
            {GENRE_OPTIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Active filter badges */}
      {hasActiveFilters && (
        <div className="flex flex-wrap gap-1 mt-2">
          {period !== 'all' && (
            <span className="text-[10px] bg-blue-900/40 text-blue-300
                             border border-blue-700/40 px-2 py-0.5 rounded-full">
              {PERIOD_OPTIONS.find(o => o.value === period)?.label}
            </span>
          )}
          {genre !== 'all' && (
            <span className="text-[10px] bg-purple-900/40 text-purple-300
                             border border-purple-700/40 px-2 py-0.5 rounded-full">
              {genre}
            </span>
          )}
        </div>
      )}
    </div>
  )

  // ── Skeleton state ────────────────────────────────────────────────────────
  if (loading) return (
    <div className="overflow-y-auto h-full px-4 py-4 space-y-4">
      <FilterBar />
      <div className="grid grid-cols-2 gap-2">
        {[...Array(4)].map((_, i) => <KPISkeleton key={i} />)}
      </div>
      <TableSkeleton />
      <ChartSkeleton title="Loading trend data..." />
      <ChartSkeleton title="Loading regional data..." />
      <ChartSkeleton title="Loading genre data..." />
      <ChartSkeleton title="Loading marketing data..." />
    </div>
  )

  // ── Error state ───────────────────────────────────────────────────────────
  if (error) return (
    <div className="flex flex-col h-full p-4">
      <FilterBar />
      <div className="flex items-center justify-center flex-1">
        <div className="text-center">
          <AlertCircle size={20} className="text-red-400 mx-auto mb-2" />
          <p className="text-red-400 text-sm mb-3">{error}</p>
          <button
            onClick={() => fetchData(period, genre)}
            className="text-xs text-blue-400 hover:underline"
          >
            Retry
          </button>
        </div>
      </div>
    </div>
  )

  // ── Data state ────────────────────────────────────────────────────────────
  return (
    <div className="overflow-y-auto h-full px-4 py-4 space-y-4">

      {/* Filters */}
      <FilterBar />

      {/* KPIs */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <SectionTitle>Key Metrics</SectionTitle>
          <button
            onClick={() => fetchData(period, genre)}
            className="text-gray-500 hover:text-gray-300 transition-colors"
            title="Refresh"
          >
            <RefreshCw size={12} />
          </button>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {data?.kpis?.map((kpi) => (
            <KPICard key={kpi.label} {...kpi} />
          ))}
        </div>
      </div>

      {/* Active filter notice */}
      {hasActiveFilters && (
        <p className="text-[10px] text-gray-400 text-center -mt-1">
          Filtered: {PERIOD_OPTIONS.find(o => o.value === period)?.label}
          {genre !== 'all' ? ` · ${genre}` : ''}
        </p>
      )}

      {/* Top Titles */}
      <div>
        <SectionTitle>Top Titles</SectionTitle>
        <div className="bg-gray-800/50 border border-gray-700/60 rounded-xl p-4">
          <TopTitlesTable titles={data?.top_titles || []} />
        </div>
      </div>

      {/* Chart 1 — Trend (changes granularity based on period) */}
      <ChartCard title="Monthly Views Trend">
        <ViewsTrendChart data={data?.views_trend?.data || []} />
      </ChartCard>

      {/* Chart 2 — Regional (changes by genre filter) */}
      <ChartCard title="City Engagement Scores">
        <RegionalHeatmap data={data?.regional_chart?.data || []} />
      </ChartCard>

      {/* Chart 3 — Genre (always all genres for comparison) */}
      <ChartCard title="Views by Genre">
        <GenreBarChart data={data?.genre_chart?.data || []} />
      </ChartCard>

      {/* Chart 4 — Marketing (changes by period) */}
      <ChartCard title="Marketing Spend by Channel">
        <MarketingROAS data={data?.marketing_chart?.data || []} />
      </ChartCard>

    </div>
  )
}