export type QType = 'noul' | 'choice' | 'score'

export interface QuestionBody {
  type: QType
  instructions: string
  criteria?: Record<string, string | null> | string[]
  head?: string
  raw?: boolean
  gate?: string
}

export interface DecideBody {
  state?: string
  image?: string
  object?: string
  questions: Record<string, QuestionBody>
}

export interface Example {
  id: string
  title: string
  group: string
  image: string | null
  object: string | null
  state: string
  questions: Record<string, QuestionBody>
  expected: string
  note: string
  /** A response from an earlier run, kept for reference. The page does not show it. */
  answers?: DecideResponse
}

export interface AnswerNoul { type: 'noul'; noul: number; mode: string }
export interface AnswerChoice { type: 'choice'; choice: string; confidence: number; probabilities: Record<string, number> }
export interface AnswerScore { type: 'score'; score: number; confidence: number; probabilities: Record<string, number>; legend: Record<string, string> }
export type Answer = AnswerNoul | AnswerChoice | AnswerScore

export interface DecideResponse {
  model: string
  version: string
  answers: Record<string, Answer>
  input: { image: boolean; state_chars: number }
  usage: { input_tokens: number; prompts: number; output_tokens: number }
  timing: { forward_s: number; total_s: number; round_trip_s: number; cold_start: boolean }
}

export interface BenchRow { system: string; auroc: number; acc: number; ece: number; latency: string; open: boolean }

export interface ModelCard {
  name: string
  tagline: string
  base_model: string
  base_model_url: string
  parameters: string
  license: string
  hardware: string
  input: string[]
  output: string
  question_types: { type: QType; what: string; how: string }[]
  modes: { mode: string; when: string; auroc: number; acc: number; ece: number }[]
  benchmark: { dataset: string; rows: BenchRow[] }
  throughput: { setting: string; per_image: string; images_per_s: number }[]
  limits: string[]
  links: { repository: string; huggingface: string; hackathon: string }
}

export type GpuState = 'cold' | 'warming' | 'warm' | 'unknown'

/** One question as the page derives it from one line of the questions box. */
export interface QForm {
  id: string
  line: string          // the trimmed line in the questions box, the key of its overrides
  name: string          // the JSON key of the question
  type: QType
  instructions: string
  options: string[]     // choice options or score levels, in order
  head: string          // '' or a head name
  raw: boolean
  gate: string          // '' or the name of a noul question
}
