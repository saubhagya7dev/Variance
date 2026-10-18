import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, Download, Sparkles } from 'lucide-react'
import type { CharacterProject } from '../api'
import { creation } from '../creation'
import type { Direction, Preview, Prompt } from '../creation'

const initial: Direction = { style: 'Custom', medium: 'Digital illustration', mood: '', palette: '', lighting: '', composition: '', preserve: '', avoid: '', aspect_ratio: '4:5' }
export default function CreativeDirection({ project, next }: { project: CharacterProject; next: () => void }) {
  const query = useQuery({ queryKey: ['prompts', project.id], queryFn: () => creation.prompts(project.id) })
  if (query.isPending) return <p role="status">Loading your creative direction…</p>
  if (query.isError) return <p role="alert">{query.error.message}<button onClick={() => void query.refetch()}>Retry</button></p>
  return <Editor key={project.id} project={project} versions={query.data} next={next} />
}
function Editor({ project, versions, next }: { project: CharacterProject; versions: Prompt[]; next: () => void }) {
  const cache = useQueryClient()
  const [direction, setDirection] = useState<Direction>(versions[0]?.direction ?? initial)
  const [preview, setPreview] = useState<Preview | null>(null)
  const [savedId, setSavedId] = useState('')
  const [historyId, setHistoryId] = useState('')
  const assemble = useMutation({ mutationFn: () => creation.preview(project.id, direction), onSuccess: data => { setPreview(data); setSavedId('') } })
  const save = useMutation({ mutationFn: () => creation.save(project.id, direction, preview!), onSuccess: data => { setSavedId(data.id); void cache.invalidateQueries({ queryKey: ['prompts', project.id] }) } })
  const busy = assemble.isPending || save.isPending
  function change(key: keyof Direction, value: string) { setDirection({ ...direction, [key]: value }); setPreview(null); setSavedId(''); assemble.reset(); save.reset() }
  const history = versions.find(p => p.id === historyId)
  return <div className="creation-page"><div className="page-heading"><div><span className="eyebrow">02 / CREATIVE DIRECTION</span><h1>A familiar face. Your perspective.</h1><p>{project.name} · Choose a style for this project, then shape the details.</p></div><span className="status-chip">{versions.length} saved versions</span></div>
    <div className="creation-columns"><section className="panel creation-panel"><span className="eyebrow">THE VISUAL LANGUAGE</span><h2>Make it your own.</h2><p>Start anywhere. Every style and detail is yours to edit.</p><fieldset disabled={busy} className="direction-fields">
      <label>Style<input list="style-ideas" value={direction.style} maxLength={100} onChange={e => change('style', e.target.value)} /></label><datalist id="style-ideas">{['Custom', 'Cinematic realism', 'Editorial illustration', 'Anime', 'Watercolor', 'Graphic novel', 'Sculptural 3D'].map(s => <option key={s}>{s}</option>)}</datalist>
      <label>Medium<input value={direction.medium} maxLength={200} onChange={e => change('medium', e.target.value)} /></label>
      <label>Aspect ratio<select value={direction.aspect_ratio} onChange={e => change('aspect_ratio', e.target.value)}>{['1:1', '4:5', '3:2', '16:9', '9:16'].map(s => <option key={s}>{s}</option>)}</select></label>
      {(['mood', 'palette', 'lighting', 'composition', 'preserve', 'avoid'] as const).map(key => <label key={key}>{key === 'preserve' ? 'Character details to preserve' : key === 'avoid' ? 'Elements to avoid' : key}<textarea rows={2} maxLength={key === 'preserve' ? 2000 : ['composition', 'avoid'].includes(key) ? 1000 : 500} value={direction[key]} placeholder={`Describe ${key === 'preserve' ? 'the defining features' : key}…`} onChange={e => change(key, e.target.value)} /></label>)}
    </fieldset><button className="primary" disabled={busy || !direction.style.trim()} onClick={() => assemble.mutate()}><Sparkles size={15} />{assemble.isPending ? 'Assembling…' : 'Assemble prompt'}</button><p className="creation-note">Uses your selected references and latest research. Assembled locally, ready for your edits.</p></section>
    <section className="panel creation-panel prompt-panel"><span className="eyebrow">YOUR MASTER PROMPT</span><h2>Refine before you create.</h2>{preview ? <><div className="snapshot-summary">{preview.context.references.length} frozen references · {direction.aspect_ratio}<ul>{preview.context.references.map(r => <li key={r.id}>{r.title}</li>)}</ul></div><label>Editable prompt<textarea className="prompt-editor" value={preview.prompt_text} maxLength={24000} disabled={busy} onChange={e => { setPreview({ ...preview, prompt_text: e.target.value }); setSavedId(''); save.reset() }} /></label><div className="creation-actions"><button className="primary" disabled={busy || !!savedId || preview.prompt_text.trim().length < 10} onClick={() => save.mutate()}>{save.isPending ? 'Saving…' : savedId ? 'Version saved' : 'Save new version'}</button>{savedId && <button className="secondary" onClick={next}>Open image studio<ArrowRight size={14} /></button>}</div></> : <div className="prompt-empty"><Sparkles size={36} strokeWidth={1} /><h3>A clear direction starts here.</h3><p>Select references in Research & references, fill in your direction, and assemble an editable prompt.</p></div>}
      {(assemble.error || save.error) && <p role="alert" className="error-message">{(assemble.error || save.error)?.message}</p>}
      <div className="prompt-history"><h3>Saved versions</h3><label>Inspect a frozen version<select value={historyId} onChange={e => setHistoryId(e.target.value)}><option value="">Choose a version</option>{versions.map(p => <option key={p.id} value={p.id}>v{p.version} · {p.direction.style} · {new Date(p.created_at).toLocaleString()}</option>)}</select></label>{history && <><pre>{history.prompt_text}</pre><a className="secondary" href={creation.pack(project.id, history.id)}><Download size={14} />Download reference pack</a></>}</div>
    </section></div></div>
}
