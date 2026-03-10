import { useState } from 'react'
import type { RequirementItem, SummarizeResponse } from '../types'

interface SummaryViewProps {
  data: SummarizeResponse
  onClose: () => void
}

interface CategorySectionProps {
  title: string
  items: RequirementItem[]
  maxFrequency: number
}

function CategorySection({ title, items, maxFrequency }: CategorySectionProps) {
  const [expanded, setExpanded] = useState(true)

  if (items.length === 0) return null

  return (
    <div className="summary-category">
      <button
        className="summary-category-header"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="summary-category-title">
          {title} ({items.length})
        </span>
        <span className="summary-category-toggle">{expanded ? '−' : '+'}</span>
      </button>

      {expanded && (
        <ul className="summary-items">
          {items.map((item) => (
            <li key={item.name} className="summary-item">
              <span className="summary-item-name">{item.name}</span>
              <span className="summary-item-bar-container">
                <span
                  className="summary-item-bar"
                  style={{ width: `${(item.frequency / maxFrequency) * 100}%` }}
                />
              </span>
              <span className="summary-item-freq">{item.frequency}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function SummaryView({ data, onClose }: SummaryViewProps) {
  const { summary, job_count, cached } = data

  // Find the global max frequency for bar scaling
  const allItems = [
    ...summary.technical_skills,
    ...summary.soft_skills,
    ...summary.education,
    ...summary.certifications,
    ...summary.experience,
  ]
  const maxFrequency = Math.max(1, ...allItems.map((i) => i.frequency))

  const categories: { title: string; items: RequirementItem[] }[] = [
    { title: 'Technical Skills', items: summary.technical_skills },
    { title: 'Soft Skills', items: summary.soft_skills },
    { title: 'Experience', items: summary.experience },
    { title: 'Education', items: summary.education },
    { title: 'Certifications', items: summary.certifications },
  ]

  const totalRequirements = allItems.length

  return (
    <div className="summary-view">
      <div className="summary-header">
        <div>
          <h2>
            Requirements Summary
            {cached && <span className="badge-cached">cached</span>}
          </h2>
          <p className="summary-meta">
            Analyzed {job_count} job{job_count !== 1 ? 's' : ''} &middot;{' '}
            {summary.total_chunks_analyzed} text chunk
            {summary.total_chunks_analyzed !== 1 ? 's' : ''} &middot;{' '}
            {totalRequirements} unique requirement
            {totalRequirements !== 1 ? 's' : ''}
          </p>
        </div>
        <button className="btn-secondary btn-small" onClick={onClose}>
          Close
        </button>
      </div>

      {totalRequirements === 0 ? (
        <p className="no-results">
          No requirements could be extracted from the selected jobs.
        </p>
      ) : (
        <div className="summary-categories">
          {categories.map((cat) => (
            <CategorySection
              key={cat.title}
              title={cat.title}
              items={cat.items}
              maxFrequency={maxFrequency}
            />
          ))}
        </div>
      )}
    </div>
  )
}
