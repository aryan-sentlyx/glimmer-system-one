import { useState } from 'react'
import type { BenchRow, ModelCard } from '../types'

type Key = keyof BenchRow
const COLS: { key: Key; label: string; num?: boolean; hint?: string }[] = [
  { key: 'system', label: 'System' },
  { key: 'auroc', label: 'AUROC', num: true, hint: 'ranking quality, 1.0 is perfect' },
  { key: 'acc', label: 'Acc at 0.5', num: true },
  { key: 'ece', label: 'ECE', num: true, hint: 'calibration error, lower is better' },
  { key: 'latency', label: 'Per image' },
  { key: 'open', label: 'Open weights' },
]

export function Benchmark({ card }: { card: ModelCard }) {
  const [sort, setSort] = useState<{ key: Key; dir: 1 | -1 }>({ key: 'auroc', dir: -1 })
  const rows = [...card.benchmark.rows].sort((a, b) => {
    const x = a[sort.key], y = b[sort.key]
    return (typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y))) * sort.dir
  })
  const best = (k: Key, v: number) => (k === 'ece' ? Math.min : Math.max)(...card.benchmark.rows.map(r => r[k] as number)) === v
  return (
    <div className="grid gap-10 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      <section>
        <h2 className="label">Defect detection · {card.benchmark.dataset}</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="data">
            <thead><tr>{COLS.map(c => (
              <th key={c.key} title={c.hint} className={c.num ? 'text-right' : ''}>
                <button className="cursor-pointer hover:text-ink-300" onClick={() => setSort(s => ({ key: c.key, dir: s.key === c.key ? (s.dir === 1 ? -1 : 1) : c.key === 'ece' || c.key === 'system' ? 1 : -1 }))}>
                  {c.label}{sort.key === c.key ? (sort.dir === 1 ? ' ↑' : ' ↓') : ''}
                </button>
              </th>))}</tr></thead>
            <tbody>{rows.map(r => (
              <tr key={r.system} className={r.system.startsWith('Glimmer') ? 'text-ink-100' : 'text-ink-300'}>
                <td>{r.system}</td>
                {(['auroc', 'acc', 'ece'] as const).map(k => (
                  <td key={k} className={`num text-right ${best(k, r[k]) ? 'text-signal' : ''}`}>{k === 'acc' ? `${(r.acc * 100).toFixed(1)}%` : r[k].toFixed(3)}</td>))}
                <td className="num whitespace-nowrap">{r.latency}</td>
                <td>{r.open ? <span className="text-noul">yes</span> : <span className="text-ink-500">no</span>}</td>
              </tr>))}</tbody>
          </table>
        </div>
        <p className="mt-3 max-w-[70ch] text-[12.5px] text-ink-500">
          The head rows use the held-out half of the images of known products. The zero-shot row is leave-one-product-out. The vendor rows and the Spark rows use all images with the same question. Amber marks the best value in a column.
        </p>
        <h2 className="label mt-10">Throughput · one H100 · 448 px</h2>
        <div className="mt-3"><table className="data">
          <thead><tr><th>Setting</th><th className="text-right">Per image</th><th className="text-right">Images / s</th></tr></thead>
          <tbody>{card.throughput.map(t => <tr key={t.setting}><td className="text-ink-300">{t.setting}</td><td className="num text-right">{t.per_image}</td><td className="num text-right">{t.images_per_s}</td></tr>)}</tbody>
        </table></div>
      </section>
      <section>
        <h2 className="label">Reliability · is 0.9 really 90%?</h2>
        <img src="/reliability.png" alt="Reliability diagram on MVTec AD: predicted probability against observed defect rate for each system" className="mt-3 w-full rounded-xs bg-ink-100" />
        <p className="mt-3 text-[12.5px] text-ink-500">A calibrated system sits on the diagonal. The decision vendors and Spark bend away from it. The Glimmer rows stay close, so a threshold on the probability means what it says.</p>
        <h2 className="label mt-10">Why speed is the story</h2>
        <p className="mt-3 text-[13.5px] leading-relaxed text-ink-300">
          Muse Spark 1.3 writes a median of <span className="num text-ink-100">1,144</span> reasoning tokens for one inspection image and takes <span className="num text-ink-100">8.0 s</span>. The decision head reads the same image in <span className="num text-ink-100">45 ms</span>, or <span className="num text-ink-100">21 ms</span> with the early exit after layer 13. More reasoning did not raise Spark's AUROC. The decision model is more accurate, better calibrated, and about 180 times faster.
        </p>
      </section>
    </div>
  )
}
