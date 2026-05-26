import { useRef, useState, useCallback, useEffect } from 'react'

export function useLatency() {
  const [elapsed, setElapsed] = useState(0)
  const [frozen, setFrozen] = useState<number | null>(null)
  const [isRunning, setIsRunning] = useState(false)
  const startRef = useRef<number | null>(null)
  const rafRef = useRef<number | null>(null)

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
    }
  }, [])

  const tick = useCallback(() => {
    if (startRef.current === null) return
    setElapsed(Date.now() - startRef.current)
    rafRef.current = requestAnimationFrame(tick)
  }, [])

  const start = useCallback(() => {
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
    startRef.current = Date.now()
    setElapsed(0)
    setFrozen(null)
    setIsRunning(true)
    rafRef.current = requestAnimationFrame(tick)
  }, [tick])

  const stop = useCallback((): number => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current)
      rafRef.current = null
    }
    const final = startRef.current !== null ? Date.now() - startRef.current : 0
    startRef.current = null
    setFrozen(final)
    setIsRunning(false)
    return final
  }, [])

  const reset = useCallback(() => {
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
    rafRef.current = null
    startRef.current = null
    setElapsed(0)
    setFrozen(null)
    setIsRunning(false)
  }, [])

  const format = (ms: number) =>
    ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(2)}s`

  const displayMs = frozen ?? elapsed

  return {
    elapsed,
    frozen,
    isRunning,
    formatted: format(displayMs),
    displayMs,
    start,
    stop,
    reset,
    format,
  }
}
