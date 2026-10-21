import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Check, CircleAlert, Send } from 'lucide-react'
import { request } from '../api'
import type { CharacterProject } from '../api'
import { posts } from '../posts'
import SocialConnections from './SocialConnections'
import LivePublishing, { DeliveryHistory } from './DeliveryStudio'

interface Preflight {
  revision: number; content_ready: boolean; message: string; post_text: string; alt_text: string;
  checks: { label: string; passed: boolean }[]; errors: string[]; blockers: string[];
}

export default function PublishingStudio({ project, captions }: { project: CharacterProject; captions: () => void }) {
  const [selected, setSelected] = useState('')
  const query = useQuery({ queryKey: ['posts', project.id], queryFn: () => posts.list(project.id) })
  const approved = query.data?.filter(p => p.status === 'approved') ?? []
  const post = approved.find(p => p.id === selected) ?? approved[0]
  const run = useMutation({ mutationFn: ({ id, revision }: { id: string; revision: number }) => request<Preflight>(`/characters/${project.id}/posts/${id}/preflight`, 'POST', { revision }) })
  const result = run.data && run.variables?.id === post?.id && run.data.revision === post?.revision ? run.data : undefined
  return <div className="settings-page">
    <div className="page-heading"><div><span className="eyebrow">PHASE 5 / PUBLISHING</span><h1>Ready for your audience.</h1><p>Check your approved post before connecting a destination.</p></div><span className="status-chip neutral">Review & publish</span></div>
    <SocialConnections />
    <section className="panel creation-panel">
      <Send size={24} /><h2>Post preflight</h2><p>Review an approved Instagram, Facebook, Threads or X post. Live publishing requires configured credentials and explicit confirmation.</p>
      {query.isPending ? <p role="status">Loading approved posts…</p> : query.isError ? <p role="alert">{query.error.message}<button className="text-button" onClick={() => void query.refetch()}>Retry</button></p> : !post ? <><p>Approve a post in Captions & tags to start a dry run.</p><button className="secondary" onClick={captions}>Open captions & tags</button></> : <>
        <label className="snapshot-picker">Approved post<select value={post.id} disabled={run.isPending} onChange={e => { setSelected(e.target.value); run.reset() }}>{approved.map(p => <option key={p.id} value={p.id}>{p.platform} · version {p.version} · {p.caption.slice(0, 55)}</option>)}</select></label>
        <p className="research-prose">{post.post_text}</p><p><strong>Alt text:</strong> {post.alt_text}</p>
        <button className="primary" disabled={run.isPending} onClick={() => run.mutate({ id: post.id, revision: post.revision })}>{run.isPending ? 'Checking…' : 'Run local checks'}</button>
        {run.isError && <p role="alert" className="error-message">{run.error.message}</p>}
        {result && <div aria-live="polite"><h3>{result.content_ready ? 'Content checks passed' : 'Review needed'}</h3>{result.checks.map(c => <p key={c.label}>{c.passed ? <Check size={15} /> : <CircleAlert size={15} />} {c.label}</p>)}{result.errors.map(e => <p key={e}>{e}</p>)}{result.blockers.map(b => <p key={b} className="discovery-message">{b}</p>)}<p>{result.message}</p></div>}
        <LivePublishing key={`${post.id}-${post.revision}`} projectId={project.id} post={post} />
      </>}
    </section>
    <DeliveryHistory projectId={project.id} />
  </div>
}
