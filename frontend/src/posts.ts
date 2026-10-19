import { request } from './api'
import type { Artwork } from './creation'
export interface Post {
  id: string; artwork_id: string; version: number; revision: number; platform: string;
  tone: string; caption: string; hashtags: string[]; alt_text: string; disclosure: string;
  provider: string; status: string; post_text: string; publication_url: string; published_at: string;
  context: { identity: { name: string; franchise: string; variant: string }; style: string; research: null | { brief: { text: string; sources: { title: string; url: string }[] } } };
  validation: { errors: string[]; characters: number; limit: number; note: string };
}
export interface PostContent { caption: string; hashtags: string[]; alt_text: string; disclosure: string }
const base = (id: string) => `/characters/${id}`
export const posts = {
  list: (id: string) => request<Post[]>(`${base(id)}/posts`),
  images: (id: string) => request<Artwork[]>(`${base(id)}/approved-artwork`),
  create: (id: string, artwork_id: string, platform: string, tone: string, provider: string) => request<Post>(`${base(id)}/posts`, 'POST', { artwork_id, platform, tone, provider }),
  edit: (id: string, row: Post, content: PostContent) => request<Post>(`${base(id)}/posts/${row.id}/versions`, 'POST', { ...content, revision: row.revision }),
  approve: (id: string, row: Post) => request<Post>(`${base(id)}/posts/${row.id}/approve`, 'POST', { revision: row.revision, content_reviewed: true }),
  publication: (id: string, row: Post, url: string, published_at: string) => request<Post>(`${base(id)}/posts/${row.id}/publication`, 'POST', { revision: row.revision, url, published_at, manually_published: true }),
  export: (id: string, row: Post) => `/api${base(id)}/posts/${row.id}/export`,
}
