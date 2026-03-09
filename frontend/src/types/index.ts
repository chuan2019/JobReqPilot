/** Mirrors backend SearchRequest Pydantic model. */
export interface SearchRequest {
  title: string
  category: string
  keywords: string[]
  location: string
  date_filter: '' | 'day' | '3days' | 'week' | 'month'
  max_results: number
}

/** Mirrors backend JobResult Pydantic model. */
export interface JobResult {
  title: string
  company: string
  url: string
  snippet: string
  jd_text: string
  date_posted: string
  source: string
  location: string
  match_score: number
}

/** Mirrors backend SearchResponse Pydantic model. */
export interface SearchResponse {
  jobs: JobResult[]
  total: number
  query_used: string
  cached: boolean
}
