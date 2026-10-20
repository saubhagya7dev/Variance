import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BookOpenText, Link2, RefreshCw, Sparkles } from 'lucide-react'
import { api } from '../api'
import type { CharacterProject } from '../api'
import { discovery } from '../discovery'
import ProjectNotes from './ProjectNotes'

const tabs = ['Overview', 'Visual DNA', 'Sources', 'My direction'] as const
export default function ResearchPanel({ project, saved, settings }: { project: CharacterProject; saved: (p: CharacterProject) => void; settings: () => void }) {
  const client = useQueryClient()
  const [tab, setTab] = useState<(typeof tabs)[number]>('Overview')
  const [snapshotId, setSnapshotId] = useState('')
  const [chosenProvider, setChosenProvider] = useState<'wikipedia' | 'gemini' | null>(null)
  const query = useQuery({ queryKey: ['research', project.id], queryFn: () => discovery.research(project.id) })
  const capabilities = useQuery({ queryKey: ['capabilities'], queryFn: api.capabilities })
  const provider = chosenProvider ?? (capabilities.data?.research.provider === 'gemini' ? 'gemini' : 'wikipedia')
  const available = provider === 'wikipedia' || capabilities.data?.research.providers?.gemini
  const run = useMutation({ mutationFn: () => discovery.runResearch(project.id, provider), onSuccess: () => {
    setSnapshotId(''); void client.invalidateQueries({ queryKey: ['research', project.id] })
  } })
  const snapshot = query.data?.find(s => s.id === snapshotId) ?? query.data?.[0]
  const brief = snapshot?.brief
  const linkedEvidence = brief?.citations.filter(c => tab !== 'Visual DNA' || brief.visual_details.includes(c.text)) ?? []
  return <section className="panel research-panel" aria-labelledby="research-heading">
    <div className="panel-heading"><div><span className="panel-icon warm"><Sparkles size={17} /></span><h2 id="research-heading">Character research</h2><span className="provider-tag">{provider ?? 'SOURCES'}</span></div><button className="icon-button" onClick={settings} aria-label="Research connection settings"><Link2 size={15} /></button></div>
    <label className="snapshot-picker">Research provider<select value={provider} disabled={run.isPending} onChange={e => { setChosenProvider(e.target.value as 'wikipedia' | 'gemini'); run.reset() }}><option value="wikipedia">Wikipedia · free source extracts</option><option value="gemini">Gemini · AI research with sources</option></select></label>
    <div className="discovery-actions"><div><strong>{provider === 'gemini' ? `Research with ${capabilities.data?.research.model ?? 'Gemini'}` : 'Discover source extracts'}</strong><p>{provider === 'gemini' ? 'Sends character identity to Google for a sourced brief. Uses your account quota.' : 'Free Wikipedia excerpts. Review matches against your exact character and version.'}</p></div><button className="secondary small" disabled={run.isPending || !available} onClick={() => run.mutate()}><RefreshCw size={13} className={run.isPending ? 'spinning' : ''} />{run.isPending ? 'Researching…' : snapshot ? 'Refresh research' : 'Start research'}</button></div>
    {provider === 'gemini' && !available && !capabilities.isPending && <p className="discovery-message">{capabilities.isError ? 'Could not check the Gemini connection.' : 'Add GEMINI_API_KEY to your local .env and restart the backend to use Gemini. Wikipedia is ready without a key.'}<button className="text-button" onClick={() => void capabilities.refetch()}>Refresh connection</button></p>}
    {run.isPending && <p className="discovery-message" role="status">Gathering sources. This can take up to 90 seconds; keep this view open.</p>}
    {(run.isError || query.isError) && <div className="discovery-message error-message" role="alert">{run.error?.message ?? query.error?.message}<button className="text-button" onClick={() => void query.refetch()}>Reload saved research</button></div>}
    {query.isPending && <p className="discovery-message" role="status">Loading saved research…</p>}
    {query.data && query.data.length > 0 && <label className="snapshot-picker">Saved research<select value={snapshot?.id ?? ''} onChange={e => setSnapshotId(e.target.value)}>{query.data.map(s => <option key={s.id} value={s.id}>{new Date(s.created_at).toLocaleString()} · {s.provider}</option>)}</select></label>}
    <div className="research-tabs" role="tablist" aria-label="Character research sections">{tabs.map((label, index) => <button key={label} role="tab" id={`research-tab-${index}`} aria-controls="research-content" aria-selected={tab === label} tabIndex={tab === label ? 0 : -1} className={tab === label ? 'selected' : ''} onClick={() => setTab(label)} onKeyDown={e => {
      const next = e.key === 'ArrowRight' ? (index + 1) % tabs.length : e.key === 'ArrowLeft' ? (index + tabs.length - 1) % tabs.length : e.key === 'Home' ? 0 : e.key === 'End' ? tabs.length - 1 : -1
      if (next >= 0) { e.preventDefault(); setTab(tabs[next]); document.getElementById(`research-tab-${next}`)?.focus() }
    }}>{label}{label === 'Sources' && <span>{brief?.sources.length ?? 0}</span>}</button>)}</div>
    <div id="research-content" role="tabpanel" aria-labelledby={`research-tab-${tabs.indexOf(tab)}`} className="research-content">
      {tab === 'My direction' ? <ProjectNotes key={`${project.id}:${project.revision}`} project={project} saved={saved} /> : !brief ? <div className="panel-empty"><BookOpenText size={28} /><h3>A source for every study.</h3><p>Start research to gather real source material. Your notes and references stay separate.</p></div>
        : tab === 'Sources' ? <div className="research-results"><p className="field-help">Source links supplied by {snapshot?.provider}. Check identity, accuracy, and reuse terms.</p>{brief.sources.map((source, i) => <a className="source-link" href={source.url} target="_blank" rel="noopener noreferrer" key={i}><span>{i + 1}</span><div><strong>{source.title}</strong><small>{new URL(source.url).hostname}</small></div><Link2 size={14} /></a>)}{brief.kind === 'source_extracts' && <p className="field-help">Wikipedia extracts: CC BY-SA; attribution and revision history are available on each source page.</p>}</div>
          : <div className="research-results"><span className="status-chip neutral">{brief.kind === 'source_extracts' ? 'Source extracts · identity not verified' : 'AI synthesis · review against sources'}</span>{tab === 'Visual DNA' && !brief.visual_details ? <p className="discovery-message">Visual traits have not been inferred from these excerpts. Add your observations in My direction, or configure Gemini for a sourced visual brief.</p> : <>{brief.kind !== 'source_extracts' && <p className="research-prose">{tab === 'Visual DNA' ? brief.visual_details : brief.text}</p>}<h3>Source-linked evidence</h3>{linkedEvidence.map((citation, i) => <div className="evidence" key={i}><p>{citation.text}</p><span>{citation.sources.map(index => brief.sources[index] && <a key={index} href={brief.sources[index].url} target="_blank" rel="noopener noreferrer">[{index + 1}] {brief.sources[index].title}</a>)}</span></div>)}</>}</div>}
    </div>
    {brief?.suggestions_html && <iframe className="search-suggestions" title="Google Search suggestions" sandbox="allow-popups allow-popups-to-escape-sandbox" referrerPolicy="no-referrer" srcDoc={'<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\';">' + brief.suggestions_html} />}
  </section>
}
