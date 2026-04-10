import { useState, useEffect, useCallback } from 'react'
import {
  fetchActiveMission,
  fetchMissionDaily,
  completeMissionDay,
  createMission,
  fetchCategories,
} from '@/services/api'
import type {
  MissionDetailResponse,
  MissionDailyResponse,
  MissionDayCompleteResponse,
  MissionCreateRequest,
  MissionResponse,
  Category,
} from '@/types'

interface UseMissionResult {
  mission: MissionDetailResponse | null
  daily: MissionDailyResponse | null
  categories: Category[]
  isLoading: boolean
  error: string | null
  noMission: boolean
  create: (req: MissionCreateRequest) => Promise<MissionResponse>
  completeDay: () => Promise<MissionDayCompleteResponse>
  refresh: () => void
  refreshDaily: () => void
}

export function useMission(): UseMissionResult {
  const [mission, setMission] = useState<MissionDetailResponse | null>(null)
  const [daily, setDaily] = useState<MissionDailyResponse | null>(null)
  const [categories, setCategories] = useState<Category[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [noMission, setNoMission] = useState(false)

  const loadMission = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    setNoMission(false)
    try {
      const data = await fetchActiveMission()
      setMission(data)
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status === 404) {
        setNoMission(true)
      } else {
        setError('Failed to load mission')
      }
    } finally {
      setIsLoading(false)
    }
  }, [])

  const loadDaily = useCallback(async () => {
    try {
      const data = await fetchMissionDaily()
      setDaily(data)
    } catch {
      // Daily load failure is non-fatal — mission view still works
    }
  }, [])

  const loadCategories = useCallback(async () => {
    try {
      const data = await fetchCategories()
      setCategories(data.categories)
    } catch {
      // Categories failure handled in setup form
    }
  }, [])

  useEffect(() => {
    loadMission()
    loadCategories()
  }, [loadMission, loadCategories])

  useEffect(() => {
    if (mission && mission.status === 'active') {
      loadDaily()
    }
  }, [mission, loadDaily])

  const create = useCallback(async (req: MissionCreateRequest) => {
    const result = await createMission(req)
    await loadMission()
    return result
  }, [loadMission])

  const doCompleteDay = useCallback(async () => {
    const result = await completeMissionDay()
    await loadMission()
    await loadDaily()
    return result
  }, [loadMission, loadDaily])

  return {
    mission,
    daily,
    categories,
    isLoading,
    error,
    noMission,
    create,
    completeDay: doCompleteDay,
    refresh: loadMission,
    refreshDaily: loadDaily,
  }
}
