import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, ArrowRight, ArrowUpRight, Bell, Check, ChevronDown, ChevronRight, CircleHelp, Clock3, Command, Download, Ellipsis, FlaskConical, Image, Layers3, LockKeyhole, Menu, PanelLeftClose, Plus, Search, Settings2, TrendingUp, WandSparkles, X } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { api } from './api'
import type { CharacterProject } from './api'
import CreateProject from './components/CreateProject'
import History from './components/History'
import Modal from './components/Modal'
import Settings from './components/Settings'
import Workspace from './components/Workspace'
import CreativeDirection from './components/CreativeDirection'
import ImageStudio from './components/ImageStudio'
import CaptionStudio from './components/CaptionStudio'
import './styles.css'
import './creation.css'

type View = 'workspace' | 'history' | 'settings' | 'prompt' | 'generation' | 'captions' | 'publishing' | 'performance'
const steps: { id: View; title: string; subtitle: string; icon: LucideIcon; phase: number }[] = [
  { id: 'workspace', title: 'Research & references', subtitle: 'Know your character', icon: Search, phase: 2 },
  { id: 'prompt', title: 'Creative direction', subtitle: 'Find your perspective', icon: WandSparkles, phase: 3 },
  { id: 'generation', title: 'Image studio', subtitle: 'Bring the idea to life', icon: Image, phase: 3 },
  { id: 'captions', title: 'Captions & tags', subtitle: 'Give it a voice', icon: Layers3, phase: 4 },
  { id: 'publishing', title: 'Publish', subtitle: 'Share with the world', icon: ArrowUpRight, phase: 5 },
  { id: 'performance', title: 'Performance', subtitle: 'Learn from the work', icon: TrendingUp, phase: 6 },
]
function readProjectId() { return new URLSearchParams(window.location.search).get('project') }

export default function App() {
  const queryClient = useQueryClient()
  const [selected, setSelected] = useState<string | null>(readProjectId)
  const [view, setView] = useState<View>('workspace')
  const [search, setSearch] = useState('')
  const [createOpen, setCreateOpen] = useState(false)
  const [mobileNav, setMobileNav] = useState(false)
  const [helpOpen, setHelpOpen] = useState(false)
  const [activityOpen, setActivityOpen] = useState(false)
  const [toast, setToast] = useState('')
  const searchRef = useRef<HTMLInputElement>(null)
  const health = useQuery({ queryKey: ['health'], queryFn: api.health, refetchInterval: 30000 })
  const projects = useQuery({ queryKey: ['projects', false], queryFn: () => api.projects() })
  const projectQuery = useQuery({ queryKey: ['project', selected], queryFn: () => api.project(selected!), enabled: !!selected })
  const project = projectQuery.data
  useEffect(() => {
    const keydown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); searchRef.current?.focus() }
      if (event.key === 'Escape') { setMobileNav(false); setActivityOpen(false) }
    }
    const pop = () => { setSelected(readProjectId()); setView('workspace') }
    window.addEventListener('keydown', keydown); window.addEventListener('popstate', pop)
    return () => { window.removeEventListener('keydown', keydown); window.removeEventListener('popstate', pop) }
  }, [])
  useEffect(() => { if (toast) { const timeout = window.setTimeout(() => setToast(''), 4500); return () => window.clearTimeout(timeout) } }, [toast])
  function navigate(next: View) { setView(next); setMobileNav(false); setActivityOpen(false) }
  function openProject(p: CharacterProject) {
    queryClient.setQueryData(['project', p.id], p); setSelected(p.id); setView('workspace'); setMobileNav(false)
    window.history.pushState({}, '', `?project=${p.id}`)
  }
  function created(p: CharacterProject) { void queryClient.invalidateQueries({ queryKey: ['projects'] }); openProject(p); setCreateOpen(false); setSearch(''); setToast('Character project created. Your starting point is saved.') }
  function saved(p: CharacterProject) { queryClient.setQueryData(['project', p.id], p); void queryClient.invalidateQueries({ queryKey: ['projects'] }); setToast('Creative direction saved locally.') }
  function newWorkspace() { setSelected(null); setView('workspace'); window.history.pushState({}, '', window.location.pathname) }
  function exportProject() {
    if (!project) return
    const url = URL.createObjectURL(new Blob([JSON.stringify(project, null, 2)], { type: 'application/json' }))
    const link = document.createElement('a'); link.href = url; link.download = `variance-${project.id.slice(0, 8)}.json`; link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000); setToast('Project notes exported. No images or posts have been published.')
  }
  const currentStep = steps.find(s => s.id === view)
  return <div className="app-shell"><a className="skip-link" href="#main-content">Skip to workspace</a>
    {mobileNav && <button className="nav-backdrop" onClick={() => setMobileNav(false)} aria-label="Close navigation" />}
    <aside className={`sidebar ${mobileNav ? 'mobile-open' : ''}`} aria-label="Studio navigation"><div className="sidebar-brand"><button className="brand" onClick={newWorkspace} aria-label="Variance home"><span className="brand-mark"><i /><i /><i /></span><span>variance<span className="brand-period">.</span></span></button><button className="icon-button mobile-close" onClick={() => setMobileNav(false)} aria-label="Close navigation"><PanelLeftClose size={17} /></button></div>
      <button className="workspace-switch" onClick={() => navigate('history')}><span className="workspace-avatar">V</span><span><strong>Personal studio</strong><small>Your creative workspace</small></span><ChevronDown size={13} /></button>
      <div className="navigation-label">CREATE WITH INTENTION<span>01—06</span></div><nav className="phase-navigation">{steps.map((step, i) => <button key={step.id} className={`phase-link ${view === step.id ? 'active' : ''}`} onClick={() => navigate(step.id)} aria-current={view === step.id ? 'page' : undefined}><span className="phase-icon"><step.icon size={17} strokeWidth={1.6} /></span><span className="phase-text"><strong>{step.title}</strong><small>{step.subtitle}</small></span><span className="phase-index">{view === step.id ? <span className="active-dot" /> : `0${i + 1}`}</span></button>)}</nav>
      <div className="sidebar-divider" /><button className={`utility-link ${view === 'history' ? 'active' : ''}`} onClick={() => navigate('history')}><Clock3 size={16} />Character history<span>{projects.data?.length ?? '—'}</span></button><button className={`utility-link ${view === 'settings' ? 'active' : ''}`} onClick={() => navigate('settings')}><Settings2 size={16} />Studio settings</button>
      <div className="sidebar-bottom"><div className="studio-note"><span className="note-star">✧</span><p>Good art starts with<br /><strong>a different perspective.</strong></p><div className="note-decoration" /></div><button className="profile-button" onClick={() => navigate('settings')}><span className="profile-avatar">Y</span><span><strong>Your workspace</strong><small><span /> Local & private</small></span><Ellipsis size={18} /></button></div>
    </aside>
    <div className="main-shell"><header className="topbar"><div className="breadcrumb"><button className="icon-button mobile-menu" onClick={() => setMobileNav(true)} aria-label="Open navigation"><Menu size={20} /></button><span>Studio</span><ChevronRight size={12} /><strong>{view === 'history' ? 'Character history' : view === 'settings' ? 'Settings' : currentStep?.title}</strong></div><div className="top-actions"><span className={`local-status ${health.isError ? 'offline' : ''}`}><span />{health.isPending ? 'Connecting' : health.isError ? 'Backend offline' : 'Local workspace'}</span><span className="top-divider" /><button className="icon-button" onClick={() => setHelpOpen(true)} aria-label="Workspace guide"><CircleHelp size={17} /></button><div className="activity-container"><button className={`icon-button ${activityOpen ? 'pressed' : ''}`} onClick={() => setActivityOpen(!activityOpen)} aria-label="Workspace activity" aria-expanded={activityOpen}><Bell size={16} /></button>{activityOpen && <div className="activity-popover"><span className="eyebrow">WORKSPACE STATUS</span><h3>Your studio activity.</h3><p>Open Image studio to follow queued generation batches and review saved results. Research and imports run when requested.</p><button className="text-button" onClick={() => navigate('settings')}>View connections<ArrowUpRight size={13} /></button></div>}</div></div></header>
      <main id="main-content"><div className="search-header"><form className="character-search" onSubmit={e => { e.preventDefault(); setCreateOpen(true) }}><span className="search-glyph"><Search size={20} strokeWidth={1.6} /></span><input ref={searchRef} aria-label="Character name" value={search} onChange={e => setSearch(e.target.value)} maxLength={100} placeholder="Who’s your next inspiration?" /><span className="keyboard-hint"><Command size={10} /> K</span><button className="search-submit" type="submit" aria-label="Create a character project"><ArrowRight size={19} /></button></form><button className="new-project-button" aria-label="New project" onClick={() => { setSearch(''); setCreateOpen(true) }}><Plus size={16} /><span>New project</span></button></div>
        {health.isError && <div className="connection-warning" role="alert"><span>The local backend is unavailable. Start it to save or open projects.</span><button className="text-button" onClick={() => { void health.refetch(); void projects.refetch(); if (selected) void projectQuery.refetch() }}>Reconnect</button></div>}
        <div className="workspace-toolbar"><div><span className="workspace-tab"><FlaskConical size={13} />{project && view === 'workspace' ? project.name : 'Creative workspace'}</span><span className="tiny-label">{view === 'workspace' ? 'DISCOVERY' : view === 'history' ? 'YOUR PROJECTS' : view === 'settings' ? 'CONFIGURATION' : ['prompt', 'generation', 'captions'].includes(view) ? 'CREATE & REVIEW' : 'UPCOMING'}</span></div><div>{project && view === 'workspace' && <button className="text-button" onClick={exportProject}><Download size={13} />Export notes</button>}<button className="icon-button" onClick={() => setHelpOpen(true)} aria-label="About this workspace"><CircleHelp size={14} /></button></div></div>
        {view === 'history' ? <History open={openProject} create={() => setCreateOpen(true)} notify={setToast} /> : view === 'settings' ? <Settings /> : ['workspace', 'prompt', 'generation', 'captions'].includes(view) ? selected && projectQuery.isPending ? <div className="large-empty"><span className="loading-ring" /><h2>Opening your character study…</h2></div> : selected && projectQuery.isError ? <div className="large-empty"><h2>Couldn’t open this project.</h2><p>{projectQuery.error.message}</p><button className="secondary" onClick={() => void projectQuery.refetch()}>Try again</button><button className="text-button" onClick={() => navigate('history')}>Back to history</button></div> : project?.archived ? <div className="large-empty"><Clock3 size={28} /><h2>This character is in your archive.</h2><p>Restore it from Character history to continue editing.</p><button className="primary" onClick={() => navigate('history')}>Open history<ArrowUpRight size={15} /></button></div> : view === 'prompt' || view === 'generation' || view === 'captions' ? project ? view === 'captions' ? <CaptionStudio key={project.id} project={project} images={() => navigate('generation')} /> : view === 'prompt' ? <CreativeDirection key={project.id} project={project} next={() => navigate('generation')} /> : <ImageStudio key={project.id} project={project} direction={() => navigate('prompt')} /> : <div className="large-empty"><h2>Start with a character.</h2><p>Create or open a project, then select references for your artwork.</p><button className="primary" onClick={() => setCreateOpen(true)}>New project</button><button className="text-button" onClick={() => navigate('history')}>Open history</button></div> : <Workspace key={project?.id ?? 'empty'} project={project} create={() => setCreateOpen(true)} saved={saved} settings={() => navigate('settings')} direction={() => navigate('prompt')} /> : <section className="future-stage"><span className="eyebrow">THE NEXT CHAPTER / PHASE {currentStep?.phase}</span><span className="future-icon">{currentStep && <currentStep.icon size={38} strokeWidth={1} />}</span><h1>{currentStep?.title}</h1><p>{view === 'prompt' ? 'Shape a signature style, then turn your researched character and selected references into an editable master prompt.' : view === 'generation' ? 'Explore variations, compare images side by side, and choose the artwork that captures your vision.' : view === 'captions' ? 'Give approved artwork a voice with grounded captions, considered hashtags, and platform-specific previews.' : view === 'publishing' ? 'Review the complete post, approve it, and share through your authorized social accounts.' : 'See what resonates with your audience through real measurements and thoughtful reflection.'}</p><span className="status-chip neutral"><LockKeyhole size={12} /> Planned · not connected</span><div className="future-path"><span className={project ? "complete" : ""}>{project && <Check size={13} />} Character identity</span><ChevronRight size={14} /><span>Research & references</span><ChevronRight size={14} /><span>{currentStep?.title}</span></div><button className="secondary" onClick={() => navigate('workspace')}><ArrowLeft size={14} />Back to your character</button></section>}
      </main><footer className="app-footer"><span>VARIANCE <i /> PERSONAL CREATIVE STUDIO</span><span>Made for imagination. Built around you.</span><span>v0.4 <span className="accent-dot" /></span></footer>
    </div>
    {createOpen && <CreateProject initialName={search} close={() => setCreateOpen(false)} created={created} />}
    {helpOpen && <Modal title="A character. A new perspective." eyebrow="YOUR WORKSPACE GUIDE" close={() => setHelpOpen(false)}><div className="help-content"><p>Start with a fictional character and confirm their franchise and version. Save your creative direction in <strong>My direction</strong>, then revisit projects from <strong>Character history</strong>.</p><div className="help-shortcut"><span>Focus character search</span><kbd>Ctrl / ⌘ + K</kbd></div><h3>What works today</h3><p>Character research, reference collections, editable prompt versions, manual generation packs, API generation with configured credentials, image comparison and review, caption versions, post approval, export packs and manual publication records.</p><h3>What comes next</h3><p>Connected publishing and measured performance are future phases. Captions and manual posting are available now. Manual generation works without API keys; Gemini image API generation requires paid access and explicit enablement. There is no published free image API tier.</p></div><button className="primary" onClick={() => setHelpOpen(false)}>Back to creating<ArrowUpRight size={14} /></button></Modal>}
    {toast && <div className="toast" role="status"><Check size={16} />{toast}<button onClick={() => setToast('')} aria-label="Dismiss notification"><X size={13} /></button></div>}
  </div>
}
