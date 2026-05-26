import { cn } from '@/lib/utils'
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion'
import { useState, useEffect, useRef } from 'react'

export interface Mood {
  id: string
  emoji: string
  name: string
  bg: string
  gradientColors: string
}

export const MOODS: Mood[] = [
  { id: 'auto',      emoji: '🎭', name: 'Auto',      bg: 'bg-violet-300', gradientColors: '#c4b5fd, #ede9fe' },
  { id: 'happy',     emoji: '😊', name: 'Happy',     bg: 'bg-yellow-300', gradientColors: '#fde047, #fef9c3' },
  { id: 'excited',   emoji: '🤩', name: 'Excited',   bg: 'bg-orange-300', gradientColors: '#fdba74, #fff7ed' },
  { id: 'sarcastic', emoji: '😏', name: 'Sarcastic', bg: 'bg-emerald-300', gradientColors: '#6ee7b7, #d1fae5' },
  { id: 'sad',       emoji: '😢', name: 'Sad',       bg: 'bg-blue-300',   gradientColors: '#93c5fd, #eff6ff' },
  { id: 'angry',     emoji: '😠', name: 'Angry',     bg: 'bg-red-300',    gradientColors: '#fca5a5, #fef2f2' },
]

export interface VerticalMoodDockProps {
  canProcess: boolean
  onProcess: (moodId: string, extraText: string) => void
  className?: string
}

export function VerticalMoodDock({ canProcess, onProcess, className }: VerticalMoodDockProps) {
  const shouldReduceMotion = useReducedMotion()
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null)
  const [extraText, setExtraText] = useState('')
  const dockRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const selectedMood = selectedIdx !== null ? MOODS[selectedIdx] : null
  const isExpanded = selectedIdx !== null

  useEffect(() => {
    if (!isExpanded) return
    const id = setTimeout(() => inputRef.current?.focus(), 200)
    return () => clearTimeout(id)
  }, [isExpanded])

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dockRef.current && !dockRef.current.contains(e.target as Node)) {
        setSelectedIdx(null)
        setExtraText('')
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleSelect = (idx: number) => {
    setSelectedIdx(prev => (prev === idx ? null : idx))
    setExtraText('')
  }

  const handleSend = () => {
    if (!canProcess || selectedIdx === null) return
    onProcess(MOODS[selectedIdx].id, extraText)
    setSelectedIdx(null)
    setExtraText('')
  }

  const springFast = { type: 'spring' as const, stiffness: 420, damping: 32 }
  const hoverAnim = shouldReduceMotion ? {} : { scale: 1.12, x: -4, transition: springFast }

  return (
    <div ref={dockRef} className={cn('fixed right-6 top-1/2 -translate-y-1/2 z-50 flex items-center gap-3', className)}>
      <AnimatePresence>
        {isExpanded && selectedMood && (
          <motion.div
            key="panel"
            initial={{ opacity: 0, x: 24, scaleX: 0.85 }}
            animate={{ opacity: 1, x: 0, scaleX: 1 }}
            exit={{ opacity: 0, x: 24, scaleX: 0.85 }}
            transition={springFast}
            style={{
              originX: 1,
              background: `linear-gradient(135deg, ${selectedMood.gradientColors})`,
            }}
            className="w-64 rounded-2xl px-4 py-4 shadow-2xl border border-white/40"
          >
            <div className="flex items-center gap-2 mb-3">
              <span className="text-2xl">{selectedMood.emoji}</span>
              <div>
                <p className="text-xs font-semibold uppercase tracking-widest text-gray-500">Mood</p>
                <p className="text-sm font-bold text-gray-800 leading-none">{selectedMood.name}</p>
              </div>
            </div>

            <input
              ref={inputRef}
              type="text"
              value={extraText}
              onChange={e => setExtraText(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') handleSend()
                if (e.key === 'Escape') {
                  setSelectedIdx(null)
                  setExtraText('')
                }
              }}
              placeholder="Extra context… (optional)"
              className="w-full rounded-xl bg-white/60 border border-white/50 px-3 py-2 text-sm text-gray-700 placeholder-gray-400 outline-none focus:bg-white/80 transition-colors"
            />

            <motion.button
              onClick={handleSend}
              disabled={!canProcess}
              whileHover={canProcess ? { scale: 1.03 } : {}}
              whileTap={canProcess ? { scale: 0.97 } : {}}
              className="mt-2 w-full rounded-xl bg-white/70 hover:bg-white py-2 text-sm font-semibold text-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
              {canProcess ? 'Generate Response' : 'Record first'}
              {canProcess && (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              )}
            </motion.button>
          </motion.div>
        )}
      </AnimatePresence>

      <motion.div
        initial={{ opacity: 0, x: 60 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ type: 'spring', stiffness: 300, damping: 28, delay: 0.2 }}
        className="rounded-full px-2 py-3 bg-white dark:bg-neutral-900 shadow-2xl border border-gray-200/60 dark:border-neutral-700/60 flex flex-col items-center gap-1.5"
      >
        <motion.button
          className={cn(
            'w-11 h-11 flex items-center justify-center rounded-full transition-shadow',
            selectedIdx === 0 ? 'bg-white shadow-lg ring-2 ring-white/80' : MOODS[0].bg,
          )}
          animate={{
            opacity: isExpanded && selectedIdx !== 0 ? 0.35 : 1,
            scale: selectedIdx === 0 ? 1.15 : 1,
          }}
          transition={springFast}
          whileHover={!isExpanded ? hoverAnim : { scale: 1.08 }}
          whileTap={{ scale: 0.92 }}
          onClick={() => handleSelect(0)}
          aria-label="Auto mood"
        >
          <span className="text-2xl">{MOODS[0].emoji}</span>
        </motion.button>

        <div className="w-6 h-px bg-gray-200 dark:bg-neutral-700 my-0.5" />

        {MOODS.slice(1).map((mood, i) => {
          const idx = i + 1
          const isSelected = selectedIdx === idx
          return (
            <motion.button
              key={mood.id}
              className={cn(
                'relative w-10 h-10 rounded-full flex items-center justify-center text-xl transition-shadow',
                isSelected ? 'bg-white shadow-lg ring-2 ring-white/80' : mood.bg,
              )}
              onClick={() => handleSelect(idx)}
              animate={{
                opacity: isExpanded && !isSelected ? 0.35 : 1,
                scale: isSelected ? 1.15 : 1,
              }}
              transition={springFast}
              whileHover={!isExpanded ? hoverAnim : { scale: 1.08 }}
              whileTap={{ scale: 0.92 }}
              aria-label={`${mood.name} mood`}
            >
              {mood.emoji}
              <motion.div
                className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-green-400 border-2 border-white rounded-full"
                initial={{ scale: 0 }}
                animate={{ scale: isExpanded && !isSelected ? 0 : 1 }}
                transition={{ type: 'spring', stiffness: 500, damping: 30, delay: isSelected ? 0.2 : 0 }}
              />
            </motion.button>
          )
        })}

        <div className="w-6 h-px bg-gray-200 dark:bg-neutral-700 my-0.5" />

        <motion.button
          className="w-11 h-11 flex items-center justify-center text-gray-400 dark:text-neutral-500"
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.92 }}
          onClick={() => {
            setSelectedIdx(null)
            setExtraText('')
          }}
          aria-label={isExpanded ? 'Close' : 'Menu'}
        >
          <AnimatePresence mode="wait">
            {isExpanded ? (
              <motion.svg
                key="x"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                initial={{ rotate: -90, opacity: 0 }}
                animate={{ rotate: 0, opacity: 1 }}
                exit={{ rotate: 90, opacity: 0 }}
                transition={{ duration: 0.15 }}
              >
                <path d="M18 6L6 18M6 6l12 12" />
              </motion.svg>
            ) : (
              <motion.svg
                key="menu"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                initial={{ rotate: 90, opacity: 0 }}
                animate={{ rotate: 0, opacity: 1 }}
                exit={{ rotate: -90, opacity: 0 }}
                transition={{ duration: 0.15 }}
              >
                <line x1="4" y1="6" x2="20" y2="6" />
                <line x1="4" y1="12" x2="20" y2="12" />
                <line x1="4" y1="18" x2="20" y2="18" />
              </motion.svg>
            )}
          </AnimatePresence>
        </motion.button>
      </motion.div>
    </div>
  )
}
