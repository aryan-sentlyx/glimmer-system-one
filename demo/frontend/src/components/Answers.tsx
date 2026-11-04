import type { Answer, AnswerChoice, AnswerNoul, AnswerScore, DecideResponse } from '../types'

const pct = (p: number) => `${(p * 100).toFixed(p < 0.01 || p > 0.99 ? 2 : 1)}%`

function Bar({ p, cls, dim }: { p: number; cls: string; dim?: boolean }) {
  return <div className="bar"><i className={cls} style={{ transform: `scaleX(${Math.max(p, 0.004)})`, opacity: dim ? 0.45 : 1 }} /></div>
}

/** The question text as the title, the JSON key small beside the type. */
function Title({ name, label, type }: { name: string; label?: string; type: string }) {
  return (
    <div className="min-w-0">
      <div className="truncate font-medium">{label ?? name}</div>
      <div className="text-[11px] font-mono text-ink-500"><span className={`type-${type}`}>{type}</span>{label && <span className="ml-2">{name}</span>}</div>
    </div>
  )
}

function Noul({ name, label, a, threshold }: { name: string; label?: string; a: AnswerNoul; threshold: number }) {
  const above = a.noul >= threshold
  return (
    <div className="rise">
      <div className="flex items-start justify-between gap-3">
        <Title name={name} label={label} type="noul" />
        <div className="num text-[22px] leading-none">{pct(a.noul)}</div>
      </div>
      <div className="mt-2"><Bar p={a.noul} cls="bg-noul" /></div>
      <div className="mt-1.5 flex flex-wrap items-center justify-between gap-2 text-[12px] text-ink-500">
        <span>{a.mode.startsWith('head') ? `trained head · ${a.mode.includes('L13') ? 'layer 13' : 'layer 52'}` : a.mode}</span>
        <span className={above ? 'text-noul' : ''}>{above ? '≥' : '<'} {Math.round(threshold * 100)}% threshold · {above ? 'true' : 'false'}</span>
      </div>
    </div>
  )
}

function Choice({ name, label, a }: { name: string; label?: string; a: AnswerChoice }) {
  const rows = Object.entries(a.probabilities).sort((x, y) => y[1] - x[1])
  return (
    <div className="rise">
      <div className="flex items-start justify-between gap-3">
        <Title name={name} label={label} type="choice" />
        <div className="num text-[15px]">{a.choice}</div>
      </div>
      <div className="mt-2 space-y-1.5">
        {rows.map(([k, p]) => (
          <div key={k} className="grid grid-cols-[minmax(0,9rem)_1fr_3.6rem] items-center gap-2 text-[12.5px]">
            <span className={`truncate ${k === a.choice ? 'text-ink-100' : 'text-ink-500'}`}>{k}</span>
            <Bar p={p} cls="bg-choice" dim={k !== a.choice} />
            <span className="num text-right text-ink-300">{pct(p)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function Score({ name, label, a }: { name: string; label?: string; a: AnswerScore }) {
  const keys = Object.keys(a.probabilities)
  const n = keys.length - 1
  const nearest = a.legend[String(Math.round(a.score))]
  return (
    <div className="rise">
      <div className="flex items-start justify-between gap-3">
        <Title name={name} label={label} type="score" />
        <div className="num text-[15px]"><span className="text-[22px] leading-none">{a.score.toFixed(2)}</span> <span className="text-ink-500">/ {n}</span></div>
      </div>
      <div className="mt-2 grid gap-1" style={{ gridTemplateColumns: `repeat(${keys.length}, 1fr)` }}>
        {keys.map(k => (
          <div key={k} title={`${a.legend[k]}: ${pct(a.probabilities[k])}`}>
            <div className="bar"><i className="bg-score" style={{ transform: `scaleX(${Math.max(a.probabilities[k], 0.01)})` }} /></div>
            <div className="mt-1 truncate text-[11px] text-ink-500">{k} {a.legend[k]}</div>
          </div>
        ))}
      </div>
      <div className="mt-1.5 text-[12px] text-ink-500">expected level · nearest “{nearest}”</div>
    </div>
  )
}

export function AnswerList({ res, threshold, labels = {} }: { res: DecideResponse; threshold: number; labels?: Record<string, string> }) {
  const entries = Object.entries(res.answers) as [string, Answer][]
  return (
    <div className="space-y-5">
      {entries.map(([name, a]) => {
        const label = labels[name] || undefined
        return a.type === 'noul' ? <Noul key={name} name={name} label={label} a={a} threshold={threshold} /> :
          a.type === 'choice' ? <Choice key={name} name={name} label={label} a={a} /> : <Score key={name} name={name} label={label} a={a} />
      })}
    </div>
  )
}

export function TimingLine({ res }: { res: DecideResponse }) {
  const t = res.timing
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-[12px] text-ink-500">
      <span>forward <b className="num text-ink-300">{(t.forward_s * 1000).toFixed(0)} ms</b></span>
      <span>server <b className="num text-ink-300">{(t.total_s * 1000).toFixed(0)} ms</b></span>
      <span>round trip <b className="num text-ink-300">{t.round_trip_s.toFixed(2)} s</b>{t.cold_start && <span className="text-signal"> · cold start</span>}</span>
      <span><b className="num text-ink-300">{res.usage.prompts}</b> prompts · one pass</span>
      <span className="text-ink-700">{res.version}</span>
    </div>
  )
}
