import { useEffect, useRef, useState } from 'react'
import { toDataUrl } from '../api'
import { HEADS, fromBody, overridesFor, prettyBody, promptCount, questionsToText, type Override, type Overrides } from '../form'
import type { DecideBody, DecideResponse, Example, GpuState, QForm } from '../types'
import { AnswerList, TimingLine } from './Answers'

export interface FormState {
  state: string; object: string; image: string | null; imageName: string
  text: string                 // the questions box, one question per line
  overrides: Overrides         // per line: name, type, head, raw, gate
  exampleId: string | null     // the loaded example, until the user edits the form
}
export const EMPTY: FormState = { state: '', object: '', image: null, imageName: '', text: '', overrides: {}, exampleId: null }

const PLACEHOLDER = [
  'The part has a visible defect.',
  'Which defect does it show? [good, broken_large, broken_small, contamination]',
  'How severe is the damage? [none < minor < moderate < severe]',
].join('\n')

/* ---------- examples ---------- */
function ExampleStrip({ examples, selected, onOpen }: { examples: Example[]; selected: string | null; onOpen: (e: Example) => void }) {
  if (examples.length === 0) return null
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <span className="label">Start from an example</span>
        <span className="text-[12px] text-ink-500">or write your own below</span>
      </div>
      <div className="mt-2 grid gap-2 grid-cols-2 sm:grid-cols-4 lg:grid-cols-7">
        {examples.map(e => {
          const on = e.id === selected
          return (
            <button key={e.id} onClick={() => onOpen(e)} aria-pressed={on}
              className={`flex cursor-pointer items-center gap-2.5 rounded-sm border p-2 text-left transition-colors ${on ? 'border-signal bg-ink-850' : 'border-ink-800 bg-ink-900 hover:border-ink-500'}`}>
              {e.image ? <img src={e.image} alt="" className="h-10 w-10 shrink-0 rounded-xs object-cover bg-ink-950" loading="lazy" />
                : <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xs bg-ink-950 font-mono text-[11px] text-ink-500">txt</span>}
              <span className="min-w-0">
                <span className="line-clamp-2 block text-[12.5px] leading-tight text-ink-100">{e.title.replace(/^Inspection: /, '')}</span>
                <span className="block truncate text-[11px] text-ink-500">{e.image ? (e.questions[Object.keys(e.questions)[0]]?.head ? 'inspection, head' : 'image, zero-shot') : 'text only'}</span>
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

/* ---------- 1 · context ---------- */
function ContextCard({ form, edit }: { form: FormState; edit: (f: FormState) => void }) {
  const input = useRef<HTMLInputElement>(null)
  const [over, setOver] = useState(false)
  const onImage = async (f: File) => edit({ ...form, image: await toDataUrl(f), imageName: f.name })
  useEffect(() => {
    const onPaste = (e: ClipboardEvent) => { const f = [...(e.clipboardData?.files ?? [])].find(f => f.type.startsWith('image/')); if (f) onImage(f) }
    window.addEventListener('paste', onPaste); return () => window.removeEventListener('paste', onPaste)
  })
  return (
    <div
      onDragOver={e => { e.preventDefault(); setOver(true) }} onDragLeave={() => setOver(false)}
      onDrop={e => { e.preventDefault(); setOver(false); const f = e.dataTransfer.files[0]; if (f) onImage(f) }}
      className={`rounded-sm border transition-colors ${over ? 'border-signal bg-ink-850' : 'border-ink-800 bg-ink-900'}`}>
      <div className="flex gap-3 p-2">
        {form.image ? (
          <img src={form.image} alt="" className="h-20 w-20 shrink-0 rounded-xs object-cover bg-ink-950" />
        ) : (
          <button onClick={() => input.current?.click()}
            className="flex h-20 w-20 shrink-0 cursor-pointer flex-col items-center justify-center gap-0.5 rounded-xs border border-dashed border-ink-700 text-[11px] leading-tight text-ink-500 hover:border-ink-500 hover:text-ink-300">
            <span className="text-[18px] leading-none">+</span><span>image</span>
          </button>
        )}
        <textarea className="field min-h-[5rem] flex-1 resize-y border-0 bg-transparent px-1 py-0.5" rows={3} value={form.state}
          onChange={e => edit({ ...form, state: e.target.value })}
          placeholder={form.image ? 'Optional. A sentence about the image, for every question.' : 'Describe the situation. Or paste a log, a ticket, an email. Or drop an image on the left.'} />
      </div>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-ink-850 px-2 py-1 text-[11.5px] text-ink-500">
        {form.image ? <>
          <span className="truncate text-ink-300">{form.imageName || 'image'}</span><span>448 px</span>
          <button className="cursor-pointer hover:text-ink-100" onClick={() => input.current?.click()}>replace</button>
          <button className="cursor-pointer hover:text-bad" onClick={() => edit({ ...form, image: null, imageName: '' })}>remove</button>
        </> : <span>Drop an image here, paste one, or <button className="cursor-pointer text-ink-300 hover:text-ink-100" onClick={() => input.current?.click()}>browse</button>. An image is optional.</span>}
      </div>
      <input ref={input} type="file" accept="image/*" className="hidden" onChange={e => { const f = e.target.files?.[0]; if (f) onImage(f); e.target.value = '' }} />
    </div>
  )
}

/* ---------- 2 · questions ---------- */
function ParsedList({ questions, setOverride }: { questions: QForm[]; setOverride: (line: string, patch: Override) => void }) {
  if (questions.length === 0) return <p className="text-[12.5px] text-ink-500">Each line becomes one question. The answer is a probability, not text.</p>
  return (
    <ul className="space-y-1.5">
      {questions.map(q => {
        const bracketed = q.type !== 'noul'
        const tag = <span className={`font-mono text-[11px] type-${q.type}`}>{q.type}</span>
        return (
          <li key={q.id} className="grid grid-cols-[3.4rem_1fr] items-baseline gap-2 text-[12.5px]">
            {bracketed
              ? <button className="cursor-pointer text-left hover:underline" title="Click to switch between choice and score"
                  onClick={() => setOverride(q.line, { type: q.type === 'choice' ? 'score' : 'choice' })}>{tag}</button>
              : <span title="A statement. The model returns the probability that it is true.">{tag}</span>}
            <span className="min-w-0 text-ink-300">
              <span className="text-ink-100">{q.instructions || <i className="text-ink-500">no text</i>}</span>
              {bracketed && (q.options.length > 0
                ? <span className="ml-1.5 text-ink-500">{q.options.join(q.type === 'score' ? ' < ' : ' · ')}</span>
                : <span className="ml-1.5 text-bad">add options between the brackets</span>)}
              {q.head && <span className="ml-1.5 text-noul/80">· trained head</span>}
              {q.gate && <span className="ml-1.5 text-choice/80">· gated by {q.gate}</span>}
              {q.raw && <span className="ml-1.5 text-ink-500">· raw</span>}
            </span>
          </li>
        )
      })}
    </ul>
  )
}

/* ---------- advanced ---------- */
function Advanced({ form, edit, questions, body, setOverride }: {
  form: FormState; edit: (f: FormState) => void; questions: QForm[]; body: DecideBody; setOverride: (line: string, patch: Override) => void
}) {
  const [jsonText, setJsonText] = useState('')
  const [dirty, setDirty] = useState(false)
  const [jsonErr, setJsonErr] = useState<string | null>(null)
  useEffect(() => { if (!dirty) { setJsonText(prettyBody(body)); setJsonErr(null) } }, [body, dirty])
  const applyJson = () => {
    try {
      const parsed = JSON.parse(jsonText) as DecideBody
      if (!parsed.questions || typeof parsed.questions !== 'object') throw new Error('"questions" must be an object')
      const qs = fromBody(parsed.questions)
      edit({ ...form, state: parsed.state ?? '', object: parsed.object ?? '', text: questionsToText(qs), overrides: overridesFor(qs) })
      setDirty(false); setJsonErr(null)
    } catch (e) { setJsonErr((e as Error).message) }
  }
  const noulNames = questions.filter(q => q.type === 'noul').map(q => q.name)
  return (
    <details className="group">
      <summary className="label cursor-pointer select-none list-none hover:text-ink-300">
        <span className="inline-block w-3 transition-transform group-open:rotate-90">▸</span> Advanced
      </summary>
      <div className="mt-4 space-y-6 border-l border-ink-800 pl-4">
        <label className="grid max-w-[16rem] gap-1"><span className="label">Object</span>
          <input className="field" value={form.object} onChange={e => edit({ ...form, object: e.target.value })} placeholder="part" />
          <span className="text-[11px] text-ink-500">The noun in the prompt of a trained head.</span></label>
        {questions.length > 0 && (
          <div>
            <span className="label">Per question</span>
            <div className="mt-2 space-y-2">
              {questions.map(q => (
                <div key={q.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[12px] text-ink-500">
                  <span className={`w-10 font-mono text-[11px] type-${q.type}`}>{q.type}</span>
                  <label className="flex items-center gap-1.5">key
                    <input className="field w-[11rem] py-0.5 font-mono text-[12px]" value={q.name} onChange={e => setOverride(q.line, { name: e.target.value.replace(/\s+/g, '_') })} /></label>
                  {q.type === 'noul' && (
                    <label className="flex items-center gap-1.5">head
                      <select className="field w-auto py-0.5 text-[12px]" value={q.head} disabled={!form.image} title={form.image ? '' : 'A head needs an image'} onChange={e => setOverride(q.line, { head: e.target.value })}>
                        {HEADS.map(h => <option key={h.value} value={h.value}>{h.label}</option>)}
                      </select></label>
                  )}
                  {q.type === 'noul' && !q.head && (
                    <label className="flex items-center gap-1.5"><input type="checkbox" checked={q.raw} onChange={e => setOverride(q.line, { raw: e.target.checked })} /> raw logits, no temperature</label>
                  )}
                  {q.type === 'choice' && noulNames.length > 0 && (
                    <label className="flex items-center gap-1.5">gate
                      <select className="field w-auto py-0.5 text-[12px]" value={q.gate} onChange={e => setOverride(q.line, { gate: e.target.value })}>
                        <option value="">none</option>
                        {noulNames.map(n => <option key={n} value={n}>P(“good”) = 1 − {n}</option>)}
                      </select></label>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
        <div>
          <div className="flex items-center justify-between"><span className="label">Request JSON</span>
            {dirty && <button className="btn btn-ghost px-2 py-0.5 text-[12px]" onClick={() => setDirty(false)}>discard edits</button>}</div>
          <textarea className="field mt-2 min-h-[14rem] font-mono text-[12px] leading-relaxed" value={jsonText} spellCheck={false}
            onChange={e => { setJsonText(e.target.value); setDirty(true) }} />
          {jsonErr && <p className="mt-1 text-[12px] text-bad">{jsonErr}</p>}
          <div className="mt-2 flex items-center gap-3 text-[12px] text-ink-500">
            <button className="btn" disabled={!dirty} onClick={applyJson}>Apply to the form</button>
            <span>The image stays as set above. The API tab has the same body as curl and Python.</span>
          </div>
        </div>
      </div>
    </details>
  )
}

/* ---------- the playground ---------- */
export function Playground({ form, edit, questions, body, examples, gpu, onRun, running, result, error, onLoadExample }: {
  form: FormState; edit: (f: FormState) => void; questions: QForm[]; body: DecideBody; examples: Example[]; gpu: GpuState
  onRun: () => void; running: boolean; result: DecideResponse | null; error: string | null
  onLoadExample: (e: Example) => void
}) {
  const [outTab, setOutTab] = useState<'answers' | 'json'>('answers')
  const [threshold, setThreshold] = useState(0.5)
  const n = promptCount(questions)
  const hasContext = !!form.image || !!form.state.trim()
  const incomplete = questions.some(q => q.type !== 'noul' && q.options.length === 0)
  const canRun = n > 0 && n <= 24 && hasContext && !incomplete && !running
  const setOverride = (line: string, patch: Override) => edit({ ...form, overrides: { ...form.overrides, [line]: { ...form.overrides[line], ...patch } } })

  const shown = result
  const waiting = canRun && !result && !error   // the form is ready, the Run button asks for the click
  const labels = Object.fromEntries(questions.map(q => [q.name, q.instructions]))

  return (
    <div className="space-y-8">
      <ExampleStrip examples={examples} selected={form.exampleId} onOpen={onLoadExample} />

      <div className="grid gap-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
        {/* INPUT */}
        <section className="space-y-6">
          <div>
            <div className="flex items-baseline justify-between"><h2 className="label">1 · Context</h2><span className="text-[12px] text-ink-500">an image, a text, or both</span></div>
            <div className="mt-2"><ContextCard form={form} edit={edit} /></div>
          </div>

          <div>
            <div className="flex items-baseline justify-between"><h2 className="label">2 · Questions</h2><span className="text-[12px] text-ink-500">one per line</span></div>
            <textarea className="field mt-2 min-h-[6rem] resize-y leading-relaxed" rows={Math.min(12, Math.max(4, form.text.split('\n').length + 1))} value={form.text} spellCheck={false}
              onChange={e => edit({ ...form, text: e.target.value })} placeholder={PLACEHOLDER} />
            <div className="mt-2.5"><ParsedList questions={questions} setOverride={setOverride} /></div>
            <p className="mt-2.5 text-[11.5px] leading-relaxed text-ink-500">
              A statement gives <span className="type-noul font-mono">noul</span>, the probability that it is true.
              Options in brackets <span className="font-mono text-ink-300">[a, b, c]</span> give <span className="type-choice font-mono">choice</span>, one option wins.
              Ordered levels <span className="font-mono text-ink-300">[low &lt; high]</span> give <span className="type-score font-mono">score</span>.
            </p>
          </div>

          <div className="sticky bottom-0 z-10 -mx-1 flex items-center justify-between gap-3 border-t border-ink-900 bg-ink-950 px-1 py-3">
            <div className="flex items-center gap-3">
              <button className={`btn btn-primary ${waiting ? 'btn-attn' : ''}`} disabled={!canRun} onClick={onRun}>
                {running ? (gpu === 'warm' ? 'Running…' : 'Waking the GPU, about 50 s…') : 'Run'}
                {!running && <span aria-hidden="true">▶</span>}
              </button>
              <span className="text-[12px] text-ink-500">
                {n > 24 ? <span className="text-bad">at most 24 prompts</span>
                  : !hasContext && n > 0 ? 'add an image or a text first'
                  : n === 0 ? 'write a question above' : `${n} prompt${n === 1 ? '' : 's'} · one forward pass`}
              </span>
            </div>
            <button className="btn btn-ghost" onClick={() => edit(EMPTY)}>Clear</button>
          </div>

          <Advanced form={form} edit={edit} questions={questions} body={body} setOverride={setOverride} />
        </section>

        {/* OUTPUT */}
        <section className="lg:border-l lg:border-ink-800 lg:pl-8">
          <div className="flex items-center justify-between">
            <h2 className="label">Output</h2>
            {shown && <div className="flex gap-3 text-[12px]">
              {(['answers', 'json'] as const).map(t => <button key={t} className={`cursor-pointer ${outTab === t ? 'text-ink-100' : 'text-ink-500 hover:text-ink-300'}`} onClick={() => setOutTab(t)}>{t.toUpperCase()}</button>)}
            </div>}
          </div>
          <div className="rule mt-2" />
          <div className="mt-4 min-h-[18rem] space-y-4">
            {error && <p className="rise rounded-sm border border-bad/40 bg-bad/10 px-3 py-2 text-[13px] text-ink-100">{error}</p>}
            {running && (
              <div className="flex flex-col gap-2 text-[13px]">
                <span className="text-ink-300">{gpu === 'warm' ? 'One forward pass on the H100…' : 'The GPU container loads 60 GB of weights. About 50 s, once.'}</span>
                <span className="pulse inline-block h-1 w-24 rounded-xs bg-signal" />
              </div>
            )}
            {!running && !error && !shown && (
              <div className="flex min-h-[18rem] flex-col items-start justify-center gap-2 text-[13px] text-ink-500">
                <span>{canRun ? 'Press Run. The answers show here.' : 'The answers show here.'} Each question returns a probability, not text.</span>
                <span>The model runs every question in one batch, in one forward pass.</span>
              </div>
            )}
            {shown && !error && (outTab === 'answers' ? (
              <div className="space-y-6">
                <AnswerList res={shown} threshold={threshold} labels={labels} />
                {Object.values(shown.answers).some(a => a.type === 'noul') && (
                  <label className="grid gap-1.5 text-[12px] text-ink-500">
                    <span className="flex justify-between"><span className="label">Threshold for noul answers</span><span className="num text-ink-300">{Math.round(threshold * 100)}%</span></span>
                    <input type="range" min={1} max={99} value={Math.round(threshold * 100)} onChange={e => setThreshold(Number(e.target.value) / 100)} className="accent-signal" />
                    <span>Calibrated probabilities make a threshold meaningful. Move it to see which answers flip.</span>
                  </label>
                )}
                <div className="rule" />
                <TimingLine res={shown} />
              </div>
            ) : (
              <pre className="overflow-auto rounded-sm bg-ink-900 p-3 font-mono text-[12px] leading-relaxed text-ink-300">{JSON.stringify(shown, null, 2)}</pre>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}
