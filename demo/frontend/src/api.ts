import type { DecideBody, DecideResponse, Example, GpuState, ModelCard } from './types'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) { super(message); this.status = status }
}

async function json<T>(r: Response): Promise<T> {
  if (!r.ok) {
    let detail = r.statusText
    try { detail = (await r.json()).detail ?? detail } catch { /* keep statusText */ }
    throw new ApiError(r.status, detail)
  }
  return r.json() as Promise<T>
}

export const api = {
  model: () => fetch('/api/model').then(r => json<ModelCard>(r)),
  examples: () => fetch('/api/examples').then(r => json<Example[]>(r)),
  health: () => fetch('/api/health').then(r => json<{ ok: boolean; gpu: GpuState }>(r)),
  warm: () => fetch('/api/warm', { method: 'POST' }).then(r => json<{ gpu: GpuState }>(r)),
  decide: (body: DecideBody) =>
    fetch('/api/decide', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) })
      .then(r => json<DecideResponse>(r)),
}

/** Reads a File or a URL as a PNG data URL, at most 448 px on the long side. */
export async function toDataUrl(src: File | string, maxSide = 448): Promise<string> {
  const blob = typeof src === 'string' ? await fetch(src).then(r => r.blob()) : src
  const bitmap = await createImageBitmap(blob)
  const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height))
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(bitmap.width * scale); canvas.height = Math.round(bitmap.height * scale)
  canvas.getContext('2d')!.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
  bitmap.close()
  return canvas.toDataURL('image/png')
}
