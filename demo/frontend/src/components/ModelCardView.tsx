import type { ModelCard } from '../types'

export function ModelCardView({ card }: { card: ModelCard }) {
  return (
    <div className="grid gap-10 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      <section className="space-y-6 text-[13.5px] leading-relaxed">
        <dl className="grid grid-cols-[7rem_1fr] gap-y-2 text-ink-300">
          <dt className="label pt-0.5">Base model</dt><dd><a className="text-ink-100 underline decoration-ink-700 underline-offset-2 hover:decoration-signal" href={card.base_model_url} target="_blank" rel="noreferrer">{card.base_model}</a></dd>
          <dt className="label pt-0.5">Parameters</dt><dd>{card.parameters}</dd>
          <dt className="label pt-0.5">License</dt><dd>{card.license}</dd>
          <dt className="label pt-0.5">Hardware</dt><dd>{card.hardware}</dd>
          <dt className="label pt-0.5">Input</dt><dd>{card.input.join(' · ')}</dd>
          <dt className="label pt-0.5">Output</dt><dd>{card.output}</dd>
          <dt className="label pt-0.5">Built for</dt><dd>{card.links.hackathon}</dd>
        </dl>
        <div>
          <h2 className="label">Limits</h2>
          <ul className="mt-2 list-disc space-y-1 pl-4 text-ink-300">{card.limits.map(l => <li key={l}>{l}</li>)}</ul>
        </div>
      </section>
      <section className="space-y-8">
        <div>
          <h2 className="label">How a question becomes a probability</h2>
          <div className="mt-3 space-y-4">
            {card.question_types.map(q => (
              <div key={q.type} className="grid gap-1 border-l-2 pl-3" style={{ borderColor: `var(--color-${q.type})` }}>
                <div><span className={`font-mono type-${q.type}`}>{q.type}</span> <span className="text-ink-300">· {q.what}</span></div>
                <div className="text-[12.5px] text-ink-500">{q.how}</div>
              </div>))}
          </div>
        </div>
        <div>
          <h2 className="label">Modes</h2>
          <table className="data mt-2">
            <thead><tr><th>Mode</th><th>When</th><th className="text-right">AUROC</th><th className="text-right">Acc</th><th className="text-right">ECE</th></tr></thead>
            <tbody>{card.modes.map(m => (
              <tr key={m.mode}><td className="whitespace-nowrap text-ink-100">{m.mode}</td><td className="text-ink-300">{m.when}</td>
                <td className="num text-right">{m.auroc.toFixed(3)}</td><td className="num text-right">{(m.acc * 100).toFixed(1)}%</td><td className="num text-right">{m.ece.toFixed(3)}</td></tr>))}</tbody>
          </table>
          <p className="mt-2 text-[12.5px] text-ink-500">A head is a logistic regression on the hidden state at the answer position. It is valid only for the exact prompt template it was trained on. The template name travels with the head.</p>
        </div>
      </section>
    </div>
  )
}
