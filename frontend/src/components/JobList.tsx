import { useState } from 'react'
import type { JobResult } from '../types'
import { JobCard } from './JobCard'
import { useJobStore } from '../store/jobStore'

interface JobListProps {
  jobs: JobResult[]
  queryUsed: string
  cached: boolean
  onSummarize: (jobIds: string[]) => void
  isSummarizing: boolean
}

type SortField = 'match_score' | 'title' | 'date_posted' | 'company'
type SortDir = 'asc' | 'desc'

export function JobList({ jobs, queryUsed, cached, onSummarize, isSummarizing }: JobListProps) {
  const [sortField, setSortField] = useState<SortField>('match_score')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const { selectedJobs, clearSelection } = useJobStore()

  const handleSort = (field: SortField) => {
    if (field === sortField) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortField(field)
      setSortDir(field === 'match_score' ? 'desc' : 'asc')
    }
  }

  const sorted = [...jobs].sort((a, b) => {
    const dir = sortDir === 'asc' ? 1 : -1
    if (sortField === 'match_score') {
      return (a.match_score - b.match_score) * dir
    }
    const aVal = a[sortField].toLowerCase()
    const bVal = b[sortField].toLowerCase()
    return aVal.localeCompare(bVal) * dir
  })

  const sortIndicator = (field: SortField) => {
    if (field !== sortField) return ''
    return sortDir === 'asc' ? ' ↑' : ' ↓'
  }

  return (
    <div className="job-list">
      <div className="job-list-header">
        <h2>
          Results ({jobs.length})
          {cached && <span className="badge-cached">cached</span>}
        </h2>
        {queryUsed && (
          <p className="query-used">
            Query: <code>{queryUsed}</code>
          </p>
        )}
        {selectedJobs.size > 0 && (
          <div className="selection-info">
            <span>{selectedJobs.size} selected</span>
            <button
              className="btn-primary btn-small"
              onClick={() => onSummarize([...selectedJobs])}
              disabled={isSummarizing}
            >
              {isSummarizing ? 'Summarizing...' : 'Summarize Selected'}
            </button>
            <button className="btn-secondary btn-small" onClick={clearSelection}>
              Clear
            </button>
          </div>
        )}
      </div>

      {jobs.length === 0 ? (
        <p className="no-results">No jobs found. Try adjusting your search criteria.</p>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th className="col-select"></th>
                <th className="col-rank">#</th>
                <th className="col-title sortable" onClick={() => handleSort('title')}>
                  Title{sortIndicator('title')}
                </th>
                <th className="col-company sortable" onClick={() => handleSort('company')}>
                  Company{sortIndicator('company')}
                </th>
                <th className="col-location">Location</th>
                <th className="col-score sortable" onClick={() => handleSort('match_score')}>
                  Score{sortIndicator('match_score')}
                </th>
                <th className="col-date sortable" onClick={() => handleSort('date_posted')}>
                  Posted{sortIndicator('date_posted')}
                </th>
                <th className="col-source">Source</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((job, i) => (
                <JobCard key={job.url} job={job} rank={i + 1} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
