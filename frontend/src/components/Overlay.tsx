import { motion, AnimatePresence } from 'framer-motion'
import { useLatency } from '@/hooks/useLatency'
import { useEffect } from 'react'

interface OverlayProps { isVisible: boolean; message: string }

export function Overlay({ isVisible, message }: OverlayProps) {
  const { start, stop, formatted } = useLatency()

  useEffect(() => {
    if (isVisible) start()
    else stop()
  }, [isVisible, start, stop])

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
          className="fixed inset-0 z-[100] flex flex-col items-center justify-center gap-3 bg-black/85 backdrop-blur-md"
        >
          <div className="w-10 h-10 rounded-full border-2 border-white/10 border-t-indigo-400 animate-spin" />
          <p className="text-sm text-white/60">{message}</p>
          <p className="text-3xl font-bold tabular-nums text-white tracking-tight">
            {formatted}
          </p>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
