import { useMutation, useQuery } from '@tanstack/react-query'
import { request } from '../api'
import '../connections.css'

interface Connection { platform: string; configured: boolean; missing: string[] }
interface Identity { name: string; account_id: string; checked_at: string; message: string }
const titles: Record<string, string> = { instagram: 'Instagram', facebook: 'Facebook Page', threads: 'Threads', x: 'X (Twitter)' }

function ConnectionCard({ connection }: { connection: Connection }) {
  const check = useMutation({ mutationFn: () => request<Identity>(`/connections/${connection.platform}/check`, 'POST') })
  return <section className="panel creation-panel">
    <h3>{titles[connection.platform]}</h3>
    <span className="status-chip neutral">{check.isPending ? 'Checking…' : check.isError ? 'Check failed' : check.isSuccess ? 'Identity verified' : connection.configured ? 'Configured · not verified' : 'Setup needed'}</span>
    {!connection.configured && <p>Add to your local .env, then restart: <code>{connection.missing.join(', ')}</code></p>}
    <button className="secondary" disabled={!connection.configured || check.isPending} onClick={() => check.mutate()}>Check connection</button>
    {check.isError && <p role="alert" className="error-message">{check.error.message}</p>}
    {check.isSuccess && !check.isPending && <div role="status"><p><strong>{check.data.name}</strong> · {check.data.account_id}</p><p>Checked {new Date(check.data.checked_at).toLocaleString()}</p><p>{check.data.message}</p></div>}
  </section>
}

export default function SocialConnections() {
  const query = useQuery({ queryKey: ['social-connections'], queryFn: () => request<Connection[]>('/connections') })
  return <section aria-label="Social account connections"><h2>Your social connections.</h2><p>Credentials stay on the backend. Check connection reads account identity only; it does not publish. Provider API usage limits or charges may apply.</p><p>Use an Instagram Login token, a Facebook Page token, a Threads token, and an X OAuth 2.0 user token respectively. Live posting and automatic token renewal are not enabled yet.</p>
    <button className="text-button" onClick={() => void query.refetch()}>Refresh configuration</button>
    {query.isPending && <p role="status">Checking local configuration…</p>}
    {query.isError && <p role="alert">{query.error.message}</p>}
    <div className="social-connection-grid">{query.data?.map(connection => <ConnectionCard key={`${connection.platform}:${connection.configured}`} connection={connection} />)}</div>
  </section>
}
