import { useState, useEffect } from 'react'
import { fetchPricing } from '@/services/api'

export interface Pricing {
  currency: string
  price: number
  price_display: string
  stripe_price_id: string
}

const DEFAULT_PRICING: Pricing = {
  currency: 'usd',
  price: 49,
  price_display: '$49/mo',
  stripe_price_id: '',
}

export function usePricing() {
  const [pricing, setPricing] = useState<Pricing>(DEFAULT_PRICING)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    fetchPricing()
      .then((data) => {
        if (!cancelled) setPricing(data)
      })
      .catch(() => {
        // Keep USD defaults on failure
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  return { pricing, isLoading }
}
