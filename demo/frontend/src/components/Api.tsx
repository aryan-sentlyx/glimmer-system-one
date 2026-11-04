import { useState } from 'react'
import type { DecideBody } from '../types'

const ORIGIN = typeof window !== 'undefined' ? window.location.origin : ''

function Snippet({ title, code }: { title: string; code: string }) {
  const [done, setDone] = useState(false)
  const copy = () => navigator.clipboard.writeText(code).then(() => { setDone(true); setTimeout(() => setDone(false), 1200) })
  return (
    <div>
      <div className="flex items-center justify-between"><span className="label">{title}</span>
        <button className="btn btn-ghost px-2 py-0.5 text-[12px]" onClick={copy}>{done ? 'copied' : 'copy'}</button></div>
      <pre className="mt-1.5 overflow-auto rounded-sm bg-ink-900 p-3 font-mono text-[12px] leading-relaxed text-ink-300">{code}</pre>
    </div>
  )
}

export function Api({ body }: { body: DecideBody }) {
  const shown = { ...body, image: body.image ? '<base64 png, or a data URL>' : undefined }
  if (!shown.image) delete shown.image
  const js = JSON.stringify(shown, null, 2)
  const curl = `curl -s ${ORIGIN}/api/decide \\\n  -H 'content-type: application/json' \\\n  -d '${js.replace(/'/g, "'\\''")}'`
  const py = `import base64, requests\n\nbody = ${js.replace(/null/g, 'None').replace(/true/g, 'True').replace(/false/g, 'False')}\n${body.image ? `body["image"] = base64.b64encode(open("part.png", "rb").read()).decode()\n` : ''}r = requests.post("${ORIGIN}/api/decide", json=body, timeout=120)\nfor name, a in r.json()["answers"].items():\n    print(name, a.get("noul", a.get("choice", a.get("score"))))`
  return (
    <div className="grid gap-10 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      <section className="space-y-6 text-[13.5px] leading-relaxed text-ink-300">
        <div>
          <h2 className="label">Endpoint</h2>
          <p className="mt-2"><code className="font-mono text-ink-100">POST {ORIGIN}/api/decide</code></p>
          <p className="mt-2">The body carries an optional <code className="font-mono">image</code>, an optional <code className="font-mono">state</code> text, an optional <code className="font-mono">object</code> noun, and a <code className="font-mono">questions</code> object. At least one of image or state. Up to 24 prompts per call. A choice with N options costs N prompts.</p>
        </div>
        <div>
          <h2 className="label">Question types</h2>
          <ul className="mt-2 space-y-2">
            <li><span className="type-noul font-mono">noul</span> · <code className="font-mono">instructions</code> is a statement. Returns <code className="font-mono">noul</code>, P(true). Optional <code className="font-mono">head</code>, <code className="font-mono">raw</code>.</li>
            <li><span className="type-choice font-mono">choice</span> · <code className="font-mono">criteria</code> maps option to a description or null. Returns <code className="font-mono">choice</code>, <code className="font-mono">probabilities</code>. Optional <code className="font-mono">gate</code>, the name of a noul question that sets P(“good”).</li>
            <li><span className="type-score font-mono">score</span> · <code className="font-mono">criteria</code> is an ordered list of levels. Returns <code className="font-mono">score</code>, the expected level, and <code className="font-mono">probabilities</code>.</li>
          </ul>
        </div>
        <div>
          <h2 className="label">Response</h2>
          <p className="mt-2"><code className="font-mono">answers</code> per question, <code className="font-mono">usage.prompts</code>, and <code className="font-mono">timing</code> with <code className="font-mono">forward_s</code> on the GPU, <code className="font-mono">total_s</code> on the server, and <code className="font-mono">round_trip_s</code> from the backend.</p>
        </div>
        <div>
          <h2 className="label">Limits</h2>
          <p className="mt-2">20 calls per minute per IP. Images up to 4 MB, resized to 448 px. The GPU idles out after 10 minutes. <code className="font-mono">POST /api/warm</code> wakes it, <code className="font-mono">GET /api/health</code> reports it.</p>
        </div>
      </section>
      <section className="space-y-6">
        <p className="text-[12.5px] text-ink-500">The snippets carry the request from the playground.</p>
        <Snippet title="curl" code={curl} />
        <Snippet title="python" code={py} />
      </section>
    </div>
  )
}
