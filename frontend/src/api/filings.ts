import { apiFetch } from './client'
import type { Filing, Company, SignalTrend, PagedResponse } from '../types'

export const fetchFilings = (params: Record<string, unknown>) =>
  apiFetch<PagedResponse<Filing>>('/api/filings', params)

export const fetchCompanies = (params: Record<string, unknown>) =>
  apiFetch<PagedResponse<Company>>('/api/companies', params)

export const fetchCategories = () =>
  apiFetch<{ category: string }[]>('/api/filings/categories')

export const fetchSignalTrend = (params: Record<string, unknown>) =>
  apiFetch<SignalTrend[]>('/api/signals/trend', params)
