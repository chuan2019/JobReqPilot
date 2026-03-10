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

/** Mirrors backend SummarizeRequest Pydantic model. */
export interface SummarizeRequest {
  job_ids: string[]
}

/** Mirrors backend RequirementItem Pydantic model. */
export interface RequirementItem {
  name: string
  frequency: number
}

/** Mirrors backend RequirementsSummary Pydantic model. */
export interface RequirementsSummary {
  technical_skills: RequirementItem[]
  soft_skills: RequirementItem[]
  education: RequirementItem[]
  certifications: RequirementItem[]
  experience: RequirementItem[]
  total_chunks_analyzed: number
}

/** Mirrors backend SummarizeResponse Pydantic model. */
export interface SummarizeResponse {
  summary: RequirementsSummary
  job_count: number
  cached: boolean
}
