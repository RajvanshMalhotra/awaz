import { useState, useCallback, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface ToastItem { id: number; message: string; type: 'ok' | 'err' }

let _push: ((msg: string, type: 'ok' | 'err') => void) | null = null

export function toast(message: string, type: 'ok' | 'err' = 'ok') {
  _push?.(message, type)
}

export function ToastProvider() {
  const [items, setItems] = useState<ToastItem[]>([])
  const counter = useRef(0)

  const push = useCallback((message: string, type: 'ok' | 'err') => {
    const id = ++counter.current
    setItems(prev => [...prev, { id, message, type }])
    setTimeout(() => setItems(prev => prev.filter(t => t.id !== id)), 3000)
  }, [])

  useEffect(() => {
    _push = push
    return () => { _push = null }
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
              item.type === 'ok'
                ? 'px-4 py-2.5 rounded-xl text-sm font-medium border bg-emerald-500/10 text-emerald-300 border-emerald-500/20 backdrop-blur-sm'
                : 'px-4 py-2.5 rounded-xl text-sm font-medium border bg-red-500/10 text-red-300 border-red-500/20 backdrop-blur-sm'
            }
          >
            {item.message}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}
