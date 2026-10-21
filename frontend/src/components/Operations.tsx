import { useMutation, useQuery } from '@tanstack/react-query'
import { request } from '../api'

interface Health { database_ok: boolean; uncertain_deliveries: number; pending_samples: number; unavailable_samples: number; publishing_enabled: boolean; metrics_enabled: boolean; recent_calls: { provider: string; kind: string; outcome: string; created_at: string }[] }
export default function Operations() {
  const query = useQuery({ queryKey: ['operations'], queryFn: () => request<Health>('/operations'), refetchInterval: 30000 })
  const backup = useMutation({ mutationFn: async () => {
    const response = await fetch('/api/operations/backup', { method: 'POST', headers: { 'X-Variance-Client': 'studio' } })
    if (!response.ok) { const error = await response.json().catch(() => null); throw new Error(error?.detail || 'Backup failed. Check the server and available disk space.') }
    const url = URL.createObjectURL(await response.blob())
    const link = document.createElement('a'); link.href = url; link.download = `variance-backup-${new Date().toISOString().slice(0, 10)}.zip`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
  } })
  return <section className="panel creation-panel"><span className="eyebrow">PHASE 7 / STUDIO CARE</span><h2>Your work, preserved.</h2><p>Download a consistent database snapshot with stored reference images and artwork. API keys and .env are excluded. Keep the archive private: it contains your projects and account identifiers.</p>
    {query.data && <div className="metric-grid"><p>Database: {query.data.database_ok ? 'healthy' : 'needs attention'}</p><p>Uncertain deliveries: {query.data.uncertain_deliveries}</p><p>Pending snapshots: {query.data.pending_samples}</p><p>Unavailable snapshots: {query.data.unavailable_samples}</p><p>Live publishing: {query.data.publishing_enabled ? 'enabled' : 'disabled'}</p><p>Metrics worker: {query.data.metrics_enabled ? 'enabled' : 'disabled'}</p></div>}
    {query.isError && <p role="alert">{query.error.message}</p>}
    <button className="secondary" disabled={backup.isPending} onClick={() => backup.mutate()}>{backup.isPending ? 'Preparing backup…' : 'Download studio backup'}</button>{backup.isError && <p role="alert">{backup.error.message}</p>}{backup.isSuccess && <p role="status">Backup download prepared.</p>}
    {query.data && query.data.recent_calls.length > 0 && <details><summary>Recent provider activity</summary>{query.data.recent_calls.map((call, i) => <p key={i}>{call.provider} · {call.kind} · {call.outcome} · {new Date(call.created_at).toLocaleString()}</p>)}</details>}
    <details><summary>Restore a backup safely</summary><p>Stop the backend. From the backend folder run the following with a new, empty destination:</p><pre><code>python -m app.backup path/to/backup.zip path/to/restored-studio</code></pre><p>Set DATABASE_URL to sqlite:/// followed by the absolute restored studio.sqlite3 path, and ASSET_DIR to the restored assets folder in .env. Restart and check your projects. Keep your previous data until you have verified the restore. Tokens must be configured separately.</p></details>
  </section>
}
