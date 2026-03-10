import axios from 'axios'
import type { SummarizeRequest, SummarizeResponse } from '../types'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

export async function postSummarize(request: SummarizeRequest): Promise<SummarizeResponse> {
  const { data } = await api.post<SummarizeResponse>('/summarize', request)
  return data
}
