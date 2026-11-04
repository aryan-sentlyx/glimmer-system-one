import type { DecideBody, QForm, QType, QuestionBody } from './types'

export const DEFECT_HEAD = 'noul_defective_known_L52'
export const HEADS: { value: string; label: string }[] = [
  { value: '', label: 'none (zero-shot)' },
  { value: DEFECT_HEAD, label: 'defect head, layer 52' },
  { value: 'noul_defective_known_L13', label: 'defect head, layer 13 (early exit)' },
]

/** Settings of one line that the parser cannot read from the line itself. Keyed by the trimmed line. */
export interface Override { name?: string; type?: QType; head?: string; raw?: boolean; gate?: string }
export type Overrides = Record<string, Override>

/* ---------- one line ---------- */

export interface ParsedLine { instructions: string; type: QType; options: string[]; bracketed: boolean }

/**
 * One line of the questions box.
 *   A statement.                         -> noul
 *   A question? [a, b, c]                -> choice, one option wins
 *   A question? [low < medium < high]    -> score, ordered levels
 */
export function parseLine(line: string): ParsedLine {
  const m = line.match(/^(.*?)\s*\[(.*)\]\s*$/)
  if (!m) return { instructions: line, type: 'noul', options: [], bracketed: false }
  const ordered = m[2].includes('<')
  const options = m[2].split(ordered ? '<' : /[,|]/).map(s => s.trim()).filter(Boolean)
  return { instructions: m[1].trim(), type: ordered ? 'score' : 'choice', options, bracketed: true }
}

/** The line that gives a question back when it is parsed. */
export function lineOf(q: { type: QType; instructions: string; options: string[] }): string {
  if (q.type === 'noul') return q.instructions
  return `${q.instructions} [${q.options.join(q.type === 'score' ? ' < ' : ', ')}]`
}

const STOP = new Set('the a an is are was were be been does do did this that these those it its there which what how of to in on at for from with should would could has have had any some'.split(' '))

/** A short JSON key made from the words of the question. */
export function slug(text: string, taken: Set<string>): string {
  const words = text.toLowerCase().replace(/[^a-z0-9\s]/g, ' ').split(/\s+/).filter(w => w && !STOP.has(w))
  const base = words.slice(0, 3).join('_').slice(0, 28).replace(/_+$/, '') || 'q'
  let name = base, k = 2
  while (taken.has(name)) name = `${base}_${k++}`
  return name
}

/* ---------- the whole box ---------- */

export function parseQuestions(text: string, overrides: Overrides, hasImage: boolean): QForm[] {
  const lines = text.split('\n').map(l => l.trim()).filter(Boolean)
  const taken = new Set<string>()
  const qs: QForm[] = lines.map((line, i) => {
    const p = parseLine(line)
    const ov = overrides[line] ?? {}
    const type: QType = p.bracketed && ov.type && ov.type !== 'noul' ? ov.type : p.type
    const name = ov.name?.trim() || slug(p.instructions || line, taken)
    taken.add(name)
    // A head needs an image. A noul line about a defect gets the trained defect head unless the user clears it.
    const autoHead = type === 'noul' && hasImage && /defect/i.test(p.instructions) ? DEFECT_HEAD : ''
    const head = type === 'noul' ? (ov.head !== undefined ? ov.head : autoHead) : ''
    return { id: `${i}:${line}`, line, name, type, instructions: p.instructions, options: p.options, head, raw: type === 'noul' && !head ? !!ov.raw : false, gate: '' }
  })
  // A choice with a "good" option is gated by the first noul that uses a head, unless the user sets the gate.
  const gateTarget = qs.find(q => q.type === 'noul' && q.head && hasImage)?.name ?? ''
  for (const q of qs) {
    if (q.type !== 'choice') continue
    const ov = overrides[q.line] ?? {}
    q.gate = ov.gate !== undefined ? ov.gate : (q.options.includes('good') && gateTarget ? gateTarget : '')
  }
  return qs
}

export function questionsToText(qs: QForm[]): string {
  return qs.map(lineOf).join('\n')
}

/** Overrides that make the parser give these questions back exactly, names and settings included. */
export function overridesFor(qs: QForm[]): Overrides {
  const out: Overrides = {}
  for (const q of qs) out[lineOf(q)] = { name: q.name, head: q.head, raw: q.raw, gate: q.gate }
  return out
}

/* ---------- JSON <-> form ---------- */

export function fromBody(qs: Record<string, QuestionBody>): QForm[] {
  return Object.entries(qs).map(([name, q], i) => {
    const options = q.type === 'choice' ? Object.keys(q.criteria ?? {}) : q.type === 'score' ? [...((q.criteria as string[]) ?? [])] : []
    const base = { type: q.type, instructions: q.instructions ?? '', options }
    return { id: `${i}:${name}`, line: lineOf(base), name, ...base, head: q.head ?? '', raw: !!q.raw, gate: q.gate ?? '' }
  })
}

export function toBody(form: { state: string; object: string; image: string | null }, qs: QForm[]): DecideBody {
  const questions: Record<string, QuestionBody> = {}
  for (const q of qs) {
    const body: QuestionBody = { type: q.type, instructions: q.instructions }
    if (q.type === 'choice') body.criteria = Object.fromEntries(q.options.map(o => [o, null]))
    if (q.type === 'score') body.criteria = q.options
    if (q.type === 'noul' && q.head && form.image) body.head = q.head
    if (q.type === 'noul' && q.raw) body.raw = true
    if (q.type === 'choice' && q.gate) body.gate = q.gate
    questions[q.name] = body
  }
  const out: DecideBody = { questions }
  if (form.state.trim()) out.state = form.state
  if (form.object.trim()) out.object = form.object.trim()
  if (form.image) out.image = form.image
  return out
}

/** The body as shown in the JSON editor: the image is shortened to keep it readable. */
export function prettyBody(body: DecideBody): string {
  const shown = { ...body }
  if (shown.image) shown.image = `data:image/png;base64,… (${Math.round((shown.image.length * 3) / 4 / 1024)} kB)`
  return JSON.stringify(shown, null, 2)
}

export function promptCount(qs: QForm[]): number {
  return qs.reduce((n, q) => n + (q.type === 'choice' ? q.options.length : 1), 0)
}
