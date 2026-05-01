import { useCallback, useEffect, useState } from 'react'
import { fetchAdminContentQuality } from '@/services/api'
import type { AdminContentQualityResponse } from '@/types'

interface UseAdminContentQualityArgs {
  windowDays?: number
  includeArchived?: boolean
}

interface UseAdminContentQualityResult {
  data: AdminContentQualityResponse | null
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

export function useAdminContentQuality(
  args: UseAdminContentQualityArgs = {},
): UseAdminContentQualityResult {
  const { windowDays = 30, includeArchived = false } = args
  const [data, setData] = useState<AdminContentQualityResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetchAdminContentQuality({
        window_days: windowDays,
        include_archived: includeArchived,
      })
      setData(response)
    } catch (err) {
      setError((err as Error).message ?? 'Failed to load content quality')
    } finally {
      setLoading(false)
    }
  }, [windowDays, includeArchived])

  useEffect(() => {
    void refetch()
  }, [refetch])

  return { data, loading, error, refetch }
}
