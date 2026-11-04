import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ApiError, api, toDataUrl } from './api'
import { fromBody, overridesFor, parseQuestions, questionsToText, toBody } from './form'
import { Api } from './components/Api'
import { Benchmark } from './components/Benchmark'
import { Header } from './components/Header'
import { ModelCardView } from './components/ModelCardView'
import { EMPTY, Playground, type FormState } from './components/Playground'
import { Tabs, type TabId } from './components/Tabs'
import type { DecideResponse, Example, GpuState, ModelCard } from './types'


export default function App() {
  const [tab, setTab] = useState<TabId>('playground')
  const [card, setCard] = useState<ModelCard | null>(null)
  const [examples, setExamples] = useState<Example[]>([])
  const [gpu, setGpu] = useState<GpuState>('unknown')
  const [form, setForm] = useState<FormState>(EMPTY)
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<DecideResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const loadedFirst = useRef(false)

  const questions = useMemo(() => parseQuestions(form.text, form.overrides, !!form.image), [form.text, form.overrides, form.image])
  const body = useMemo(() => toBody(form, questions), [form, questions])
  /** A user edit. The form no longer equals the loaded example, so the example card loses its highlight. */
  const edit = useCallback((f: FormState) => { setForm({ ...f, exampleId: null }); setResult(null); setError(null) }, [])

  const loadExample = useCallback(async (e: Example) => {
    const qs = fromBody(e.questions)
    const imageName = e.image ? e.image.split('/').pop()! : ''
    setForm({ state: e.state, object: e.object ?? '', image: null, imageName, text: questionsToText(qs), overrides: overridesFor(qs), exampleId: e.id })
    setResult(null); setError(null); setTab('playground')
    if (e.image) {
      try { const image = await toDataUrl(e.image); setForm(f => (f.exampleId === e.id ? { ...f, image } : f)) }
      catch { setError('The example image did not load.') }
    }
  }, [])

  // model card, examples, first example, wake the GPU
  useEffect(() => {
    api.model().then(setCard).catch(() => {})
    api.examples().then(ex => { setExamples(ex); if (!loadedFirst.current && ex[0]) { loadedFirst.current = true; loadExample(ex[0]) } }).catch(() => {})
    api.warm().then(r => setGpu(r.gpu)).catch(() => api.health().then(h => setGpu(h.gpu)).catch(() => setGpu('unknown')))
  }, [loadExample])

  // poll the GPU state while it is not warm
  useEffect(() => {
    if (gpu === 'warm') return
    const id = setInterval(() => api.health().then(h => setGpu(h.gpu)).catch(() => {}), 5000)
    return () => clearInterval(id)
  }, [gpu])

  const run = async () => {
    setRunning(true); setError(null)
    try {
      const res = await api.decide(body)
      setResult(res); setGpu('warm')
    } catch (e) {
      const msg = e instanceof ApiError ? (e.status === 429 ? 'Rate limit. Wait a minute and run again.' : e.message) : 'The request did not reach the backend.'
      setError(msg)
    } finally { setRunning(false) }
  }

  return (
    <div className="mx-auto max-w-[1180px] px-4 pb-16 sm:px-6">
      <Header card={card} gpu={gpu} />
      <Tabs tab={tab} onTab={setTab} />
      <main className="pt-7">
        {tab === 'playground' && (
          <Playground form={form} edit={edit} questions={questions} body={body} examples={examples} gpu={gpu}
            onRun={run} running={running} result={result} error={error} onLoadExample={loadExample} />
        )}
        {tab === 'benchmark' && (card ? <Benchmark card={card} /> : <Loading />)}
        {tab === 'api' && <Api body={body} />}
        {tab === 'model' && (card ? <ModelCardView card={card} /> : <Loading />)}
      </main>
      <footer className="mt-16 flex flex-wrap gap-x-6 gap-y-1 border-t border-ink-800 pt-4 text-[12px] text-ink-500">
        <span>Glimmer System One · Apache 2.0</span>
        <span>Example images from MVTec AD, CC BY-NC-SA 4.0, research use</span>
        <span>Muse Glimmer 30B by Meta</span>
      </footer>
    </div>
  )
}

function Loading() { return <p className="text-[13px] text-ink-500">Loading…</p> }
