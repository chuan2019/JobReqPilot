import { lazy, Suspense, useRef, useState } from 'react'
import { QueryClient, QueryClientProvider, useMutation } from '@tanstack/react-query'
import { SearchForm } from './components/SearchForm'
import { JobList } from './components/JobList'

const SummaryView = lazy(() =>
  import('./components/SummaryView').then((m) => ({ default: m.SummaryView }))
)
import { postSearch } from './api/search'
import { postSummarize } from './api/summarize'
import type { SearchRequest, SearchResponse, SummarizeResponse } from './types'
import './App.css'

const queryClient = new QueryClient()

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    // Axios wraps the response body in error.response.data
    const axiosError = error as { response?: { data?: { error?: string; detail?: string } } }
    if (axiosError.response?.data?.error) {
      const detail = axiosError.response.data.detail
      return detail
        ? `${axiosError.response.data.error}: ${detail}`
        : axiosError.response.data.error
    }
    return error.message
  }
  return 'An unexpected error occurred.'
}

function SearchPage() {
  const [results, setResults] = useState<SearchResponse | null>(null)
  const [summaryData, setSummaryData] = useState<SummarizeResponse | null>(null)
  const lastSearchParams = useRef<SearchRequest | null>(null)
  const lastSummarizeIds = useRef<string[] | null>(null)

  const searchMutation = useMutation({
    mutationFn: postSearch,
    onSuccess: (data) => {
      setResults(data)
      setSummaryData(null)
    },
  })

  const summarizeMutation = useMutation({
    mutationFn: postSummarize,
    onSuccess: (data) => setSummaryData(data),
  })

  const handleSearch = (params: SearchRequest) => {
    lastSearchParams.current = params
    searchMutation.mutate(params)
  }

  const handleSummarize = (jobIds: string[]) => {
    lastSummarizeIds.current = jobIds
    summarizeMutation.mutate({ job_ids: jobIds })
  }

  const retrySearch = () => {
    if (lastSearchParams.current) {
      searchMutation.mutate(lastSearchParams.current)
    }
  }

  const retrySummarize = () => {
    if (lastSummarizeIds.current) {
      summarizeMutation.mutate({ job_ids: lastSummarizeIds.current })
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>JobReqPilot</h1>
        <p>AI-powered job search and requirements analysis</p>
      </header>

      <main>
        <SearchForm onSearch={handleSearch} isLoading={searchMutation.isPending} />

        {searchMutation.isPending && (
          <div className="loading-banner">
            <span className="spinner" />
            <span>Searching job boards and scoring results...</span>
          </div>
        )}

        {searchMutation.isError && (
          <div className="error-banner">
            <span>
              <strong>Search failed:</strong> {getErrorMessage(searchMutation.error)}
            </span>
            <div className="error-actions">
              <button className="btn-primary btn-small" onClick={retrySearch}>
                Retry
              </button>
              <button className="btn-secondary btn-small" onClick={() => searchMutation.reset()}>
                Dismiss
              </button>
            </div>
          </div>
        )}

        {summarizeMutation.isPending && (
          <div className="loading-banner">
            <span className="spinner" />
            <span>Analyzing job descriptions and extracting requirements...</span>
          </div>
        )}

        {summarizeMutation.isError && (
          <div className="error-banner">
            <span>
              <strong>Summarize failed:</strong> {getErrorMessage(summarizeMutation.error)}
            </span>
            <div className="error-actions">
              <button className="btn-primary btn-small" onClick={retrySummarize}>
                Retry
              </button>
              <button className="btn-secondary btn-small" onClick={() => summarizeMutation.reset()}>
                Dismiss
              </button>
            </div>
          </div>
        )}

        {summaryData && (
          <Suspense fallback={<div className="loading-banner"><span className="spinner" /><span>Loading summary...</span></div>}>
            <SummaryView data={summaryData} onClose={() => setSummaryData(null)} />
          </Suspense>
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
