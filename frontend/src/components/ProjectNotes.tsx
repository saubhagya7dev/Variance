import { useEffect, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Check, Save, WandSparkles } from 'lucide-react'
import { api } from '../api'
import type { CharacterProject } from '../api'

export default function ProjectNotes({ project, saved }: { project: CharacterProject; saved: (project: CharacterProject) => void }) {
  const draftKey = `variance-draft:${project.id}:${project.revision}`
  const [notes, setNotes] = useState(() => sessionStorage.getItem(`${draftKey}:notes`) ?? project.notes)
  const [direction, setDirection] = useState(() => sessionStorage.getItem(`${draftKey}:direction`) ?? project.direction)
  useEffect(() => {
    sessionStorage.setItem(`${draftKey}:notes`, notes)
    sessionStorage.setItem(`${draftKey}:direction`, direction)
  }, [draftKey, notes, direction])
  const dirty = notes !== project.notes || direction !== project.direction
  const mutation = useMutation({ mutationFn: () => api.save(project, notes, direction), onSuccess: updated => {
    sessionStorage.removeItem(`${draftKey}:notes`)
    sessionStorage.removeItem(`${draftKey}:direction`)
    saved(updated)
  } })
  return <form className="notes-form" onSubmit={e => { e.preventDefault(); mutation.mutate() }}>
    <div className="editor-intro"><span className="small-icon"><WandSparkles size={16} /></span><div><h3>Your point of view</h3><p>Give this character a creative direction.</p></div></div>
    <label>Creative direction <span>Optional</span><textarea value={direction} onChange={e => setDirection(e.target.value)} maxLength={3000} placeholder="The mood, style, palette, or story you want to explore…" rows={4} /></label>
    <label>Character notes <span>Optional</span><textarea value={notes} onChange={e => setNotes(e.target.value)} maxLength={6000} placeholder="An outfit to preserve, a version to avoid, details to look into…" rows={5} /></label>
    <p className="field-help">Personal notes, kept separate from sourced research.</p>
    {mutation.isError && <p className="error-message" role="alert">{mutation.error.message}</p>}
    <div className="editor-footer"><span>{dirty ? 'Unsaved changes' : <><Check size={12} /> Saved locally · v{project.revision}</>}</span><button className="secondary small" disabled={!dirty || mutation.isPending}><Save size={13} />{mutation.isPending ? 'Saving…' : 'Save direction'}</button></div>
  </form>
}
