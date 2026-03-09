import { create } from 'zustand'
import type { SearchRequest } from '../types'

interface JobStore {
  /** Currently selected job IDs (URLs used as unique keys) for future summarization. */
  selectedJobs: Set<string>

  /** Current search parameters. */
  searchParams: SearchRequest

  /** Toggle a job's selection state. */
  toggleJob: (url: string) => void

  /** Clear all selections. */
  clearSelection: () => void

  /** Update search parameters. */
  setSearchParams: (params: Partial<SearchRequest>) => void

  /** Reset search parameters to defaults. */
  resetSearchParams: () => void
}

const defaultSearchParams: SearchRequest = {
  title: '',
  category: '',
  keywords: [],
  location: '',
  date_filter: '',
  max_results: 20,
}

export const useJobStore = create<JobStore>((set) => ({
  selectedJobs: new Set<string>(),
  searchParams: { ...defaultSearchParams },

  toggleJob: (url) =>
    set((state) => {
      const next = new Set(state.selectedJobs)
      if (next.has(url)) {
        next.delete(url)
      } else {
        next.add(url)
      }
      return { selectedJobs: next }
    }),

  clearSelection: () => set({ selectedJobs: new Set() }),

  setSearchParams: (params) =>
    set((state) => ({
      searchParams: { ...state.searchParams, ...params },
    })),

  resetSearchParams: () =>
    set({ searchParams: { ...defaultSearchParams } }),
}))
