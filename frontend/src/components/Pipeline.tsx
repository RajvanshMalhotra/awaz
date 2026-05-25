import { motion, AnimatePresence } from 'framer-motion'
import { useEffect } from 'react'
import { cn } from '@/lib/utils'
import type { RecorderState } from '@/hooks/useRecorder'

interface PipelineProps {
  recorderState: RecorderState
  formattedTime: string
  onToggle: () => void
  onReset: () => void
  relationship: string
  onRelationshipChange: (v: string) => void
  showReset: boolean
}

const RELATIONSHIPS = ['friend','best_friend','parent','sibling','romantic','colleague','boss','stranger']

export function Pipeline({ recorderState, formattedTime, onToggle, onReset, relationship, onRelationshipChange, showReset }: PipelineProps) {
  const isRecording = recorderState === 'recording'
  const isReady = recorderState === 'ready'

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.code === 'Space' && (e.target as HTMLElement).tagName !== 'INPUT' && (e.target as HTMLElement).tagName !== 'TEXTAREA') {
        e.preventDefault()
        onToggle()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onToggle])

  return (
    <div className="flex flex-col items-center gap-6">
      <div className="relative flex items-center justify-center">
        <AnimatePresence>
          {isRecording && (
            <motion.div
              className="absolute w-28 h-28 rounded-full bg-red-500/20"
              initial={{ scale: 0.8, opacity: 0.8 }}
              animate={{ scale: 1.6, opacity: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 1.4, repeat: Infinity, ease: 'easeOut' }}
            />
          )}
        </AnimatePresence>

        <motion.button
          onClick={onToggle}
          whileHover={{ scale: 1.06 }}
          whileTap={{ scale: 0.94 }}
          className={cn(
            'relative w-24 h-24 rounded-full flex items-center justify-center shadow-2xl transition-all duration-300 z-10',
            isRecording
              ? 'bg-gradient-to-br from-red-500 to-red-700 shadow-red-500/30'
              : 'bg-gradient-to-br from-indigo-500 to-purple-600 shadow-indigo-500/30',
          )}
          aria-label={isRecording ? 'Stop recording' : 'Start recording'}
        >
          {isRecording ? (
            <svg width="28" height="28" viewBox="0 0 24 24" fill="white">
              <rect x="6" y="6" width="12" height="12" rx="2.5" />
            </svg>
          ) : (
            <svg width="28" height="28" viewBox="0 0 24 24" fill="white">
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3zm-1 3a1 1 0 0 1 2 0v7a1 1 0 0 1-2 0V5zm8 5v1a7 7 0 0 1-14 0v-1H3v1a9 9 0 0 0 8 8.94V22h-3v2h8v-2h-3v-2.06A9 9 0 0 0 21 11v-1h-2z"/>
            </svg>
          )}
        </motion.button>
      </div>

      <div className="text-center space-y-1">
        {isRecording && (
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-red-400 text-sm font-semibold tabular-nums">
            {formattedTime}
          </motion.p>
        )}
        <p className="text-sm text-white/40">
          {isRecording ? 'Recording — click to stop' : isReady ? 'Ready — select a mood →' : 'Click to record · Space'}
        </p>
      </div>

      <div className="flex items-center gap-3">
        <label className="text-xs font-semibold uppercase tracking-widest text-white/30">Relationship</label>
        <select
          value={relationship}
          onChange={e => onRelationshipChange(e.target.value)}
          className="bg-white/5 border border-white/10 rounded-xl px-3 py-1.5 text-sm text-white/70 outline-none focus:border-indigo-500/50 transition-colors appearance-none cursor-pointer"
        >
          {RELATIONSHIPS.map(r => <option key={r} value={r}>{r.replace('_', ' ')}</option>)}
        </select>
      </div>

      <AnimatePresence>
        {showReset && (
          <motion.button
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            onClick={onReset}
            className="text-xs text-white/25 hover:text-white/50 transition-colors"
          >
            ↺ Record another
          </motion.button>
        )}
      </AnimatePresence>
    </div>
  )
}
