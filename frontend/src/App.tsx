import { useQuery } from '@tanstack/react-query'

export default function App() {
  const health = useQuery({ queryKey: ['health'], queryFn: async () => {
    const response = await fetch('/api/health')
    if (!response.ok) throw new Error('Backend unavailable')
    return response.json() as Promise<{ status: string }>
  } })
  return <main><h1>Variance Studio</h1><p>{health.isPending ? 'Connecting…' : health.isError ? 'Start the backend to connect.' : 'Local foundation is ready.'}</p></main>
}
