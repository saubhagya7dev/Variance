import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, Check, Download, Feather } from 'lucide-react'
import { api } from '../api'
import type { CharacterProject } from '../api'
import { creation } from '../creation'
import { posts } from '../posts'
import type { Post, PostContent } from '../posts'
import './captions.css'

export default function CaptionStudio({ project, images }: { project: CharacterProject; images: () => void }) {
  const cache = useQueryClient()
  const [artId, setArtId] = useState('')
  const [selected, setSelected] = useState('')
  const [platform, setPlatform] = useState('instagram')
  const [tone, setTone] = useState('reflective')
  const [provider, setProvider] = useState('local')
  const arts = useQuery({ queryKey: ['approved-artwork', project.id], queryFn: () => posts.images(project.id) })
  const drafts = useQuery({ queryKey: ['posts', project.id], queryFn: () => posts.list(project.id) })
  const caps = useQuery({ queryKey: ['capabilities'], queryFn: api.capabilities })
  function saved(row: Post) { setSelected(row.id); void cache.invalidateQueries({ queryKey: ['posts', project.id] }) }
  const create = useMutation({ mutationFn: () => posts.create(project.id, artId || arts.data?.[0]?.id || '', platform, tone, provider), onSuccess: saved })
  const row = drafts.data?.find(p => p.id === selected) ?? drafts.data?.[0]
  return <div className="creation-page caption-studio">
    <div className="page-heading"><div><span className="eyebrow">04 / CAPTIONS & MANUAL POSTING</span><h1>Give the artwork a voice.</h1><p>{project.name} · Shape the words. Review the details. Share when ready.</p></div><button className="secondary" onClick={images}>Review artwork<ArrowRight size={14} /></button></div>
    <section className="panel caption-start"><div><Feather size={21} /><h2>Start with approved artwork.</h2><p>Local templates are free and use identity and creative direction. Optional Gemini drafts from the saved research; factual accuracy still needs your review.</p></div>
      <fieldset disabled={create.isPending} className="caption-controls"><label>Approved artwork<select value={artId || arts.data?.[0]?.id || ''} onChange={e => setArtId(e.target.value)}><option value="">Choose artwork</option>{arts.data?.map(a => <option key={a.id} value={a.id}>{a.title} · {a.id.slice(0, 6)}</option>)}</select></label><label>Platform<select value={platform} onChange={e => setPlatform(e.target.value)}><option value="instagram">Instagram</option><option value="facebook">Facebook</option></select></label><label>Tone<select value={tone} onChange={e => setTone(e.target.value)}>{['reflective', 'playful', 'minimal'].map(t => <option key={t}>{t}</option>)}</select></label><label>Drafting method<select value={provider} onChange={e => setProvider(e.target.value)}><option value="local">Local templates · no key</option><option value="gemini" disabled={!caps.data?.captions.configured}>Gemini · {caps.data?.captions.configured ? 'configured' : 'setup required'}</option></select></label></fieldset>
      {provider === 'gemini' && <p>Identity, style and saved research will be sent to Google. Your image is not sent. Use a free-tier project without billing enabled.</p>}
      <button className="primary" disabled={create.isPending || !arts.data?.length} onClick={() => create.mutate()}>{create.isPending ? 'Drafting…' : 'Create caption draft'}</button>{arts.data?.length === 0 && <p>Approve an image in Image studio to start.</p>}
    </section>
    {(arts.error || drafts.error || caps.error || create.error) && <p role="alert" className="error-message">{(arts.error || drafts.error || caps.error || create.error)?.message}<button className="text-button" onClick={() => { void arts.refetch(); void drafts.refetch(); void caps.refetch() }}>Reload</button></p>}
    <div className="batch-heading"><h2>Your post versions</h2><label>Saved post<select value={row?.id ?? ''} onChange={e => setSelected(e.target.value)}><option value="">Choose a version</option>{drafts.data?.map(p => <option key={p.id} value={p.id}>{p.platform} · artwork {p.artwork_id.slice(0, 6)} · v{p.version} · {p.status}</option>)}</select></label></div>
    {row ? <PostEditor key={`${row.id}-${row.revision}`} row={row} projectId={project.id} saved={saved} /> : <div className="panel prompt-empty"><Feather size={34} /><h3>A thoughtful caption starts here.</h3><p>Choose approved artwork and create your first draft.</p></div>}
  </div>
}

function PostEditor({ row, projectId, saved }: { row: Post; projectId: string; saved: (row: Post) => void }) {
  const [caption, setCaption] = useState(row.caption)
  const [tags, setTags] = useState(row.hashtags.map(t => '#' + t).join(' '))
  const [alt, setAlt] = useState(row.alt_text)
  const [disclosure, setDisclosure] = useState(row.disclosure)
  const [reviewed, setReviewed] = useState(false)
  const [copied, setCopied] = useState('')
  const [url, setUrl] = useState('')
  const [postedAt, setPostedAt] = useState('')
  const [published, setPublished] = useState(false)
  const normalizedTags = tags.trim().split(/\s+/).filter(Boolean).map(t => t.replace(/^#/, ''))
  const content: PostContent = { caption, hashtags: normalizedTags, alt_text: alt, disclosure }
  const dirty = caption !== row.caption || alt !== row.alt_text || disclosure !== row.disclosure || JSON.stringify(normalizedTags) !== JSON.stringify(row.hashtags)
  const save = useMutation({ mutationFn: () => posts.edit(projectId, row, content), onSuccess: saved })
  const approve = useMutation({ mutationFn: () => posts.approve(projectId, row), onSuccess: saved })
  const record = useMutation({ mutationFn: () => posts.publication(projectId, row, url, new Date(postedAt).toISOString()), onSuccess: saved })
  const busy = save.isPending || approve.isPending || record.isPending
  const preview = [caption, disclosure, normalizedTags.map(t => '#' + t).join(' ')].filter(Boolean).join('\n\n')
  const valid = !row.validation.errors.length
  const exportable = !dirty && valid && ['approved', 'published'].includes(row.status)
  async function copy() { try { await navigator.clipboard.writeText(row.post_text); setCopied('Caption copied.') } catch { setCopied('Clipboard unavailable. Use the exported caption.txt instead.') } }
  return <div className="creation-columns caption-columns"><section className="panel creation-panel"><span className="eyebrow">EDIT / VERSION {row.version} · {row.provider === 'local' ? 'LOCAL TEMPLATE' : row.provider === 'gemini' ? 'GEMINI DRAFT' : 'USER EDITED'}</span><h2>The words are yours.</h2>
    <fieldset disabled={busy} className="direction-fields"><label>Caption<textarea rows={7} maxLength={5000} value={caption} onChange={e => setCaption(e.target.value)} /></label><label>Hashtags<textarea rows={2} value={tags} maxLength={1300} onChange={e => setTags(e.target.value)} /></label><label>Alt text · describe what is actually visible<textarea rows={3} maxLength={1000} value={alt} onChange={e => setAlt(e.target.value)} placeholder="Inspect the image and describe its subject, composition and relevant visual details." /></label><label>Disclosure<textarea rows={2} maxLength={300} value={disclosure} onChange={e => setDisclosure(e.target.value)} /></label></fieldset>
    <button className="primary" disabled={busy || !caption.trim() || !disclosure.trim()} onClick={() => save.mutate()}>{save.isPending ? 'Saving…' : 'Save as new version'}</button><p className="creation-note">Each save creates a draft. Earlier versions and approval records stay intact. Unsaved changes are lost when switching versions or leaving this page.</p>
    <details className="caption-evidence"><summary>Research & identity behind this image</summary><p>{row.context.identity.name} · {row.context.identity.franchise} · {row.context.identity.variant}</p><p>Creative direction: {row.context.style}</p>{row.context.research ? <><pre>{row.context.research.brief.text}</pre>{row.context.research.brief.sources.map((s, i) => <a key={i} href={s.url} target="_blank" rel="noreferrer">{s.title} ↗</a>)}</> : <p>No research was frozen with this artwork’s prompt. Keep factual claims limited to confirmed identity, or verify them yourself.</p>}<p>Source context is provided for review. Edited or AI-drafted claims are not automatically verified.</p></details>
    {(save.error || approve.error || record.error) && <p className="error-message" role="alert">{(save.error || approve.error || record.error)?.message}<button className="text-button" onClick={() => saved(row)}>Reload saved state</button></p>}
  </section><div><section className="panel post-preview"><div className="preview-account"><span className="profile-avatar">V</span><div><strong>Your account</strong><small>{row.platform} · approximate preview</small></div><span className="status-chip">{row.status === 'published' ? 'Publication recorded' : row.status}</span></div><a href={creation.image(projectId, row.artwork_id)} target="_blank" rel="noreferrer"><img src={creation.image(projectId, row.artwork_id)} alt={alt || 'Artwork awaiting an accessible description'} /></a><div className="post-preview-copy"><p>{preview}</p><span className={Array.from(preview).length > row.validation.limit ? 'error-message' : 'creation-note'}>{Array.from(preview).length} / {row.validation.limit} studio character limit</span></div></section>
    <section className="panel creation-panel post-approval"><span className="eyebrow">REVIEW BEFORE SHARING</span><h2>{row.status === 'published' ? 'Your publication record.' : 'One final look.'}</h2><p className="creation-note">{row.validation.note} Studio policy: at most five hashtags. No post is sent from this workspace.</p>
      {dirty ? <p role="status">Save a new version to validate and approve these changes.</p> : row.validation.errors.map(e => <p key={e} className="error-message">{e}</p>)}
      {row.status === 'draft' && <><label className="post-check"><input type="checkbox" checked={reviewed} disabled={busy || dirty} onChange={e => setReviewed(e.target.checked)} /><span>I reviewed the factual claims, image, alt text and disclosure.</span></label><button className="primary" disabled={busy || dirty || !reviewed || !valid} onClick={() => approve.mutate()}><Check size={14} />Approve this version</button></>}
      {exportable && <div className="creation-actions"><a className="secondary" href={posts.export(projectId, row)}><Download size={14} />Export posting pack</a><button className="secondary" onClick={() => void copy()}>Copy approved caption</button></div>}{copied && <p role="status">{copied}</p>}
      {row.status === 'approved' && <details className="publication-form"><summary>Already posted manually? Record it here.</summary><p>This records your report locally. Variance does not publish or verify the remote post.</p><label>Published post URL<input type="url" value={url} placeholder={`https://www.${row.platform}.com/…`} onChange={e => setUrl(e.target.value)} /></label><label>Actual posting time · your local timezone<input type="datetime-local" value={postedAt} onChange={e => setPostedAt(e.target.value)} /></label><label className="post-check"><input type="checkbox" checked={published} onChange={e => setPublished(e.target.checked)} /><span>I published this exact version myself.</span></label><button className="secondary" disabled={busy || !exportable || !published || !url || !postedAt || !Number.isFinite(new Date(postedAt).getTime())} onClick={() => record.mutate()}>Record manual publication</button></details>}
      {row.status === 'published' && <p><a href={row.publication_url} target="_blank" rel="noreferrer">Open recorded post ↗</a><br />Reported posting time: {new Date(row.published_at).toLocaleString()}<br />Self-reported · not independently verified.</p>}
    </section></div></div>
}
