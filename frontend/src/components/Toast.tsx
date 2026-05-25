import { useState, useCallback, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface ToastItem { id: number; message: string; type: 'success' | 'error' | 'info' }

let _push: ((msg: string, type: 'success' | 'error' | 'info') => void) | null = null

export function toast(message: string, type: 'success' | 'error' | 'info' = 'info') {
  _push?.(message, type)
}

export function ToastProvider() {
  const [items, setItems] = useState<ToastItem[]>([])
  const counter = useRef(0)
  const timers = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map())

  const push = useCallback((message: string, type: 'success' | 'error' | 'info') => {
    const id = ++counter.current
    setItems(prev => [...prev, { id, message, type }])
    const t = setTimeout(() => {
      setItems(prev => prev.filter(item => item.id !== id))
      timers.current.delete(id)
    }, 3000)
    timers.current.set(id, t)
  }, [])

  useEffect(() => {
    _push = push
    return () => {
      _push = null
      timers.current.forEach(t => clearTimeout(t))
      timers.current.clear()
    }
  }, [push])

  return (
    <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-[200] flex flex-col gap-2 pointer-events-none items-center">
      <AnimatePresence>
        {items.map(item => (
          <motion.div
            key={item.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ type: 'spring', stiffness: 400, damping: 30 }}
            className={
              item.type === 'success'
                ? 'px-4 py-2.5 rounded-xl text-sm font-medium border bg-emerald-500/10 text-emerald-300 border-emerald-500/20 backdrop-blur-sm'
                : item.type === 'error'
                ? 'px-4 py-2.5 rounded-xl text-sm font-medium border bg-red-500/10 text-red-300 border-red-500/20 backdrop-blur-sm'
                : 'px-4 py-2.5 rounded-xl text-sm font-medium border bg-blue-500/10 text-blue-300 border-blue-500/20 backdrop-blur-sm'
            }
          >
            {item.message}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}
