import { useQuery } from '@tanstack/react-query'
import { Check, Database, Image, Link2, LockKeyhole, Radio, Sparkles } from 'lucide-react'
import { api } from '../api'

export default function Settings() {
  const query = useQuery({ queryKey: ['capabilities'], queryFn: api.capabilities })
  return <div className="settings-page"><div className="page-heading"><div><span className="eyebrow">THE TOOLS BEHIND THE WORK</span><h1>Your studio. Your setup.</h1><p>Simple connections, clear capabilities, and no surprises.</p></div><span className="status-chip"><LockKeyhole size={12} /> Personal workspace</span></div>
    {query.isError && <p role="alert" className="error-message">Connection status could not be loaded. <button className="text-button" onClick={() => void query.refetch()}>Retry</button></p>}
    <div className="settings-layout"><section className="panel settings-connections"><div className="panel-heading"><div><Link2 size={17} /><h2>Connections</h2></div><span className="tiny-label">ROADMAP</span></div>{[
      { key: 'research' as const, title: 'Character research', subtitle: 'Gemini · grounded briefs and source evidence', icon: Sparkles, phase: 2 },
      { key: 'references' as const, title: 'Reference discovery', subtitle: 'Image search · sources and visual details', icon: Image, phase: 2 },
      { key: 'generation' as const, title: 'Image generation', subtitle: 'Manual packs + optional paid Gemini image API', icon: Radio, phase: 3 },
      { key: 'captions' as const, title: 'Captions & manual posting', subtitle: 'Local templates � optional Gemini drafting � approved exports', icon: Sparkles, phase: 4 },
      { key: 'publishing' as const, title: 'Social accounts', subtitle: 'Instagram, Facebook, and optionally X', icon: Link2, phase: 5 },
    ].map(item => <div className="connection-row" key={item.key}><span className="small-icon"><item.icon size={19} /></span><div><h3>{item.title}</h3><p>{item.subtitle}</p><span className="connection-detail">{query.isPending ? 'Checking configuration…' : query.isError ? 'Status unavailable' : query.data?.[item.key].configured ? 'Key configured · adapter not connected' : 'Not connected'} · planned for phase {item.phase}</span></div><LockKeyhole size={13} /></div>)}</section><div><section className="panel local-settings"><span className="empty-symbol"><Database size={23} /></span><h2>At home on your device.</h2><p>Your character projects and notes are saved in a local SQLite database. No cloud account is needed for this workspace.</p><div><Check size={13} /> Local project storage</div><div><Check size={13} /> Reversible project archiving</div><div><Check size={13} /> Dark theme by design</div></section><div className="privacy-note"><LockKeyhole size={15} /><p>Provider keys belong in your local <code>.env</code> file. They are never displayed here. Free discovery and manual generation need no keys. Gemini image API access is not free. It stays disabled unless GEMINI_API_KEY and GEMINI_IMAGE_PAID_ENABLED=true are configured locally. To use Gemini research, set GEMINI_API_KEY, restart, then choose Gemini in Character research. RESEARCH_PROVIDER sets the initial selection. Use an account without billing enabled to stay within the free tier. For optional caption drafting, also set GEMINI_CAPTIONS_ENABLED=true; local caption templates work without keys.</p></div></div></div>
  </div>
}
