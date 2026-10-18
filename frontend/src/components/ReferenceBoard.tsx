import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Image, Layers3, Search, Upload, X } from 'lucide-react'
import type { CharacterProject } from '../api'
import { discovery } from '../discovery'

function Preview({ src, title }: { src: string; title: string }) {
  const [failed, setFailed] = useState(false)
  return failed ? <div className="image-fallback"><Image size={24} /><span>Preview unavailable</span></div> : <img src={src} alt={title} loading="lazy" onError={() => setFailed(true)} />
}

export default function ReferenceBoard({ project, direction }: { project: CharacterProject; direction: () => void }) {
  const client = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState(`${project.name} ${project.franchise}`.slice(0, 200))
  const [view, setView] = useState<'search' | 'library'>('library')
  const [notice, setNotice] = useState('')
  const candidates = useQuery({ queryKey: ['candidates', project.id], queryFn: () => discovery.candidates(project.id), retry: false })
  const refs = useQuery({ queryKey: ['references', project.id], queryFn: () => discovery.references(project.id) })
  const search = useMutation({ mutationFn: () => discovery.search(project.id, query), onSuccess: rows => {
    client.setQueryData(['candidates', project.id], rows); setView('search'); setNotice(`${rows.length} Commons results. Check that each matches your character.`)
  } })
  const change = useMutation({ mutationFn: async (action: { kind: 'import' | 'select' | 'remove'; id: string; selected?: boolean }) => {
    if (action.kind === 'import') return discovery.import(project.id, action.id)
    if (action.kind === 'remove') return discovery.remove(project.id, action.id)
    return discovery.select(project.id, action.id, !!action.selected)
  }, onSuccess: (_, action) => { void client.invalidateQueries({ queryKey: ['references', project.id] }); setNotice(action.kind === 'import' ? 'Reference imported. Open Your references to select it.' : action.kind === 'remove' ? 'Reference removed. Reimport it to restore it.' : 'Selection saved.') } })
  const upload = useMutation({ mutationFn: (file: File) => discovery.upload(project.id, file), onSuccess: () => {
    void client.invalidateQueries({ queryKey: ['references', project.id] }); setView('library'); setNotice('Reference saved locally. Duplicate images are combined.')
  } })
  const selected = refs.data?.filter(r => r.selected) ?? []
  const busy = search.isPending || change.isPending || upload.isPending
  const error = search.error ?? change.error ?? upload.error ?? refs.error ?? candidates.error
  return <><section className="panel references-panel" aria-labelledby="references-heading"><div className="panel-heading"><div><span className="panel-icon"><Image size={17} /></span><h2 id="references-heading">Visual references</h2><span className="count-badge">{refs.data?.length ?? 0}</span></div><button className="secondary small" disabled={busy} onClick={() => fileRef.current?.click()}><Upload size={13} />Upload</button><input ref={fileRef} aria-label="Upload reference image" className="visually-hidden" type="file" accept="image/png,image/jpeg,image/webp" onChange={e => { const file = e.target.files?.[0]; if (file) upload.mutate(file); e.target.value = '' }} /></div>
      <form className="reference-search-form" onSubmit={e => { e.preventDefault(); search.mutate() }}><input aria-label="Search Wikimedia Commons" maxLength={200} value={query} onChange={e => setQuery(e.target.value)} placeholder="Search free reference images…" /><button className="secondary small" disabled={busy || !query.trim()}><Search size={14} />{search.isPending ? 'Searching…' : 'Search'}</button></form>
      <p className="reference-explainer">Wikimedia Commons · no key needed. Results may include cosplay or unrelated versions. Upload PNG, JPEG or WebP files up to 8 MB.</p>
      <div className="reference-view-tabs"><button className={view === 'library' ? 'active' : ''} aria-pressed={view === 'library'} onClick={() => setView('library')}>Your references ({refs.data?.length ?? 0})</button><button className={view === 'search' ? 'active' : ''} aria-pressed={view === 'search'} onClick={() => setView('search')}>Search results ({candidates.data?.length ?? 0})</button></div>
      {error && <p role="alert" className="discovery-message error-message">{error.message}</p>}
      {notice && <p role="status" className="discovery-message">{notice}</p>}
      {busy && <p role="status" className="discovery-message">{upload.isPending ? 'Validating and saving your image…' : change.isPending ? 'Saving reference…' : 'Searching Commons…'}</p>}
      {refs.isPending && <p className="discovery-message">Loading references…</p>}
      {view === 'library' ? <div className="reference-cards">{refs.data?.map(ref => <article className={`reference-card ${ref.selected ? 'selected' : ''}`} key={ref.id}><Preview src={discovery.image(project.id, ref.id)} title={ref.title} /><div><h3>{ref.title}</h3><p>{ref.width} × {ref.height} · {ref.license}</p>{ref.attribution && <p>{ref.attribution}</p>}{ref.page_url && <a href={ref.page_url} target="_blank" rel="noopener noreferrer">Source & licence</a>}<div className="reference-card-actions"><button className="secondary small" aria-pressed={ref.selected} disabled={busy} onClick={() => change.mutate({ kind: 'select', id: ref.id, selected: !ref.selected })}><Check size={12} />{ref.selected ? 'Selected' : 'Select'}</button><button className="icon-button" disabled={busy} aria-label={`Remove ${ref.title}`} onClick={() => change.mutate({ kind: 'remove', id: ref.id })}><X size={14} /></button></div></div></article>)}</div> : <div className="reference-cards">{candidates.data?.map(candidate => <article className="reference-card" key={candidate.id}><Preview src={discovery.thumbnail(project.id, candidate.id)} title={candidate.title} /><div><h3>{candidate.title}</h3><p>{candidate.license} · {candidate.attribution}</p><a href={candidate.page_url} target="_blank" rel="noopener noreferrer">Inspect source & licence</a><button className="secondary small" disabled={busy} onClick={() => change.mutate({ kind: 'import', id: candidate.id })}>Import reference</button></div></article>)}</div>}
      {!(view === 'library' ? refs.data?.length : candidates.data?.length) && !busy && <div className="panel-empty"><Image size={26} /><h3>{view === 'library' ? 'A place for your references.' : 'No matching images yet.'}</h3><p>{view === 'library' ? 'Search Commons or upload a local image, then select the references you want to use.' : 'Try a broader character name or upload an image. Commons does not cover every fictional character.'}</p></div>}
    </section><section className="selection-tray live-selection" aria-label="Selected reference images"><div className="tray-title"><span className="tray-icon"><Layers3 size={20} /></span><div><h3>Selected references <span>{selected.length}</span></h3><p>Saved with this character project.</p></div></div><div className="selected-thumbnails">{selected.map(ref => <button key={ref.id} disabled={busy} title={`Deselect ${ref.title}`} aria-label={`Deselect ${ref.title}`} onClick={() => change.mutate({ kind: 'select', id: ref.id, selected: false })}><img src={discovery.image(project.id, ref.id)} alt={ref.title} /><X size={12} /></button>)}</div><button className="primary" disabled={!selected.length} onClick={direction}>Shape creative direction</button></section></>
}
