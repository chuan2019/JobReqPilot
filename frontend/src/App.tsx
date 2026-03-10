import { useState } from 'react'
import { QueryClient, QueryClientProvider, useMutation } from '@tanstack/react-query'
import { SearchForm } from './components/SearchForm'
import { JobList } from './components/JobList'
import { SummaryView } from './components/SummaryView'
import { postSearch } from './api/search'
import { postSummarize } from './api/summarize'
import type { SearchRequest, SearchResponse, SummarizeResponse } from './types'
import './App.css'

const queryClient = new QueryClient()

function SearchPage() {
  const [results, setResults] = useState<SearchResponse | null>(null)
  const [summaryData, setSummaryData] = useState<SummarizeResponse | null>(null)

  const searchMutation = useMutation({
    mutationFn: postSearch,
    onSuccess: (data) => {
      setResults(data)
      setSummaryData(null) // Clear previous summary on new search
    },
  })

  const summarizeMutation = useMutation({
    mutationFn: postSummarize,
    onSuccess: (data) => setSummaryData(data),
  })

  const handleSearch = (params: SearchRequest) => {
    searchMutation.mutate(params)
  }

  const handleSummarize = (jobIds: string[]) => {
    summarizeMutation.mutate({ job_ids: jobIds })
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>JobReqPilot</h1>
        <p>AI-powered job search and requirements analysis</p>
      </header>

      <main>
        <SearchForm onSearch={handleSearch} isLoading={searchMutation.isPending} />

        {searchMutation.isError && (
          <div className="error-banner">
            <strong>Search failed:</strong>{' '}
            {searchMutation.error instanceof Error
              ? searchMutation.error.message
              : 'An unexpected error occurred.'}
            <button className="btn-secondary btn-small" onClick={() => searchMutation.reset()}>
              Dismiss
            </button>
          </div>
        )}

        {summarizeMutation.isError && (
          <div className="error-banner">
            <strong>Summarize failed:</strong>{' '}
            {summarizeMutation.error instanceof Error
              ? summarizeMutation.error.message
              : 'An unexpected error occurred.'}
            <button className="btn-secondary btn-small" onClick={() => summarizeMutation.reset()}>
              Dismiss
            </button>
          </div>
        )}

        {summaryData && (
          <SummaryView data={summaryData} onClose={() => setSummaryData(null)} />
        )}

        {results && (
          <JobList
            jobs={results.jobs}
            queryUsed={results.query_used}
            cached={results.cached}
            onSummarize={handleSummarize}
            isSummarizing={summarizeMutation.isPending}
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
