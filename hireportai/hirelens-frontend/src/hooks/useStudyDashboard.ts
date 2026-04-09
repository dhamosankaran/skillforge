import { useState, useEffect, useCallback } from 'react'
import { fetchCategories } from '@/services/api'
import { useUsage } from '@/context/UsageContext'
import type { Category } from '@/types'

interface UseStudyDashboardResult {
  categories: Category[]
  isLoading: boolean
  error: Error | null
  refetch: () => void
}

export function useStudyDashboard(): UseStudyDashboardResult {
  const { usage } = useUsage()
  const isFree = usage.plan === 'free'

  const [categories, setCategories] = useState<Category[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const load = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await fetchCategories()
      // Derive locked state client-side: any non-foundation category is locked
      // for free-plan users. Once GET /api/v1/study/dashboard is deployed, the
      // API will return this flag directly and also include premium categories
      // (not just foundation ones) so free users can see locked tiles.
      const enriched = data.categories.map((cat) => ({
        ...cat,
        studied_count: cat.studied_count ?? 0,
        locked: isFree && cat.source !== 'foundation',
      }))
      setCategories(enriched)
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to load categories'))
    } finally {
      setIsLoading(false)
    }
  }, [isFree])

  useEffect(() => {
    load()
  }, [load])

  return { categories, isLoading, error, refetch: load }
}
