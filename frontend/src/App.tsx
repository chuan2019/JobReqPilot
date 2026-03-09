import { useState } from 'react'
import { QueryClient, QueryClientProvider, useMutation } from '@tanstack/react-query'
import { SearchForm } from './components/SearchForm'
import { JobList } from './components/JobList'
import { postSearch } from './api/search'
import type { SearchRequest, SearchResponse } from './types'
import './App.css'

const queryClient = new QueryClient()

function SearchPage() {
  const [results, setResults] = useState<SearchResponse | null>(null)

  const mutation = useMutation({
    mutationFn: postSearch,
    onSuccess: (data) => setResults(data),
  })

  const handleSearch = (params: SearchRequest) => {
    mutation.mutate(params)
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>JobReqPilot</h1>
        <p>AI-powered job search and requirements analysis</p>
      </header>

      <main>
        <SearchForm onSearch={handleSearch} isLoading={mutation.isPending} />

        {mutation.isError && (
          <div className="error-banner">
            <strong>Search failed:</strong>{' '}
            {mutation.error instanceof Error
              ? mutation.error.message
              : 'An unexpected error occurred.'}
            <button className="btn-secondary btn-small" onClick={() => mutation.reset()}>
              Dismiss
            </button>
          </div>
        )}

        {results && (
          <JobList
            jobs={results.jobs}
            queryUsed={results.query_used}
            cached={results.cached}
          />
        )}
      </main>
    </div>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <SearchPage />
    </QueryClientProvider>
  )
}

export default App
