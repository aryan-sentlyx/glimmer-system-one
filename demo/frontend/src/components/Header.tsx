import type { GpuState, ModelCard } from '../types'

const GPU: Record<GpuState, { text: string; cls: string; pulse?: boolean }> = {
  warm: { text: 'GPU warm', cls: 'bg-noul' },
  warming: { text: 'GPU warming', cls: 'bg-signal', pulse: true },
  cold: { text: 'GPU cold', cls: 'bg-ink-500' },
  unknown: { text: 'GPU …', cls: 'bg-ink-700' },
}

export function Header({ card, gpu }: { card: ModelCard | null; gpu: GpuState }) {
  const g = GPU[gpu]
  return (
    <header className="pt-7 pb-5">
      <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden="true">
              <circle cx="16" cy="16" r="10" fill="none" stroke="var(--color-signal)" strokeWidth="2.5" />
              <circle cx="16" cy="16" r="3.2" fill="var(--color-signal)" />
            </svg>
            <h1 className="font-cond text-[clamp(1.6rem,3.5vw,2.3rem)] font-semibold leading-none tracking-tight">
              Glimmer <span className="text-ink-300">System One</span>
            </h1>
          </div>
          <p className="mt-3 max-w-[62ch] text-[15px] leading-snug text-ink-300">
            {card?.tagline ?? 'An open multimodal decision model on Muse Glimmer 30B.'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="chip" title="The GPU container idles out after 10 minutes. The page wakes it on load.">
            <i className={`inline-block h-2 w-2 rounded-full ${g.cls} ${g.pulse ? 'pulse' : ''}`} />
            {g.text}
          </span>
          {card && <a className="btn btn-ghost" href={card.links.repository} target="_blank" rel="noreferrer">GitHub</a>}
          {card && <a className="btn btn-ghost" href={card.links.huggingface} target="_blank" rel="noreferrer">Hugging Face</a>}
        </div>
      </div>
      <div className="mt-5 flex flex-wrap gap-x-5 gap-y-1.5 text-[12.5px] text-ink-300">
        <span><b className="text-ink-100 font-medium">Base</b> Muse Glimmer 30B</span>
        <span><b className="text-ink-100 font-medium">License</b> Apache 2.0</span>
        <span><b className="text-ink-100 font-medium">Serving</b> one H100, Modal</span>
        <span><b className="text-ink-100 font-medium">Per image</b> <span className="num">45 ms</span> batched, <span className="num">21 ms</span> early exit</span>
        <span><b className="text-ink-100 font-medium">AUROC</b> <span className="num">0.962</span> on MVTec AD</span>
        <span><b className="text-ink-100 font-medium">Questions</b> <span className="type-noul">noul</span> · <span className="type-choice">choice</span> · <span className="type-score">score</span></span>
      </div>
    </header>
  )
}
