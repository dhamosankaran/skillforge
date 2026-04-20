import { useEffect } from 'react'
import type { RefObject } from 'react'

export function useClickOutside(
  refs: Array<RefObject<HTMLElement>>,
  enabled: boolean,
  onOutside: () => void,
): void {
  useEffect(() => {
    if (!enabled) return
    function handler(event: MouseEvent | TouchEvent) {
      const target = event.target as Node | null
      if (!target) return
      for (const ref of refs) {
        if (ref.current && ref.current.contains(target)) return
      }
      onOutside()
    }
    document.addEventListener('mousedown', handler)
    document.addEventListener('touchstart', handler)
    return () => {
      document.removeEventListener('mousedown', handler)
      document.removeEventListener('touchstart', handler)
    }
  }, [refs, enabled, onOutside])
}
