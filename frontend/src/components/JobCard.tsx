import type { JobResult } from '../types'
import { useJobStore } from '../store/jobStore'

interface JobCardProps {
  job: JobResult
  rank: number
}

function formatScore(score: number): string {
  return `${Math.round(score * 100)}%`
}

function scoreClass(score: number): string {
  if (score >= 0.8) return 'score-high'
  if (score >= 0.5) return 'score-mid'
  return 'score-low'
}

export function JobCard({ job, rank }: JobCardProps) {
  const { selectedJobs, toggleJob } = useJobStore()
  const isSelected = selectedJobs.has(job.url)

  return (
    <tr className={`job-card ${isSelected ? 'job-selected' : ''}`}>
      <td className="col-select">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={() => toggleJob(job.url)}
          aria-label={`Select ${job.title}`}
        />
      </td>
      <td className="col-rank">{rank}</td>
      <td className="col-title">
        <a href={job.url} target="_blank" rel="noopener noreferrer">
          {job.title}
        </a>
      </td>
      <td className="col-company">{job.company}</td>
      <td className="col-location">{job.location}</td>
      <td className={`col-score ${scoreClass(job.match_score)}`}>
        {formatScore(job.match_score)}
      </td>
      <td className="col-date">{job.date_posted}</td>
      <td className="col-source">{job.source}</td>
    </tr>
  )
}
