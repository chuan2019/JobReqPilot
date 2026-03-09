import axios from 'axios'
import type { SearchRequest, SearchResponse } from '../types'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

export async function postSearch(request: SearchRequest): Promise<SearchResponse> {
  const { data } = await api.post<SearchResponse>('/search', request)
  return data
}
