/** Status = icon + label + colour (fixed status palette), never colour alone. */
const KINDS: Record<string, { tone: 'good' | 'warning' | 'critical' | 'neutral'; icon: string; label: string }> = {
  success: { tone: 'good', icon: '✓', label: 'Success' },
  pass: { tone: 'good', icon: '✓', label: 'Pass' },
  ok: { tone: 'good', icon: '✓', label: 'OK' },
  warn: { tone: 'warning', icon: '!', label: 'Warning' },
  fail: { tone: 'critical', icon: '✕', label: 'Fail' },
  failed: { tone: 'critical', icon: '✕', label: 'Failed' },
  skipped: { tone: 'neutral', icon: '–', label: 'Skipped' },
  running: { tone: 'neutral', icon: '…', label: 'Running' },
}

export function StatusBadge({ status }: { status: string }) {
  const kind = KINDS[status] ?? { tone: 'neutral' as const, icon: '?', label: status }
  return (
    <span className={`badge badge-${kind.tone}`}>
      <span className="badge-icon" aria-hidden="true">
        {kind.icon}
      </span>
      {kind.label}
    </span>
  )
}
