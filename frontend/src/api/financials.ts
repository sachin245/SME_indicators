import { apiFetch } from './client'
import type { Financial } from '../types'

export const fetchFinancials = (params: Record<string, unknown>) =>
  apiFetch<Financial[]>('/api/financials', params)
