const SOURCE_STYLES = {
  'SQL Database':  'bg-emerald-900/60 text-emerald-300 border border-emerald-700/50',
  'CSV Analytics': 'bg-blue-900/60 text-blue-300 border border-blue-700/50',
  default:         'bg-amber-900/60 text-amber-300 border border-amber-700/50',
}

export default function SourceBadge({ source }) {
  const style = SOURCE_STYLES[source] || SOURCE_STYLES.default
  const label = source.startsWith('PDF:')
    ? source.replace('PDF: ', '').replace(/_/g, ' ')
    : source

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${style}`}>
      {source.startsWith('PDF:') ? '📄' : source === 'SQL Database' ? '🗄️' : '📊'} {label}
    </span>
  )
}
