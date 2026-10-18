import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Download, Image, Upload, WandSparkles } from 'lucide-react'
import { api } from '../api'
import type { CharacterProject } from '../api'
import { creation } from '../creation'
import type { Artwork, Batch } from '../creation'

export default function ImageStudio({ project, direction }: { project: CharacterProject; direction: () => void }) {
  const cache = useQueryClient()
  const [mode, setMode] = useState<'manual' | 'api'>('manual')
  const [promptId, setPromptId] = useState('')
  const [count, setCount] = useState(2)
  const [batchId, setBatchId] = useState('')
  const requestKey = useRef({ settings: '', key: '' })
  const prompts = useQuery({ queryKey: ['prompts', project.id], queryFn: () => creation.prompts(project.id) })
  const caps = useQuery({ queryKey: ['capabilities'], queryFn: api.capabilities })
  const batches = useQuery({ queryKey: ['batches', project.id], queryFn: () => creation.batches(project.id), refetchInterval: q => q.state.data?.some(b => ['queued', 'running'].includes(b.status)) ? 2000 : false })
  const chosen = promptId || prompts.data?.[0]?.id || ''
  const batch = batches.data?.find(b => b.id === batchId) ?? batches.data?.[0]
  const create = useMutation({ mutationFn: () => {
    const settings = JSON.stringify([chosen, mode, count])
    if (requestKey.current.settings !== settings) requestKey.current = { settings, key: crypto.randomUUID() }
    return creation.batch(project.id, chosen, mode, count, requestKey.current.key)
  }, onSuccess: data => { setBatchId(data.id); requestKey.current = { settings: '', key: '' }; void cache.invalidateQueries({ queryKey: ['batches', project.id] }) } })
  return <div className="creation-page"><div className="page-heading"><div><span className="eyebrow">03 / IMAGE STUDIO</span><h1>Explore the possibilities.</h1><p>{project.name} · Two ways to create. One place to review.</p></div><button className="secondary" onClick={direction}>Edit creative direction</button></div>
    <div className="generation-options" role="group" aria-label="Generation route">{(['manual', 'api'] as const).map(m => <button key={m} className={`generation-option ${mode === m ? 'selected' : ''}`} aria-pressed={mode === m} disabled={create.isPending} onClick={() => setMode(m)}>{m === 'manual' ? <Upload size={22} /> : <WandSparkles size={22} />}<span className="eyebrow">{m === 'manual' ? '01 / YOUR FAVORITE TOOL' : '02 / CONNECTED CREATION'}</span><h2>{m === 'manual' ? 'Manual generation' : 'API generation'}</h2><p>{m === 'manual' ? 'Take your prompt and references to any image tool. Import the results here.' : 'Generate with FLUX.2 klein through Cloudflare Workers AI. Free-plan credentials required.'}</p><span className="status-chip">{m === 'manual' ? 'Ready · no API key' : caps.data?.generation.available ? 'Configured · free-plan account' : 'Free tier · setup required'}</span></button>)}</div>
    {mode === 'api' && <div className="panel api-setup"><p>Your saved prompt and up to four reference images will be sent to Cloudflare. Free-plan quota applies; no automatic retries or paid fallback.</p>{!caps.data?.generation.available && <p>In your local .env, set <code>CLOUDFLARE_ACCOUNT_ID</code>, <code>CLOUDFLARE_API_TOKEN</code>, and <code>CLOUDFLARE_FREE_PLAN_CONFIRMED=true</code> after confirming the account uses Workers Free. Restart the backend. Never paste tokens into this workspace.</p>}<a href="https://developers.cloudflare.com/workers-ai/platform/pricing/" target="_blank" rel="noreferrer">Free allocation and account plans ↗</a><button className="text-button" onClick={() => void caps.refetch()}>Refresh connection</button></div>}
    <section className="panel batch-controls"><label>Saved prompt<select value={chosen} disabled={create.isPending} onChange={e => setPromptId(e.target.value)}><option value="">Choose a prompt</option>{prompts.data?.map(p => <option key={p.id} value={p.id}>v{p.version} · {p.direction.style} · {p.context.references.length} references</option>)}</select></label><label>Variations<select value={count} disabled={create.isPending} onChange={e => setCount(Number(e.target.value))}>{[1, 2, 3, 4].map(n => <option key={n}>{n}</option>)}</select></label><button className="primary" disabled={!chosen || create.isPending || (mode === 'api' && !caps.data?.generation.available)} onClick={() => create.mutate()}>{create.isPending ? 'Creating batch…' : mode === 'manual' ? 'Create manual batch' : 'Generate batch'}</button>{prompts.data?.length === 0 && <p>Save a prompt in Creative direction first.</p>}</section>
    {(create.error || prompts.error || batches.error || caps.error) && <p role="alert" className="error-message">{(create.error || prompts.error || batches.error || caps.error)?.message}<button className="text-button" onClick={() => { void prompts.refetch(); void batches.refetch(); void caps.refetch() }}>Reload</button></p>}
    <div className="batch-heading"><h2>Your image studies</h2><label>Batch history<select value={batch?.id ?? ''} onChange={e => setBatchId(e.target.value)}><option value="">Choose a batch</option>{batches.data?.map((b, i) => <option key={b.id} value={b.id}>Study {batches.data.length - i} · {b.mode} · {b.status.replaceAll('_', ' ')} · {b.id.slice(0, 6)}</option>)}</select></label></div>
    {batch ? <BatchReview key={batch.id} projectId={project.id} batch={batch} /> : <section className="panel prompt-empty"><Image size={36} strokeWidth={1} /><h3>Your next perspective belongs here.</h3><p>Create a batch to collect and compare your artwork.</p></section>}
  </div>
}
function BatchReview({ projectId, batch }: { projectId: string; batch: Batch }) {
  const cache = useQueryClient()
  const arts = useQuery({ queryKey: ['artwork', projectId, batch.id, batch.status], queryFn: () => creation.artwork(projectId, batch.id), refetchInterval: ['queued', 'running'].includes(batch.status) ? 2000 : false })
  const [compare, setCompare] = useState(false)
  const upload = useMutation({ mutationFn: (file: File) => creation.upload(projectId, batch.id, file), onSuccess: () => { void cache.invalidateQueries({ queryKey: ['artwork', projectId, batch.id] }); void cache.invalidateQueries({ queryKey: ['batches', projectId] }) } })
  return <section className="panel batch-review"><div className="review-toolbar"><span className="status-chip">{batch.mode} · {batch.status.replaceAll('_', ' ')} · {arts.data?.length ?? 0}/{batch.target_count}</span><a className="secondary" href={creation.pack(projectId, batch.prompt_id)}><Download size={14} />Prompt + references</a>{batch.mode === 'manual' && <label className="secondary upload-result"><Upload size={14} />{upload.isPending ? 'Importing…' : 'Import result'}<input aria-label="Import generated result" type="file" accept="image/png,image/jpeg,image/webp" disabled={upload.isPending || !arts.data || arts.data.length >= batch.target_count} onChange={e => { const file = e.target.files?.[0]; if (file) upload.mutate(file); e.target.value = '' }} /></label>}<button className="text-button" aria-pressed={compare} onClick={() => setCompare(!compare)}>{compare ? 'Show review controls' : 'Compare images'}</button></div>
    {batch.mode === 'manual' && <p className="creation-note">Download the pack, generate in your chosen tool, then import each result as PNG, JPEG or WebP (up to 8 MB). Exporting a pack does not generate images.</p>}
    {batch.error && <p role="alert" className="error-message">{batch.error}</p>}{(upload.error || arts.error) && <p role="alert" className="error-message">{(upload.error || arts.error)?.message}<button onClick={() => void arts.refetch()}>Reload images</button></p>}
    {['queued', 'running'].includes(batch.status) && <p role="status">Generation {batch.status}. You can leave this page while the backend stays open.</p>}
    <div className={`artwork-grid ${compare ? 'comparing' : ''}`}>{arts.data?.map(art => <ArtCard key={`${art.id}-${art.revision}`} projectId={projectId} batchId={batch.id} art={art} compare={compare} />)}</div>
  </section>
}
function ArtCard({ projectId, batchId, art, compare }: { projectId: string; batchId: string; art: Artwork; compare: boolean }) {
  const cache = useQueryClient()
  const [note, setNote] = useState(art.review_note)
  const review = useMutation({ mutationFn: (decision: Artwork['decision']) => creation.review(projectId, art, decision, note), onSuccess: () => { void cache.invalidateQueries({ queryKey: ['artwork', projectId, batchId] }); void cache.invalidateQueries({ queryKey: ['batches', projectId] }) } })
  return <article className={`artwork-card ${art.decision}`}><a href={creation.image(projectId, art.id)} target="_blank" rel="noreferrer" aria-label={`Inspect ${art.title}`}><img src={creation.image(projectId, art.id)} alt={art.title} /></a><div><h3>{art.title}</h3><span className="status-chip">{art.decision} · {art.width} × {art.height}</span>{!compare && <><label>Review notes<textarea value={note} maxLength={2000} onChange={e => setNote(e.target.value)} placeholder="Identity, anatomy, composition, and visual quality…" /></label><div className="creation-actions">{(['approved', 'rejected', 'pending'] as const).map(d => <button className={d === 'approved' ? 'primary' : 'secondary'} key={d} disabled={review.isPending} onClick={() => review.mutate(d)}>{d === 'approved' ? 'Approve' : d === 'rejected' ? 'Reject' : 'Reset'}</button>)}<button className="text-button" disabled={review.isPending} onClick={() => review.mutate(art.decision)}>Save note</button></div></>}{review.error && <p role="alert" className="error-message">{review.error.message}<button onClick={() => void cache.invalidateQueries({ queryKey: ['artwork', projectId, batchId] })}>Reload review</button></p>}<a className="text-button" href={`${creation.image(projectId, art.id)}?download=true`}>Download image<Download size={13} /></a></div></article>
}
