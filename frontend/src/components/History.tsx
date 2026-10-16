import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Archive, ArchiveRestore, ArrowUpRight, Clock3, Plus, Search } from 'lucide-react'
import { api } from '../api'
import type { CharacterProject } from '../api'

export default function History({ open, create, notify }: { open: (project: CharacterProject) => void; create: () => void; notify: (text: string) => void }) {
  const [archived, setArchived] = useState(false)
  const [search, setSearch] = useState('')
  const queryClient = useQueryClient()
  const query = useQuery({ queryKey: ['projects', archived], queryFn: () => api.projects(archived) })
  const mutation = useMutation({ mutationFn: (p: CharacterProject) => api.archive(p, !p.archived), onSuccess: p => {
    void queryClient.invalidateQueries({ queryKey: ['projects'] })
    void queryClient.invalidateQueries({ queryKey: ['project', p.id] })
    notify(p.archived ? 'Project archived. You can restore it here anytime.' : 'Project restored to your workspace.')
  } })
  const projects = query.data?.filter(p => `${p.name} ${p.franchise} ${p.variant}`.toLowerCase().includes(search.toLowerCase())) ?? []
  return <div className="history-page"><div className="page-heading"><div><span className="eyebrow">YOUR CREATIVE ARCHIVE</span><h1>Every character has a history.</h1><p>Pick up a thought. Revisit a direction. Make something new.</p></div><button className="primary" onClick={create}><Plus size={15} /> New project</button></div><div className="history-toolbar"><div className="segmented"><button className={!archived ? 'active' : ''} onClick={() => setArchived(false)}>Active projects</button><button className={archived ? 'active' : ''} onClick={() => setArchived(true)}>Archived</button></div><label className="filter-input"><Search size={15} /><input aria-label="Search project history" value={search} onChange={e => setSearch(e.target.value)} placeholder="Find a character…" /></label></div>
    {mutation.isError && <p role="alert" className="error-message">{mutation.error.message}</p>}
    {query.isPending ? <div className="large-empty">Loading your projects…</div> : query.isError ? <div className="large-empty"><h3>Couldn’t open your history.</h3><p>{query.error.message}</p><button className="secondary" onClick={() => void query.refetch()}>Try again</button></div> : !projects.length ? <div className="large-empty"><span className="empty-symbol"><Clock3 size={28} /></span><h2>{search ? 'No matching characters.' : archived ? 'Nothing tucked away yet.' : 'Your next character starts here.'}</h2><p>{search ? 'Try a different name or franchise.' : archived ? 'Archived projects stay available for you to restore.' : 'Create a project and it will be saved here automatically.'}</p>{!search && !archived && <button className="primary" onClick={create}>Create a project<ArrowUpRight size={16} /></button>}</div> : <div className="history-grid">{projects.map((p, i) => <article className="project-card" key={p.id}><button className="project-card-open" onClick={() => open(p)}><div className={`project-card-art tone-${i % 3}`}><div className="card-orbit" /><span>{p.name.slice(0, 1).toUpperCase()}</span><small>CHARACTER STUDY / {p.id.slice(0, 6)}</small><ArrowUpRight size={19} className="card-arrow" /></div><div className="project-card-info"><span className="eyebrow">{p.franchise}</span><h2>{p.name}</h2><p>{p.variant}</p><span className="status-chip neutral">{p.archived ? 'Archived' : 'Identity confirmed'}</span></div></button><div className="project-card-footer"><span><Clock3 size={11} />{new Date(p.updated_at).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })}</span><button disabled={mutation.isPending} onClick={() => mutation.mutate(p)} aria-label={`${p.archived ? 'Restore' : 'Archive'} ${p.name}`}>{p.archived ? <><ArchiveRestore size={13} />Restore</> : <><Archive size={13} />Archive</>}</button></div></article>)}</div>}
  </div>
}
