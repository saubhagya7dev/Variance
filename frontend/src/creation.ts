import { request } from './api'
export type Direction = { style: string; medium: string; mood: string; palette: string; lighting: string; composition: string; preserve: string; avoid: string; aspect_ratio: string }
export type Prompt = { id: string; version: number; direction: Direction; prompt_text: string; context: { references: { id: string; title: string }[] }; created_at: string }
export type Preview = Pick<Prompt, 'context' | 'prompt_text'> & { context_hash: string }
export type Batch = { id: string; prompt_id: string; mode: 'manual' | 'api'; provider: string; model: string; target_count: number; status: string; error: string; created_at: string }
export type Artwork = { id: string; title: string; width: number; height: number; decision: 'pending' | 'approved' | 'rejected'; review_note: string; revision: number }
export const base = (id: string) => `/characters/${id}`
export const creation = {
  prompts: (id: string) => request<Prompt[]>(`${base(id)}/prompts`),
  preview: (id: string, direction: Direction) => request<Preview>(`${base(id)}/prompts/preview`, 'POST', direction),
  save: (id: string, direction: Direction, preview: Preview) => request<Prompt>(`${base(id)}/prompts`, 'POST', { direction, context_hash: preview.context_hash, prompt_text: preview.prompt_text }),
  batches: (id: string) => request<Batch[]>(`${base(id)}/batches`),
  batch: (id: string, prompt_id: string, mode: string, target_count: number, request_key: string) => request<Batch>(`${base(id)}/batches`, 'POST', { prompt_id, mode, target_count, request_key }),
  artwork: (id: string, batch: string) => request<Artwork[]>(`${base(id)}/batches/${batch}/artwork`),
  review: (id: string, art: Artwork, decision: Artwork['decision'], review_note: string) => request<Artwork>(`${base(id)}/artwork/${art.id}`, 'PATCH', { decision, review_note, revision: art.revision }),
  pack: (id: string, prompt: string) => `/api${base(id)}/prompts/${prompt}/pack`,
  image: (id: string, art: string) => `/api${base(id)}/artwork/${art}/image`,
  async upload(id: string, batch: string, file: File) {
    if (file.size > 8 * 1024 * 1024) throw new Error('Choose an image smaller than 8 MB.')
    const response = await fetch(`/api${base(id)}/batches/${batch}/artwork?title=${encodeURIComponent(file.name.slice(0, 160))}`, { method: 'POST', headers: { 'X-Variance-Client': 'studio' }, body: file })
    if (!response.ok) { const error = await response.json(); throw new Error(error.detail || 'Import failed.') }
    return response.json() as Promise<Artwork>
  },
}
