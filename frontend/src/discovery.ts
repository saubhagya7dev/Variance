import { request } from './api'

export interface Source { title: string; url: string }
export interface ResearchSnapshot {
  id: string; provider: string; created_at: string;
  brief: { text: string; visual_details: string; kind: string; sources: Source[];
    citations: { text: string; sources: number[] }[]; suggestions_html: string }
}
export interface Candidate { id: string; title: string; page_url: string; attribution: string; license: string }
export interface Reference extends Candidate { selected: boolean; width: number; height: number; source_url: string }
const base = (id: string) => `/characters/${id}`
export const discovery = {
  research: (id: string) => request<ResearchSnapshot[]>(base(id) + '/research'),
  runResearch: (id: string, provider: 'wikipedia' | 'gemini') => request<ResearchSnapshot>(base(id) + `/research?provider=${provider}`, 'POST'),
  candidates: (id: string) => request<Candidate[]>(base(id) + '/candidates'),
  search: (id: string, query: string) => request<Candidate[]>(base(id) + '/candidates', 'POST', { query }),
  import: (id: string, candidate: string) => request<Reference>(base(id) + `/candidates/${candidate}/import`, 'POST'),
  references: (id: string) => request<Reference[]>(base(id) + '/references'),
  select: (id: string, ref: string, selected: boolean) => request<Reference>(base(id) + `/references/${ref}`, 'PATCH', { selected }),
  remove: (id: string, ref: string) => request(base(id) + `/references/${ref}`, 'DELETE'),
  image: (id: string, ref: string) => '/api' + base(id) + `/references/${ref}/image`,
  thumbnail: (id: string, ref: string) => '/api' + base(id) + `/candidates/${ref}/thumbnail`,
  async upload(id: string, file: File): Promise<Reference> {
    if (file.size > 8 * 1024 * 1024) throw new Error('Choose an image no larger than 8 MB.')
    const response = await fetch('/api' + base(id) + '/references/upload?title=' + encodeURIComponent(file.name.slice(0, 160)), {
      method: 'POST', headers: { 'X-Variance-Client': 'studio', 'Content-Type': 'application/octet-stream' }, body: file,
    })
    const body = await response.json()
    if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'Upload failed. Please try again.')
    return body
  },
}
