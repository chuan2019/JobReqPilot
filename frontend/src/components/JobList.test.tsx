import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { JobList } from './JobList'
import type { JobResult } from '../types'

const mockJobs: JobResult[] = [
  {
    title: 'Senior Engineer',
    company: 'Acme Corp',
    url: 'https://example.com/job1',
    snippet: 'Great opportunity',
    jd_text: '',
    date_posted: '2 days ago',
    source: 'LinkedIn',
    location: 'Remote',
    match_score: 0.92,
  },
  {
    title: 'Junior Developer',
    company: 'Beta Inc',
    url: 'https://example.com/job2',
    snippet: 'Entry level',
    jd_text: '',
    date_posted: '1 week ago',
    source: 'Indeed',
    location: 'New York',
    match_score: 0.65,
  },
  {
    title: 'Tech Lead',
    company: 'Gamma LLC',
    url: 'https://example.com/job3',
    snippet: 'Leadership role',
    jd_text: '',
    date_posted: '3 days ago',
    source: 'Glassdoor',
    location: 'San Francisco',
    match_score: 0.45,
  },
]

const defaultProps = {
  jobs: mockJobs,
  queryUsed: '',
  cached: false,
  onSummarize: vi.fn(),
  isSummarizing: false,
}

describe('JobList', () => {
  it('renders all jobs', () => {
    render(<JobList {...defaultProps} queryUsed="test query" />)

    expect(screen.getByText('Senior Engineer')).toBeInTheDocument()
    expect(screen.getByText('Junior Developer')).toBeInTheDocument()
    expect(screen.getByText('Tech Lead')).toBeInTheDocument()
  })

  it('shows result count', () => {
    render(<JobList {...defaultProps} />)
    expect(screen.getByText('Results (3)')).toBeInTheDocument()
  })

  it('shows cached badge when cached', () => {
    render(<JobList {...defaultProps} cached={true} />)
    expect(screen.getByText('cached')).toBeInTheDocument()
  })

  it('shows no results message when empty', () => {
    render(<JobList {...defaultProps} jobs={[]} />)
    expect(screen.getByText(/no jobs found/i)).toBeInTheDocument()
  })

  it('displays match scores as percentages', () => {
    render(<JobList {...defaultProps} />)
    expect(screen.getByText('92%')).toBeInTheDocument()
    expect(screen.getByText('65%')).toBeInTheDocument()
    expect(screen.getByText('45%')).toBeInTheDocument()
  })

  it('sorts by title when column header is clicked', async () => {
    const user = userEvent.setup()
    render(<JobList {...defaultProps} />)

    // Click Title column to sort ascending
    await user.click(screen.getByText(/^Title/))

    const rows = screen.getAllByRole('row')
    // header row + 3 data rows; first data row should be Junior Developer (alphabetical)
    expect(rows[1]).toHaveTextContent('Junior Developer')
  })

  it('displays query used', () => {
    render(<JobList {...defaultProps} queryUsed="software engineer React" />)
    expect(screen.getByText('software engineer React')).toBeInTheDocument()
  })
})
