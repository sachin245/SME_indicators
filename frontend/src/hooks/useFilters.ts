import { useSearchParams } from 'react-router-dom'
import { subDays, format } from 'date-fns'

const today = format(new Date(), 'yyyy-MM-dd')
const ninetyDaysAgo = format(subDays(new Date(), 90), 'yyyy-MM-dd')

export function useFilters() {
  const [searchParams, setSearchParams] = useSearchParams()

  const from = searchParams.get('from') ?? ninetyDaysAgo
  const to = searchParams.get('to') ?? today
  const exchange = searchParams.getAll('exchange')

  function setFrom(val: string) {
    setSearchParams((prev) => { prev.set('from', val); return prev }, { replace: true })
  }
  function setTo(val: string) {
    setSearchParams((prev) => { prev.set('to', val); return prev }, { replace: true })
  }
  function toggleExchange(val: string) {
    setSearchParams((prev) => {
      const current = prev.getAll('exchange')
      prev.delete('exchange')
      if (current.includes(val)) {
        current.filter((e) => e !== val).forEach((e) => prev.append('exchange', e))
      } else {
        [...current, val].forEach((e) => prev.append('exchange', e))
      }
      return prev
    }, { replace: true })
  }

  return { from, to, exchange, setFrom, setTo, toggleExchange }
}
