import { useState, useEffect, useCallback } from 'react'
import {
  getApplications,
  createApplication,
  updateApplication,
  deleteApplication,
} from '@/services/api'
import type { TrackerApplication, ApplicationStatus } from '@/types'

export function useTracker() {
  const [applications, setApplications] = useState<TrackerApplication[]>([])
  const [isLoading, setIsLoading] = useState(false)

  const load = useCallback(async () => {
    setIsLoading(true)
    try {
      const apps = await getApplications()
      setApplications(apps)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const add = useCallback(
    async (data: Omit<TrackerApplication, 'id' | 'created_at'>) => {
      const app = await createApplication(data)
      setApplications((prev) => [app, ...prev])
      return app
    },
    []
  )

  const update = useCallback(
    async (id: string, data: Partial<Omit<TrackerApplication, 'id' | 'created_at'>>) => {
      const updated = await updateApplication(id, data)
      setApplications((prev) => prev.map((a) => (a.id === id ? updated : a)))
      return updated
    },
    []
  )

  const remove = useCallback(async (id: string) => {
    await deleteApplication(id)
    setApplications((prev) => prev.filter((a) => a.id !== id))
  }, [])

  const moveStatus = useCallback(
    async (id: string, status: ApplicationStatus) => {
      await update(id, { status })
    },
    [update]
  )

  return { applications, isLoading, add, update, remove, moveStatus, reload: load }
}
