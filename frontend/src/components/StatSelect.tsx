import { useMemo } from 'react'

import type { StatDefinition } from '../api/client'
import { useStatCatalogue } from '../api/hooks'
import { titleCase } from '../lib/format'

/** Stat dropdown grouped by category. */
export function StatSelect({
  label,
  value,
  onChange,
}: {
  label: string
  value: string
  onChange: (statId: string) => void
}) {
  const catalogue = useStatCatalogue()
  const grouped = useMemo(() => {
    const groups = new Map<string, StatDefinition[]>()
    for (const stat of catalogue.data ?? []) {
      const key = stat.categories[0] ?? 'OTHER'
      groups.set(key, [...(groups.get(key) ?? []), stat])
    }
    return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b))
  }, [catalogue.data])

  return (
    <label>
      {label}
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {grouped.map(([group, stats]) => (
          <optgroup key={group} label={titleCase(group)}>
            {stats.map((s) => (
              <option key={s.stat_id} value={s.stat_id}>
                {s.stat_name}
              </option>
            ))}
          </optgroup>
        ))}
        {!catalogue.data && <option value={value}>{value}</option>}
      </select>
    </label>
  )
}
