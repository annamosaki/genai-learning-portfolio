import { clsx, type ClassValue } from 'clsx'

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs)
}

/** Parse ISO timestamps; treat naive values as UTC. */
export function parseTimestamp(
  timestamp: string | Date | number | undefined | null
): Date | null {
  if (timestamp == null) return null
  if (timestamp instanceof Date) {
    return Number.isNaN(timestamp.getTime()) ? null : timestamp
  }
  if (typeof timestamp === 'number') {
    const d = new Date(timestamp)
    return Number.isNaN(d.getTime()) ? null : d
  }
  const raw = String(timestamp).trim()
  if (!raw) return null
  // Backend may emit naive UTC (no Z) — force UTC so local TZ doesn't skew by hours
  const normalized =
    /^\d{4}-\d{2}-\d{2}T/.test(raw) && !/[zZ]|[+-]\d{2}:?\d{2}$/.test(raw)
      ? `${raw}Z`
      : raw
  const d = new Date(normalized)
  return Number.isNaN(d.getTime()) ? null : d
}

/** Elapsed since run start, e.g. "+12s", "+1m 05s". */
export function formatElapsed(from: Date | null, to: Date | null): string {
  if (!from || !to) return '—'
  const ms = Math.max(0, to.getTime() - from.getTime())
  const totalSec = Math.floor(ms / 1000)
  const hours = Math.floor(totalSec / 3600)
  const minutes = Math.floor((totalSec % 3600) / 60)
  const seconds = totalSec % 60
  if (hours > 0) {
    return `+${hours}h ${String(minutes).padStart(2, '0')}m`
  }
  if (minutes > 0) {
    return `+${minutes}m ${String(seconds).padStart(2, '0')}s`
  }
  return `+${seconds}s`
}

/** Relative to now; prefers seconds for recent events. */
export function formatDistanceToNow(timestamp: string): string {
  const time = parseTimestamp(timestamp)
  if (!time) return '—'
  const diff = Math.max(0, Date.now() - time.getTime())
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)

  if (hours > 0) return `${hours}h ago`
  if (minutes > 0) return `${minutes}m ago`
  return `${seconds}s ago`
}
