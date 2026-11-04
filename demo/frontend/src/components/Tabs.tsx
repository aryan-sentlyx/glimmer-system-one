export type TabId = 'playground' | 'benchmark' | 'api' | 'model'
const TABS: { id: TabId; label: string }[] = [
  { id: 'playground', label: 'Playground' }, { id: 'benchmark', label: 'Benchmark' },
  { id: 'api', label: 'API' }, { id: 'model', label: 'Model card' },
]
export function Tabs({ tab, onTab }: { tab: TabId; onTab: (t: TabId) => void }) {
  return (
    <nav role="tablist" className="flex gap-5 overflow-x-auto border-b border-ink-800 [scrollbar-width:none]">
      {TABS.map(t => (
        <button key={t.id} role="tab" aria-selected={tab === t.id} className="tab shrink-0" onClick={() => onTab(t.id)}>{t.label}</button>
      ))}
    </nav>
  )
}
