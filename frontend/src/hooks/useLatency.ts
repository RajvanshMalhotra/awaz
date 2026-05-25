import { useRef, useState, useCallback } from 'react'

export function useLatency() {
  const [elapsed, setElapsed] = useState(0)
  const [frozen, setFrozen] = useState<number | null>(null)
  const startRef = useRef<number | null>(null)
  const rafRef = useRef<number | null>(null)

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
    return final
  }, [])

  const reset = useCallback(() => {
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
    rafRef.current = null
    startRef.current = null
    setElapsed(0)
    setFrozen(null)
  }, [])

  const format = (ms: number) =>
    ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(2)}s`

  const displayMs = frozen ?? elapsed

  return {
    elapsed,
    frozen,
    isRunning: rafRef.current !== null,
    formatted: format(displayMs),
    displayMs,
    start,
    stop,
    reset,
    format,
  }
}
