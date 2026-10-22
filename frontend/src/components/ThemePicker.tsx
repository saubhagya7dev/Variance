import { Check, Palette } from 'lucide-react'
import { useStudioTheme } from '../theme'
import type { StudioTheme } from '../theme'

const options: { id: StudioTheme; name: string; description: string }[] = [
  { id: 'brown', name: 'Warm Brown', description: 'Espresso, amber light, and a soft grain.' },
  { id: 'purple', name: 'Deep Purple', description: 'Midnight violet with a diffused plum glow.' },
  { id: 'charcoal', name: 'Dark Charcoal', description: 'Graphite surfaces and quiet silver accents.' },
]

export default function ThemePicker() {
  const { theme, persisted, setTheme } = useStudioTheme()
  return <section className="panel appearance-panel" aria-labelledby="appearance-title">
    <div className="appearance-heading"><div><span className="eyebrow"><Palette size={13} /> STUDIO APPEARANCE</span><h2 id="appearance-title">Set the mood.</h2><p>Three palettes. Your own creative atmosphere.</p></div><span className="status-chip neutral">All dark, by design</span></div>
    <fieldset className="theme-options"><legend className="visually-hidden">Studio theme</legend>
      {options.map(option => <label key={option.id} className={`theme-option ${theme === option.id ? 'is-selected' : ''}`}>
        <input type="radio" name="studio-theme" value={option.id} checked={theme === option.id} onChange={() => setTheme(option.id)} />
        <span className={`theme-preview preview-${option.id}`} aria-hidden="true"><span className="theme-preview-sidebar"><i /><i /><i /></span><span className="theme-preview-workspace"><i /><span><i /><i /></span><i /></span></span>
        <span className="theme-option-copy"><span><strong>{option.name}</strong><span className="theme-selected" aria-hidden="true">{theme === option.id && <Check size={13} />}</span></span><small>{option.description}</small></span>
      </label>)}
    </fieldset>
    <p className="appearance-status" role="status">{options.find(option => option.id === theme)?.name} selected. {persisted ? 'Saved in this browser for your next visit.' : 'Applied for this visit. Browser storage is unavailable.'}</p>
  </section>
}
