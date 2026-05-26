import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { HeroHighlight } from '@/components/ui/hero-highlight'
import { GlassEffect, GlassFilter } from '@/components/ui/liquid-glass'
import { api, type Profile } from '@/lib/api'
import { toast } from '@/components/Toast'

const QUESTIONS = [
  { text: "Do you feel energized after spending time with people?",           yes: ['energy','chaotic'],    no: ['energy','chill'] },
  { text: "Do criticism or negative comments stay with you for a long time?", yes: ['tone','sincere'],      no: ['tone','sarcastic'] },
  { text: "Do you make plans and usually follow them?",                       yes: ['style','punchy'],      no: ['style','dramatic'] },
  { text: "Do you often procrastinate on important tasks?",                   yes: ['style','dramatic'],    no: ['style','punchy'] },
  { text: "Do you enjoy exploring unfamiliar ideas or perspectives?",         yes: ['lang_lean','hindi'],   no: ['lang_lean','english'] },
  { text: "Do you find it easy to say no to people?",                        yes: ['filter','unfiltered'], no: ['filter','clean'] },
  { text: "Do you speak up when you disagree?",                              yes: ['filter','unfiltered'], no: ['filter','clean'] },
  { text: "Do you avoid conflict to maintain harmony?",                      yes: ['tone','sincere'],      no: ['tone','sarcastic'] },
  { text: "Does uncertainty excite you more than it scares you?",            yes: ['energy','chaotic'],    no: ['energy','chill'] },
  { text: "Do you trust your judgment more than popular opinion?",           yes: ['lang_lean','hindi'],   no: ['lang_lean','english'] },
]

const DEFAULTS: Record<string, string> = { energy: 'chill', filter: 'clean', style: 'punchy', tone: 'sincere', lang_lean: 'hindi' }

const DIM_DISPLAY: Record<string, Record<string, string>> = {
  energy:    { chill: 'Calm / Introverted',       chaotic: 'High-energy / Extroverted' },
  filter:    { clean: 'Measured / Clean',          unfiltered: 'Direct / Unfiltered' },
  style:     { punchy: 'Concise / Efficient',      dramatic: 'Expressive / Dramatic' },
  tone:      { sincere: 'Warm / Sincere',          sarcastic: 'Dry / Sarcastic' },
  lang_lean: { hindi: 'Hindi-leaning Hinglish',   english: 'English-leaning Hinglish' },
}

const DIM_ICON: Record<string, string> = {
  energy: '⚡', filter: '🎛', style: '✍️', tone: '🎭', lang_lean: '🗣',
}

interface OnboardingProps { onComplete: (profile: Profile) => void }
type Step = 'name' | 'quiz' | 'result'

export function Onboarding({ onComplete }: OnboardingProps) {
  const [step, setStep] = useState<Step>('name')
  const [name, setName] = useState('')
  const [qIdx, setQIdx] = useState(0)
  const [votes, setVotes] = useState<Record<string, string[]>>({ energy: [], filter: [], style: [], tone: [], lang_lean: [] })
  const [history, setHistory] = useState<{ dim: string; val: string }[]>([])
  const [personality, setPersonality] = useState<Record<string, string>>(DEFAULTS)
  const [vibe, setVibe] = useState('')
  const [saving, setSaving] = useState(false)

  const startQuiz = () => {
    if (!name.trim()) { toast('Enter your name first', 'error'); return }
    setStep('quiz')
    setQIdx(0)
    setVotes({ energy: [], filter: [], style: [], tone: [], lang_lean: [] })
    setHistory([])
  }

  const answer = (yes: boolean) => {
    const q = QUESTIONS[qIdx]
    const [dim, val] = yes ? q.yes : q.no
    const newVotes = { ...votes, [dim]: [...votes[dim], val] }
    setVotes(newVotes)
    setHistory(h => [...h, { dim, val }])

    const next = qIdx + 1
    if (next < QUESTIONS.length) {
      setQIdx(next)
    } else {
      const p = { ...DEFAULTS }
      Object.keys(DEFAULTS).forEach(d => {
        const counts: Record<string, number> = {}
        newVotes[d].forEach(v => { counts[v] = (counts[v] ?? 0) + 1 })
        const top = Math.max(0, ...Object.values(counts))
        const winners = Object.keys(counts).filter(k => counts[k] === top)
        p[d] = winners.length === 1 ? winners[0] : DEFAULTS[d]
      })
      setPersonality(p)
      setStep('result')
    }
  }

  const goBack = () => {
    if (qIdx === 0) return
    const last = history[history.length - 1]
    setVotes(v => ({ ...v, [last.dim]: v[last.dim].slice(0, -1) }))
    setHistory(h => h.slice(0, -1))
    setQIdx(i => i - 1)
  }

  const save = async () => {
    setSaving(true)
    try {
      const saved = await api.saveProfile({ name, personality, custom_vibe: vibe })
      toast(`Welcome, ${saved.name}!`, 'success')
      onComplete(saved)
    } catch {
      toast('Failed to save profile', 'error')
    } finally { setSaving(false) }
  }

  useEffect(() => {
    if (step !== 'quiz') return
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(tag)) return
      if (e.key === 'y' || e.key === 'Y') { e.preventDefault(); answer(true) }
      if (e.key === 'n' || e.key === 'N') { e.preventDefault(); answer(false) }
      if (e.key === 'Backspace' || e.key === 'ArrowLeft') { e.preventDefault(); goBack() }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [step, qIdx]) // eslint-disable-line react-hooks/exhaustive-deps

  const pct = Math.round((qIdx / QUESTIONS.length) * 100)

  return (
    <HeroHighlight containerClassName="min-h-screen overflow-y-auto">
      {/* SVG glass filter — required for GlassEffect */}
      <GlassFilter />

      <div className="flex flex-col items-center w-full py-16 px-5">
        {/* Logo */}
        <div className="mb-8 text-center">
          <span className="text-white/20 font-black text-lg tracking-[-0.04em]">AWAAZ</span>
        </div>

        {/* Step content */}
        <div className="w-full max-w-md">
        <AnimatePresence mode="wait">

          {/* ── Step 1: Name ── */}
          {step === 'name' && (
            <motion.div
              key="name"
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ type: 'spring', stiffness: 340, damping: 30 }}
            >
              <div className="text-center mb-8 space-y-3">
                <motion.h1
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 }}
                  className="text-4xl font-black text-white tracking-[-0.03em]"
                >
                  Meet Your Voice
                </motion.h1>
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.2 }}
                  className="text-white/35 text-sm"
                >
                  10 quick questions — your AI perfectly mirrors you.
                </motion.p>
              </div>

              <GlassEffect className="rounded-3xl p-7 w-full">
                <div className="space-y-5">
                  <p className="text-white/40 text-xs font-semibold uppercase tracking-widest text-center">
                    What should we call you?
                  </p>
                  <input
                    type="text"
                    value={name}
                    onChange={e => setName(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && startQuiz()}
                    placeholder="Your name…"
                    maxLength={64}
                    autoFocus
                    className="w-full rounded-2xl px-4 py-3.5 text-base text-white placeholder-white/20 outline-none transition-all"
                    style={{
                      background: 'rgba(255,255,255,0.06)',
                      border: '1px solid rgba(255,255,255,0.1)',
                    }}
                    onFocus={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.28)' }}
                    onBlur={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)' }}
                  />
                  <button
                    onClick={startQuiz}
                    className="w-full py-3.5 rounded-2xl font-semibold text-sm transition-all active:scale-[0.98]"
                    style={{
                      background: 'rgba(255,255,255,0.92)',
                      color: '#060810',
                      boxShadow: '0 4px 20px rgba(255,255,255,0.08)',
                    }}
                  >
                    Start Quiz →
                  </button>
                </div>
              </GlassEffect>
            </motion.div>
          )}

          {/* ── Step 2: Quiz ── */}
          {step === 'quiz' && (
            <motion.div
              key="quiz"
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ type: 'spring', stiffness: 340, damping: 30 }}
              className="space-y-5"
            >
              {/* Progress */}
              <div className="space-y-2">
                <div className="flex justify-between text-xs text-white/25 font-mono">
                  <span>{qIdx + 1} / {QUESTIONS.length}</span>
                  <span>{pct}%</span>
                </div>
                <div className="h-px w-full rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.08)' }}>
                  <motion.div
                    className="h-full rounded-full"
                    style={{ background: 'rgba(255,255,255,0.5)' }}
                    animate={{ width: `${pct}%` }}
                    transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                  />
                </div>
              </div>

              {/* Question card */}
              <AnimatePresence mode="wait">
                <motion.div
                  key={qIdx}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ type: 'spring', stiffness: 400, damping: 35 }}
                >
                  <GlassEffect className="rounded-3xl p-7 w-full">
                    <div className="space-y-6">
                      <p className="text-white/60 text-base font-medium leading-snug text-center">
                        {QUESTIONS[qIdx].text}
                      </p>

                      <div className="grid grid-cols-2 gap-3">
                        {[
                          { label: 'Yes', hint: 'Y', fn: () => answer(true), accent: 'rgba(110,231,183,0.15)', border: 'rgba(110,231,183,0.3)', textAccent: 'rgb(110,231,183)' },
                          { label: 'No',  hint: 'N', fn: () => answer(false), accent: 'rgba(252,165,165,0.15)', border: 'rgba(252,165,165,0.3)', textAccent: 'rgb(252,165,165)' },
                        ].map(b => (
                          <button
                            key={b.label}
                            onClick={b.fn}
                            className="py-4 rounded-2xl flex flex-col items-center gap-1 transition-all active:scale-[0.96] group"
                            style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)' }}
                            onMouseEnter={e => {
                              e.currentTarget.style.background = b.accent
                              e.currentTarget.style.borderColor = b.border
                            }}
                            onMouseLeave={e => {
                              e.currentTarget.style.background = 'rgba(255,255,255,0.05)'
                              e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)'
                            }}
                          >
                            <span className="text-white font-semibold text-base">{b.label}</span>
                            <span className="text-white/25 text-[10px] uppercase tracking-widest font-mono">press {b.hint}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  </GlassEffect>
                </motion.div>
              </AnimatePresence>

              {qIdx > 0 && (
                <button
                  onClick={goBack}
                  className="flex items-center gap-1.5 text-xs text-white/25 hover:text-white/50 transition-colors"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M19 12H5M12 5l-7 7 7 7" />
                  </svg>
                  Back
                </button>
              )}
            </motion.div>
          )}

          {/* ── Step 3: Result ── */}
          {step === 'result' && (
            <motion.div
              key="result"
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ type: 'spring', stiffness: 340, damping: 30 }}
              className="space-y-5"
            >
              <div className="text-center space-y-2">
                <motion.h1
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-3xl font-black text-white tracking-[-0.03em]"
                >
                  Your Vibe
                </motion.h1>
                <p className="text-white/30 text-sm">Here's what we picked up.</p>
              </div>

              {/* Personality card */}
              <GlassEffect className="rounded-3xl p-6 w-full">
                <div className="space-y-1">
                  {Object.entries(personality).map(([k, v], i) => (
                    <motion.div
                      key={k}
                      initial={{ opacity: 0, x: -12 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.06 }}
                      className="flex items-center justify-between py-2.5 border-b last:border-0"
                      style={{ borderColor: 'rgba(255,255,255,0.06)' }}
                    >
                      <div className="flex items-center gap-2.5">
                        <span className="text-base">{DIM_ICON[k]}</span>
                        <span className="text-white/35 text-xs font-semibold uppercase tracking-widest">
                          {k.replace('_', ' ')}
                        </span>
                      </div>
                      <span className="text-white/80 text-sm font-semibold">
                        {DIM_DISPLAY[k]?.[v] ?? v}
                      </span>
                    </motion.div>
                  ))}
                </div>
              </GlassEffect>

              {/* Custom vibe */}
              <GlassEffect className="rounded-3xl p-5 w-full">
                <div className="space-y-3">
                  <label className="text-white/30 text-xs font-semibold uppercase tracking-widest">
                    Custom Vibe <span className="text-white/15 normal-case tracking-normal">(optional)</span>
                  </label>
                  <textarea
                    value={vibe}
                    onChange={e => setVibe(e.target.value)}
                    rows={2}
                    maxLength={400}
                    placeholder="e.g. chaotic Delhi college kid who laughs at everything…"
                    className="w-full rounded-xl px-3 py-2.5 text-sm text-white/80 placeholder-white/15 outline-none resize-none transition-all"
                    style={{
                      background: 'rgba(255,255,255,0.05)',
                      border: '1px solid rgba(255,255,255,0.08)',
                    }}
                    onFocus={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.2)' }}
                    onBlur={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)' }}
                  />
                </div>
              </GlassEffect>

              {/* Save button */}
              <button
                onClick={save}
                disabled={saving}
                className="w-full py-4 rounded-2xl font-semibold text-sm transition-all active:scale-[0.98] disabled:opacity-40"
                style={{
                  background: 'rgba(255,255,255,0.92)',
                  color: '#060810',
                  boxShadow: '0 4px 24px rgba(255,255,255,0.08)',
                }}
              >
                {saving ? 'Saving…' : `Save & Enter as ${name} →`}
              </button>

              <button
                onClick={() => { setStep('quiz'); setQIdx(0); setVotes({ energy: [], filter: [], style: [], tone: [], lang_lean: [] }); setHistory([]) }}
                className="w-full text-xs text-white/20 hover:text-white/40 transition-colors py-2"
              >
                ↺ Retake quiz
              </button>
            </motion.div>
          )}

        </AnimatePresence>
        </div>
      </div>
    </HeroHighlight>
  )
}
