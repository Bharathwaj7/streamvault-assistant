export const fmtNumber = (n) =>
  typeof n === 'number' ? n.toLocaleString() : n

export const fmtCurrency = (n) =>
  typeof n === 'number'
    ? `$${n.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
    : n

export const fmtPercent = (n) =>
  typeof n === 'number' ? `${(n * 100).toFixed(1)}%` : n

export const fmtDate = (d) =>
  d ? new Date(d).toLocaleDateString('en-US', { month: 'short', year: 'numeric' }) : d

export const truncate = (str, n = 60) =>
  str && str.length > n ? str.slice(0, n) + '…' : str
