import { type FormEvent, useState } from 'react'
import { useJobStore } from '../store/jobStore'
import type { SearchRequest } from '../types'

interface SearchFormProps {
  onSearch: (params: SearchRequest) => void
  isLoading: boolean
}

const CATEGORIES = [
  '',
  'Software Engineering',
  'Data Science',
  'Product Management',
  'Design',
  'Marketing',
  'Sales',
  'Finance',
  'Human Resources',
  'Operations',
  'Other',
]

const DATE_OPTIONS: { label: string; value: SearchRequest['date_filter'] }[] = [
  { label: 'Any time', value: '' },
  { label: 'Past 24 hours', value: 'day' },
  { label: 'Past 3 days', value: '3days' },
  { label: 'Past week', value: 'week' },
  { label: 'Past month', value: 'month' },
]

export function SearchForm({ onSearch, isLoading }: SearchFormProps) {
  const { searchParams, setSearchParams, resetSearchParams } = useJobStore()
  const [keywordInput, setKeywordInput] = useState('')

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!searchParams.title.trim()) return
    onSearch(searchParams)
  }

  const addKeyword = () => {
    const kw = keywordInput.trim()
    if (kw && !searchParams.keywords.includes(kw)) {
      setSearchParams({ keywords: [...searchParams.keywords, kw] })
    }
    setKeywordInput('')
  }

  const removeKeyword = (kw: string) => {
    setSearchParams({
      keywords: searchParams.keywords.filter((k) => k !== kw),
    })
  }

  const handleKeywordKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      addKeyword()
    }
  }

  const handleReset = () => {
    resetSearchParams()
    setKeywordInput('')
  }

  return (
    <form className="search-form" onSubmit={handleSubmit}>
      <h2>Job Search</h2>

      <div className="form-grid">
        <div className="form-group">
          <label htmlFor="title">Job Title *</label>
          <input
            id="title"
            type="text"
            placeholder="e.g. Senior Software Engineer"
            value={searchParams.title}
            onChange={(e) => setSearchParams({ title: e.target.value })}
            required
            maxLength={200}
          />
        </div>

        <div className="form-group">
          <label htmlFor="category">Category</label>
          <select
            id="category"
            value={searchParams.category}
            onChange={(e) => setSearchParams({ category: e.target.value })}
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c || 'All Categories'}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="location">Location</label>
          <input
            id="location"
            type="text"
            placeholder="e.g. San Francisco, CA"
            value={searchParams.location}
            onChange={(e) => setSearchParams({ location: e.target.value })}
            maxLength={200}
          />
        </div>

        <div className="form-group">
          <label htmlFor="date_filter">Date Posted</label>
          <select
            id="date_filter"
            value={searchParams.date_filter}
            onChange={(e) =>
              setSearchParams({
                date_filter: e.target.value as SearchRequest['date_filter'],
              })
            }
          >
            {DATE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group form-group-wide">
          <label htmlFor="keywords">Keywords</label>
          <div className="keyword-input-row">
            <input
              id="keywords"
              type="text"
              placeholder="Add a keyword and press Enter"
              value={keywordInput}
              onChange={(e) => setKeywordInput(e.target.value)}
              onKeyDown={handleKeywordKeyDown}
            />
            <button type="button" onClick={addKeyword} className="btn-secondary">
              Add
            </button>
          </div>
          {searchParams.keywords.length > 0 && (
            <div className="keyword-tags">
              {searchParams.keywords.map((kw) => (
                <span key={kw} className="keyword-tag">
                  {kw}
                  <button
                    type="button"
                    onClick={() => removeKeyword(kw)}
                    aria-label={`Remove ${kw}`}
                  >
                    x
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="max_results">Max Results</label>
          <input
            id="max_results"
            type="number"
            min={1}
            max={100}
            value={searchParams.max_results}
            onChange={(e) =>
              setSearchParams({ max_results: Number(e.target.value) })
            }
          />
        </div>
      </div>

      <div className="form-actions">
        <button type="submit" className="btn-primary" disabled={isLoading || !searchParams.title.trim()}>
          {isLoading ? 'Searching...' : 'Search Jobs'}
        </button>
        <button type="button" className="btn-secondary" onClick={handleReset}>
          Reset
        </button>
      </div>
    </form>
  )
}
