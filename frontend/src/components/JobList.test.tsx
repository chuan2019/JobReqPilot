import { describe, it, expect } from 'vitest'
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

describe('JobList', () => {
  it('renders all jobs', () => {
    render(<JobList jobs={mockJobs} queryUsed="test query" cached={false} />)

    expect(screen.getByText('Senior Engineer')).toBeInTheDocument()
    expect(screen.getByText('Junior Developer')).toBeInTheDocument()
    expect(screen.getByText('Tech Lead')).toBeInTheDocument()
  })

  it('shows result count', () => {
    render(<JobList jobs={mockJobs} queryUsed="" cached={false} />)
    expect(screen.getByText('Results (3)')).toBeInTheDocument()
  })

  it('shows cached badge when cached', () => {
    render(<JobList jobs={mockJobs} queryUsed="" cached={true} />)
    expect(screen.getByText('cached')).toBeInTheDocument()
  })

  it('shows no results message when empty', () => {
    render(<JobList jobs={[]} queryUsed="" cached={false} />)
    expect(screen.getByText(/no jobs found/i)).toBeInTheDocument()
  })

  it('displays match scores as percentages', () => {
    render(<JobList jobs={mockJobs} queryUsed="" cached={false} />)
    expect(screen.getByText('92%')).toBeInTheDocument()
    expect(screen.getByText('65%')).toBeInTheDocument()
    expect(screen.getByText('45%')).toBeInTheDocument()
  })

  it('sorts by title when column header is clicked', async () => {
    const user = userEvent.setup()
    render(<JobList jobs={mockJobs} queryUsed="" cached={false} />)

    // Click Title column to sort ascending
    await user.click(screen.getByText(/^Title/))

    const rows = screen.getAllByRole('row')
    // header row + 3 data rows; first data row should be Junior Developer (alphabetical)
    expect(rows[1]).toHaveTextContent('Junior Developer')
  })

  it('displays query used', () => {
    render(<JobList jobs={mockJobs} queryUsed="software engineer React" cached={false} />)
    expect(screen.getByText('software engineer React')).toBeInTheDocument()
  })
})
