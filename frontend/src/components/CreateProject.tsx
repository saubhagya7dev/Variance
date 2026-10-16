import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { ArrowUpRight, Check, UserRound } from 'lucide-react'
import { api } from '../api'
import type { CharacterProject } from '../api'
import Modal from './Modal'

export default function CreateProject({ initialName, close, created }: { initialName: string; close: () => void; created: (project: CharacterProject) => void }) {
  const [name, setName] = useState(initialName)
  const [franchise, setFranchise] = useState('')
  const [variant, setVariant] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const mutation = useMutation({ mutationFn: () => api.create({ name: name.trim(), franchise: franchise.trim(), variant: variant.trim(), fictional_confirmed: true }), onSuccess: created })
  return <Modal title="Meet your next character." eyebrow="A NEW CREATIVE PROJECT" close={close}>
    <p className="modal-description">Start with the right identity. The franchise and version keep every detail of your character in focus.</p>
    <form onSubmit={event => { event.preventDefault(); if (confirmed) mutation.mutate() }}>
      <label>Character name<input autoFocus value={name} onChange={e => setName(e.target.value)} required maxLength={100} placeholder="e.g. Frieren" /></label>
      <div className="form-columns"><label>Franchise<input value={franchise} onChange={e => setFranchise(e.target.value)} required maxLength={160} placeholder="e.g. Beyond Journey’s End" /></label><label>Version or appearance<input value={variant} onChange={e => setVariant(e.target.value)} required maxLength={160} placeholder="e.g. Original anime design" /></label></div>
      <div className="identity-preview"><span className="identity-icon"><UserRound size={23} /></span><div><strong>{name.trim() || 'Your character'}</strong><p>{franchise.trim() || 'Franchise'} <span> / </span> {variant.trim() || 'Version'}</p></div><span className="tiny-label">IDENTITY</span></div>
      <label className="checkbox-label"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} required /><span>This is a fictional character. I’ve confirmed the franchise and version.</span></label>
      {mutation.isError && <p className="error-message" role="alert">{mutation.error.message}</p>}
      <div className="modal-footer"><span><Check size={13} /> Saved on this device</span><button className="primary" disabled={mutation.isPending || !confirmed || !name.trim() || !franchise.trim() || !variant.trim()}>{mutation.isPending ? 'Creating…' : 'Create project'}<ArrowUpRight size={16} /></button></div>
    </form>
  </Modal>
}
