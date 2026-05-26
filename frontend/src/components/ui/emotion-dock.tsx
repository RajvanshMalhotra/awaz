"use client"

import { cn } from "@/lib/utils"
import { motion, AnimatePresence, useReducedMotion } from "framer-motion"
import { useState, useRef, useEffect } from "react"

export interface Emotion {
  name: string
  emoji: string
}

// Default visible emotions in the dock (8 max looks good)
const DEFAULT_EMOTIONS: Emotion[] = [
  { name: 'auto',       emoji: '🎭' },
  { name: 'happy',      emoji: '😊' },
  { name: 'excited',    emoji: '🤩' },
  { name: 'calm',       emoji: '😌' },
  { name: 'sarcastic',  emoji: '😏' },
  { name: 'angry',      emoji: '😠' },
  { name: 'whispering', emoji: '🤫' },
  { name: 'neutral',    emoji: '😐' },
]

// Extra emotions shown in the + picker
const EXTRA_EMOTIONS: Emotion[] = [
  { name: 'sad',        emoji: '😢' },
  { name: 'laughing',   emoji: '😂' },
  { name: 'shocked',    emoji: '😱' },
  { name: 'confident',  emoji: '😎' },
  { name: 'empathetic', emoji: '🥹' },
  { name: 'scared',     emoji: '😨' },
]

interface EmotionDockProps {
  selected: string
  onSelect: (emotion: string) => void
  className?: string
}

export function EmotionDock({ selected, onSelect, className }: EmotionDockProps) {
  const shouldReduceMotion = useReducedMotion()
  const [showPicker, setShowPicker] = useState(false)
  const dockRef = useRef<HTMLDivElement>(null)

  // Close picker on outside click
  useEffect(() => {
    if (!showPicker) return
    const handler = (e: MouseEvent) => {
      if (dockRef.current && !dockRef.current.contains(e.target as Node)) {
        setShowPicker(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [showPicker])

  const handleSelect = (name: string) => {
    onSelect(name)
    setShowPicker(false)
  }

  const hoverAnim = shouldReduceMotion
    ? {}
    : { scale: 1.1, y: -4, transition: { type: 'spring', stiffness: 400, damping: 25 } }

  return (
    <div ref={dockRef} className={cn("relative", className)}>

      {/* Extra emoji picker — floats above the dock */}
      <AnimatePresence>
        {showPicker && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.92 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.92 }}
            transition={{ type: 'spring', stiffness: 380, damping: 28 }}
            className="absolute bottom-full mb-3 left-1/2 -translate-x-1/2 z-50"
          >
            <div className="rounded-full px-3 py-2 bg-white shadow-2xl border border-gray-200/50 flex items-center gap-1">
              {EXTRA_EMOTIONS.map((e) => (
                <motion.button
                  key={e.name}
                  onClick={() => handleSelect(e.name)}
                  whileHover={hoverAnim}
                  whileTap={{ scale: 0.92 }}
                  className="relative w-9 h-9 rounded-full flex items-center justify-center"
                  title={e.name}
                >
                  <span className="text-xl">{e.emoji}</span>
                  {selected === e.name && (
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-green-500 border-2 border-white rounded-full"
                    />
                  )}
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main dock pill */}
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.85 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ type: 'spring', stiffness: 300, damping: 28, mass: 0.8 }}
        className="rounded-full px-3 py-2 bg-white shadow-2xl border border-gray-200/50 flex items-center gap-1"
      >
        {DEFAULT_EMOTIONS.map((e) => (
          <motion.button
            key={e.name}
            onClick={() => handleSelect(e.name)}
            whileHover={hoverAnim}
            whileTap={{ scale: 0.92 }}
            className="relative w-9 h-9 rounded-full flex items-center justify-center"
            title={e.name}
          >
            <span className="text-xl">{e.emoji}</span>
            {selected === e.name && (
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-green-500 border-2 border-white rounded-full"
              />
            )}
          </motion.button>
        ))}

        {/* Separator */}
        <div className="w-px h-5 bg-gray-200 mx-1" />

        {/* + button */}
        <motion.button
          onClick={() => setShowPicker(v => !v)}
          whileHover={hoverAnim}
          whileTap={{ scale: 0.92 }}
          className={cn(
            "w-9 h-9 rounded-full flex items-center justify-center text-base font-semibold transition-colors",
            showPicker
              ? "bg-gray-100 text-gray-600"
              : "text-gray-400 hover:bg-gray-50 hover:text-gray-600"
          )}
          title="More emotions"
        >
          +
        </motion.button>
      </motion.div>
    </div>
  )
}
