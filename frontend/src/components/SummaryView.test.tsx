import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SummaryView } from './SummaryView'
import type { SummarizeResponse } from '../types'

const mockData: SummarizeResponse = {
  summary: {
    technical_skills: [
      { name: 'Python', frequency: 5 },
      { name: 'AWS', frequency: 3 },
      { name: 'Docker', frequency: 2 },
    ],
    soft_skills: [
      { name: 'Communication', frequency: 4 },
      { name: 'Teamwork', frequency: 2 },
    ],
    education: [
      { name: "Bachelor's in Computer Science", frequency: 3 },
    ],
    certifications: [
      { name: 'AWS Solutions Architect', frequency: 1 },
    ],
    experience: [
      { name: '3+ Years Software Development', frequency: 4 },
    ],
    total_chunks_analyzed: 8,
  },
  job_count: 5,
  cached: false,
}

describe('SummaryView', () => {
  it('renders the header with job count', () => {
    render(<SummaryView data={mockData} onClose={vi.fn()} />)
    expect(screen.getByText('Requirements Summary')).toBeInTheDocument()
    expect(screen.getByText(/analyzed 5 jobs/i)).toBeInTheDocument()
  })

  it('renders all requirement categories', () => {
    render(<SummaryView data={mockData} onClose={vi.fn()} />)
    expect(screen.getByText(/Technical Skills \(3\)/)).toBeInTheDocument()
    expect(screen.getByText(/Soft Skills \(2\)/)).toBeInTheDocument()
    expect(screen.getByText(/Education \(1\)/)).toBeInTheDocument()
    expect(screen.getByText(/Certifications \(1\)/)).toBeInTheDocument()
    expect(screen.getByText(/Experience \(1\)/)).toBeInTheDocument()
  })

  it('renders requirement items with frequencies', () => {
    render(<SummaryView data={mockData} onClose={vi.fn()} />)
    expect(screen.getByText('Python')).toBeInTheDocument()
    expect(screen.getByText('AWS')).toBeInTheDocument()
    expect(screen.getByText('Communication')).toBeInTheDocument()
  })

  it('shows cached badge when cached', () => {
    const cachedData = { ...mockData, cached: true }
    render(<SummaryView data={cachedData} onClose={vi.fn()} />)
    expect(screen.getByText('cached')).toBeInTheDocument()
  })

  it('calls onClose when close button is clicked', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    render(<SummaryView data={mockData} onClose={onClose} />)

    await user.click(screen.getByText('Close'))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('collapses category when header is clicked', async () => {
    const user = userEvent.setup()
    render(<SummaryView data={mockData} onClose={vi.fn()} />)

    // Python should be visible initially
    expect(screen.getByText('Python')).toBeInTheDocument()

    // Click Technical Skills header to collapse
    await user.click(screen.getByText(/Technical Skills \(3\)/))

    // Python should no longer be visible
    expect(screen.queryByText('Python')).not.toBeInTheDocument()
  })

  it('shows chunks analyzed count', () => {
    render(<SummaryView data={mockData} onClose={vi.fn()} />)
    expect(screen.getByText(/8 text chunks/)).toBeInTheDocument()
  })

  it('shows empty message when no requirements', () => {
    const emptyData: SummarizeResponse = {
      summary: {
        technical_skills: [],
        soft_skills: [],
        education: [],
        certifications: [],
        experience: [],
        total_chunks_analyzed: 0,
      },
      job_count: 0,
      cached: false,
    }
    render(<SummaryView data={emptyData} onClose={vi.fn()} />)
    expect(screen.getByText(/no requirements could be extracted/i)).toBeInTheDocument()
  })
})
