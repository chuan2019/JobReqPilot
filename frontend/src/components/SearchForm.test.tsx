import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SearchForm } from './SearchForm'
import { useJobStore } from '../store/jobStore'

describe('SearchForm', () => {
  beforeEach(() => {
    useJobStore.getState().resetSearchParams()
  })

  it('renders all form fields', () => {
    render(<SearchForm onSearch={vi.fn()} isLoading={false} />)

    expect(screen.getByLabelText(/job title/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/category/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/location/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/date posted/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/keywords/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/max results/i)).toBeInTheDocument()
  })

  it('disables submit when title is empty', () => {
    render(<SearchForm onSearch={vi.fn()} isLoading={false} />)
    const btn = screen.getByRole('button', { name: /search jobs/i })
    expect(btn).toBeDisabled()
  })

  it('calls onSearch with params when submitted', async () => {
    const user = userEvent.setup()
    const onSearch = vi.fn()
    render(<SearchForm onSearch={onSearch} isLoading={false} />)

    await user.type(screen.getByLabelText(/job title/i), 'Software Engineer')
    await user.click(screen.getByRole('button', { name: /search jobs/i }))

    expect(onSearch).toHaveBeenCalledTimes(1)
    expect(onSearch.mock.calls[0][0].title).toBe('Software Engineer')
  })

  it('shows loading state', () => {
    render(<SearchForm onSearch={vi.fn()} isLoading={true} />)
    expect(screen.getByRole('button', { name: /searching/i })).toBeDisabled()
  })

  it('adds and removes keywords', async () => {
    const user = userEvent.setup()
    render(<SearchForm onSearch={vi.fn()} isLoading={false} />)

    const kwInput = screen.getByLabelText(/keywords/i)
    await user.type(kwInput, 'React{enter}')

    expect(screen.getByText('React')).toBeInTheDocument()

    await user.click(screen.getByLabelText(/remove react/i))
    expect(screen.queryByText('React')).not.toBeInTheDocument()
  })

  it('resets form on Reset button click', async () => {
    const user = userEvent.setup()
    render(<SearchForm onSearch={vi.fn()} isLoading={false} />)

    const titleInput = screen.getByLabelText(/job title/i)
    await user.type(titleInput, 'Developer')
    expect(titleInput).toHaveValue('Developer')

    await user.click(screen.getByRole('button', { name: /reset/i }))
    expect(titleInput).toHaveValue('')
  })
})
