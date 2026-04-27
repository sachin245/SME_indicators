import { apiFetch } from './client'
import type { IndicatorRow } from '../types'

export const fetchLatestIndicators = () =>
  apiFetch<IndicatorRow[]>('/api/indicators/latest')

export const fetchIndicatorHistory = (params: {
  sector?: string
  from_date?: string
  to_date?: string
}) => apiFetch<IndicatorRow[]>('/api/indicators', params)

export const fetchSectors = () =>
  apiFetch<{ sector: string }[]>('/api/sectors')
