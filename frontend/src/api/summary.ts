import { apiFetch } from './client'
import type { Summary } from '../types'

export const fetchSummary = (params: Record<string, unknown>) =>
  apiFetch<Summary>('/api/summary', params)
