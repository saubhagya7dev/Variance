import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { request } from '../api'
import type { Post } from '../posts'

interface Sample { id: string; window: string; due_at: string; status: string; values: Record<string, number>; error: string; collected_at: string }
interface Delivery { id: string; post_id: string; platform: string; account_id: string; account_name: string; status: string; remote_id: string; created_at: string; error: string; samples: Sample[] }

function Observations({ deliveries }: { deliveries: Delivery[] }) {
  const groups = new Map<string, { delivery: Delivery; sample: Sample; likes: number }[]>()
  for (const delivery of deliveries) for (const sample of delivery.samples) {
    const likes = sample.values[delivery.platform === 'x' ? 'like_count' : 'likes']
    const lateness = new Date(sample.collected_at).getTime() - new Date(sample.due_at).getTime()
    if (sample.status !== 'collected' || likes === undefined || lateness < 0 || lateness > 15 * 60 * 1000) continue
    const key = `${delivery.platform}:${delivery.account_id}:${sample.window}`
    groups.set(key, [...(groups.get(key) || []), { delivery, sample, likes }])
  }
  const comparable = [...groups.entries()].filter(([, entries]) => entries.length >= 3)
  return <div className="delivery-form"><h3>What to explore next</h3>{comparable.length === 0 ? <p>Collect at least three snapshots for the same account and time window, each within 15 minutes of its deadline, to unlock a comparison.</p> : comparable.map(([key, entries]) => {
    const ranked = [...entries].sort((a, b) => b.likes - a.likes)
    const highest = ranked[0]
    const median = [...entries].sort((a, b) => a.likes - b.likes)[Math.floor(entries.length / 2)].likes
    return <p key={key}>{highest.delivery.platform} · {highest.delivery.account_name} · {highest.sample.window}: among {entries.length} comparable snapshots, post <code>{highest.delivery.remote_id}</code> received {highest.likes} likes; the middle observation was {median}. {highest.likes > median ? 'Review its image and caption as a starting point for your next experiment.' : 'There is no clear lead in likes yet; keep exploring.'}</p>
  })}<p className="creation-note">Observations use native likes from this project. Audience changes, posting time and other factors can explain differences; this does not prove that a style caused the result. Late or incomplete samples are excluded.</p></div>
}
export function DeliveryHistory({ projectId, performance = false }: { projectId: string; performance?: boolean }) {
  const client = useQueryClient()
  const query = useQuery({ queryKey: ['deliveries', projectId], queryFn: () => request<Delivery[]>(`/characters/${projectId}/posts/deliveries`), refetchInterval: 15000 })
  const [remote, setRemote] = useState<Record<string, string>>({})
  const action = useMutation({ mutationFn: ({ path, data }: { path: string; data?: unknown }) => request(path, 'POST', data), onSuccess: () => { void client.invalidateQueries({ queryKey: ['deliveries', projectId] }); void client.invalidateQueries({ queryKey: ['posts', projectId] }) } })
  return <section className="panel creation-panel"><span className="eyebrow">{performance ? 'PHASE 6 / PERFORMANCE' : 'DELIVERY JOURNAL'}</span><h2>{performance ? 'Measure what resonates.' : 'Every attempt, accounted for.'}</h2>
    <p>{performance ? 'Native counts are collected at 1 hour, 24 hours and 7 days while the server runs and METRICS_ENABLED=true. Late collections show their actual time. Missing counts are unavailable, never zero. Manual publication records are not tracked here.' : 'Uncertain results are never resent automatically. Check the native account before taking further action.'}</p>
    {query.isPending && <p>Loading delivery records…</p>}{query.isError && <p role="alert">{query.error.message}</p>}{action.isError && <p role="alert">{action.error.message}</p>}
    {query.data?.length === 0 && <p>No connected publications yet. Publish an approved post to begin tracking.</p>}
    {query.data?.map(d => <article className="delivery-card" key={d.id}><h3>{d.platform} · {d.account_name}</h3><p><span className="status-chip neutral">{d.status}</span> · {new Date(d.created_at).toLocaleString()}</p>{d.remote_id && <p>Remote post ID: <code>{d.remote_id}</code></p>}{d.error && <p role="status">{d.error}</p>}
      {!performance && d.status === 'uncertain' && <div className="delivery-form"><label>Remote post ID<input value={remote[d.id] || ''} onChange={e => setRemote({ ...remote, [d.id]: e.target.value })} placeholder="ID from the native platform" /></label><button className="secondary" disabled={action.isPending || !remote[d.id]} onClick={() => action.mutate({ path: `/characters/${projectId}/posts/${d.post_id}/reconcile`, data: { remote_id: remote[d.id] } })}>Verify remote publication</button><p>Verification checks the author and exact text. If the provider altered the text, the attempt stays unresolved. Reconciled posts start measurement windows at verification time.</p></div>}
      {performance && <div className="metric-grid">{d.samples.map(s => <div key={s.id} className="metric-card"><h4>{s.window} snapshot · {s.status}</h4><p>Due {new Date(s.due_at).toLocaleString()}</p>{s.collected_at && <p>Attempted {new Date(s.collected_at).toLocaleString()}</p>}<dl>{Object.entries(s.values).map(([k, v]) => <div key={k}><dt>{k.replaceAll('_', ' ')}</dt><dd>{v.toLocaleString()}</dd></div>)}</dl>{s.error && <p>{s.error}</p>}{s.status === 'unavailable' && <button className="text-button" disabled={action.isPending} onClick={() => action.mutate({ path: `/characters/${projectId}/posts/metrics/${s.id}/retry` })}>Retry collection</button>}</div>)}</div>}
    </article>)}{performance && query.data && <Observations deliveries={query.data} />}
  </section>
}

export default function LivePublishing({ projectId, post }: { projectId: string; post: Post }) {
  const client = useQueryClient()
  const [url, setUrl] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const check = useMutation({ mutationFn: () => request<{ account_id: string; name: string }>(`/connections/${post.platform}/check`, 'POST') })
  const send = useMutation({ mutationFn: () => request<{ status: string }>(`/characters/${projectId}/posts/${post.id}/publish`, 'POST', { revision: post.revision, account_id: check.data?.account_id, confirmed: true, public_image_url: url }), onSuccess: () => { void client.invalidateQueries({ queryKey: ['posts', projectId] }); void client.invalidateQueries({ queryKey: ['deliveries', projectId] }) } })
  const caps = useQuery({ queryKey: ['publishing-capabilities'], queryFn: () => request<{ publishing: { available: boolean } }>('/capabilities') })
  return <div className="delivery-form"><h3>Publish this approved version</h3><p>Single-image publishing uses your configured account and counts against DAILY_POST_CAP. Enable PUBLISH_ENABLED in .env and restart when ready.</p>
    <a className="text-button" href={`/api/characters/${projectId}/posts/${post.id}/publish-image`} download>Download publication JPEG ↗</a>
    {['instagram', 'threads'].includes(post.platform) && <label>Public HTTPS image URL<input type="url" value={url} onChange={e => { setUrl(e.target.value); setConfirmed(false) }} placeholder="https://your-image-host/artwork.jpg" /><small>Upload the exact downloaded JPEG to your image host. Keep it accessible until publishing finishes. Do not expose the local studio server publicly.</small></label>}
    <button className="secondary" disabled={check.isPending || send.isPending} onClick={() => { setConfirmed(false); check.mutate() }}>Verify destination</button>
    {check.data && <><p>Destination: <strong>{check.data.name}</strong> · {check.data.account_id} · {post.platform}</p><label className="post-check"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} /><span>I reviewed this exact post and approve publishing it to this account now.</span></label></>}
    <button className="primary" disabled={!caps.data?.publishing.available || !confirmed || !check.data || send.isPending || check.isPending || (['instagram', 'threads'].includes(post.platform) && !url.trim())} onClick={() => send.mutate()}>{send.isPending ? 'Publishing…' : 'Publish now'}</button>
    {caps.isError && <p role="alert">Could not load publishing configuration. <button className="text-button" onClick={() => void caps.refetch()}>Retry</button></p>}
    {!caps.data?.publishing.available && <p>Live publishing is disabled.</p>}{(check.isError || send.isError) && <p role="alert">{check.error?.message || send.error?.message}</p>}
  </div>
}
