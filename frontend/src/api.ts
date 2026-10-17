export interface CharacterProject {
  id: string; name: string; franchise: string; variant: string; status: string;
  notes: string; direction: string; archived: boolean; revision: number;
  created_at: string; updated_at: string;
}
export interface Identity { name: string; franchise: string; variant: string; fictional_confirmed: true }
export interface Capability { available: boolean; configured?: boolean; phase: number; provider?: string }
export type Capabilities = Record<'research' | 'references' | 'generation' | 'captions' | 'publishing' | 'metrics', Capability>

export async function request<T>(path: string, method = 'GET', data?: unknown): Promise<T> {
  const response = await fetch('/api' + path, { method,
    headers: { 'Content-Type': 'application/json', 'X-Variance-Client': 'studio' },
    body: data === undefined ? undefined : JSON.stringify(data),
  })
  if (!response.ok) {
    const error = await response.json().catch(() => null)
    const detail = error?.detail
    throw new Error(typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((e: { msg: string }) => e.msg).join('. ') : `Request failed (${response.status}). Please try again.`)
  }
  return response.json() as Promise<T>
}
export const api = {
  health: () => request<{ status: string }>('/health'),
  capabilities: () => request<Capabilities>('/capabilities'),
  projects: (archived = false) => request<CharacterProject[]>(`/characters?archived=${archived}`),
  project: (id: string) => request<CharacterProject>(`/characters/${id}`),
  create: (identity: Identity) => request<CharacterProject>('/characters', 'POST', identity),
  save: (p: CharacterProject, notes: string, direction: string) => request<CharacterProject>(`/characters/${p.id}`, 'PATCH', { revision: p.revision, notes, direction }),
  archive: (p: CharacterProject, archived: boolean) => request<CharacterProject>(`/characters/${p.id}/archive`, 'POST', { revision: p.revision, archived }),
}
