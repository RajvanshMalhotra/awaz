import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { HeroHighlight, Highlight } from '@/components/ui/hero-highlight'
import { ContainerScroll } from '@/components/ui/container-scroll-animation'
import { api, type Profile } from '@/lib/api'
import { toast } from '@/components/Toast'

const QUESTIONS = [
  { text: "Do you feel energized after spending time with people?",          yes: ['energy','chaotic'],    no: ['energy','chill'] },
  { text: "Do criticism or negative comments stay with you for a long time?",yes: ['tone','sincere'],      no: ['tone','sarcastic'] },
  { text: "Do you make plans and usually follow them?",                      yes: ['style','punchy'],      no: ['style','dramatic'] },
  { text: "Do you often procrastinate on important tasks?",                  yes: ['style','dramatic'],    no: ['style','punchy'] },
  { text: "Do you enjoy exploring unfamiliar ideas or perspectives?",        yes: ['lang_lean','hindi'],   no: ['lang_lean','english'] },
  { text: "Do you find it easy to say no to people?",                        yes: ['filter','unfiltered'], no: ['filter','clean'] },
  { text: "Do you speak up when you disagree?",                              yes: ['filter','unfiltered'], no: ['filter','clean'] },
  { text: "Do you avoid conflict to maintain harmony?",                      yes: ['tone','sincere'],      no: ['tone','sarcastic'] },
  { text: "Does uncertainty excite you more than it scares you?",            yes: ['energy','chaotic'],    no: ['energy','chill'] },
  { text: "Do you trust your judgment more than popular opinion?",           yes: ['lang_lean','hindi'],   no: ['lang_lean','english'] },
]

const DEFAULTS: Record<string,string> = { energy:'chill', filter:'clean', style:'punchy', tone:'sincere', lang_lean:'hindi' }

const DIM_DISPLAY: Record<string,Record<string,string>> = {
  energy:    { chill:'Calm / Introverted',     chaotic:'High-energy / Extroverted' },
  filter:    { clean:'Measured / Clean',        unfiltered:'Direct / Unfiltered' },
  style:     { punchy:'Concise / Efficient',    dramatic:'Expressive / Dramatic' },
  tone:      { sincere:'Warm / Sincere',        sarcastic:'Dry / Sarcastic' },
  lang_lean: { hindi:'Hindi-leaning Hinglish',  english:'English-leaning Hinglish' },
}

interface OnboardingProps { onComplete: (profile: Profile) => void }

type Step = 'name' | 'quiz' | 'result'

export function Onboarding({ onComplete }: OnboardingProps) {
  const [step, setStep] = useState<Step>('name')
  const [name, setName] = useState('')
  const [qIdx, setQIdx] = useState(0)
  const [votes, setVotes] = useState<Record<string,string[]>>({ energy:[], filter:[], style:[], tone:[], lang_lean:[] })
  const [history, setHistory] = useState<{ dim: string; val: string }[]>([])
  const [personality, setPersonality] = useState<Record<string,string>>(DEFAULTS)
  const [vibe, setVibe] = useState('')
  const [saving, setSaving] = useState(false)

  const startQuiz = () => {
    if (!name.trim()) { toast('Enter your name first', 'error'); return }
    setStep('quiz')
    setQIdx(0)
    setVotes({ energy:[], filter:[], style:[], tone:[], lang_lean:[] })
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
        const counts: Record<string,number> = {}
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

  // Y/N/Backspace keyboard shortcuts during quiz
  useEffect(() => {
    if (step !== 'quiz') return
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName
      if (['INPUT','TEXTAREA','SELECT'].includes(tag)) return
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
      <div className="max-w-lg mx-auto px-6 py-16 space-y-8">
        <AnimatePresence mode="wait">

          {step === 'name' && (
            <motion.div key="name" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}>
              <ContainerScroll
                titleComponent={
                  <div className="text-center space-y-4 mb-8">
                    <motion.h1
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: [20, -5, 0] }}
                      transition={{ duration: 0.6, ease: [0.4, 0, 0.2, 1] }}
                      className="text-4xl md:text-6xl font-bold text-neutral-800 dark:text-white leading-tight"
                    >
                      Meet Your{' '}
                      <Highlight className="text-neutral-900 dark:text-white">Voice</Highlight>
                    </motion.h1>
                    <p className="text-neutral-500 dark:text-neutral-400 text-base max-w-sm mx-auto">
                      10 quick questions so your AI perfectly mirrors your personality.
                    </p>
                  </div>
                }
              >
                {/* Name form inside the 3D card */}
                <div className="h-full flex flex-col items-center justify-center gap-4 p-6">
                  <p className="text-sm font-semibold text-neutral-500 uppercase tracking-widest">First, what should we call you?</p>
                  <input
                    type="text"
                    value={name}
                    onChange={e => setName(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && startQuiz()}
                    placeholder="Your name…"
                    maxLength={64}
                    autoFocus
                    className="w-full max-w-xs rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-3 text-base text-neutral-900 dark:text-white placeholder-neutral-400 outline-none focus:border-indigo-400 transition-colors"
                  />
                  <button onClick={startQuiz}
                    className="px-8 py-3 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 text-white font-semibold text-sm hover:from-indigo-400 hover:to-purple-500 transition-all shadow-lg">
                    Start Quiz →
                  </button>
                </div>
              </ContainerScroll>
            </motion.div>
          )}

          {step === 'quiz' && (
            <motion.div key="quiz" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}
              className="space-y-6">
              {/* Progress */}
              <div>
                <div className="flex justify-between text-xs text-neutral-500 dark:text-neutral-400 mb-2">
                  <span>Question {qIdx + 1} of {QUESTIONS.length}</span>
                  <span>{pct}%</span>
                </div>
                <div className="h-1 rounded-full bg-neutral-200 dark:bg-neutral-800 overflow-hidden">
                  <motion.div className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-purple-500"
                    animate={{ width: `${pct}%` }} transition={{ type: 'spring', stiffness: 300, damping: 30 }} />
                </div>
              </div>

              {/* Question card */}
              <AnimatePresence mode="wait">
                <motion.div key={qIdx}
                  initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}
                  transition={{ type: 'spring', stiffness: 400, damping: 35 }}
                  className="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-8 text-center shadow-xl">
                  <p className="text-xs font-semibold uppercase tracking-widest text-neutral-400 mb-4">{qIdx + 1} / {QUESTIONS.length}</p>
                  <p className="text-xl font-semibold text-neutral-800 dark:text-white leading-snug mb-8">{QUESTIONS[qIdx].text}</p>
                  <div className="grid grid-cols-2 gap-3">
                    {[{ label: 'Yes', hint: 'press Y', fn: () => answer(true), color: 'hover:bg-emerald-50 hover:border-emerald-300 hover:text-emerald-700 dark:hover:bg-emerald-900/20 dark:hover:border-emerald-600 dark:hover:text-emerald-300' },
                      { label: 'No', hint: 'press N', fn: () => answer(false), color: 'hover:bg-red-50 hover:border-red-300 hover:text-red-700 dark:hover:bg-red-900/20 dark:hover:border-red-600 dark:hover:text-red-300' }].map(b => (
                      <button key={b.label} onClick={b.fn}
                        className={`py-4 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 font-semibold text-base flex flex-col items-center gap-1 transition-all ${b.color}`}>
                        {b.label}
                        <span className="text-xs font-normal opacity-40 uppercase tracking-wider">{b.hint}</span>
                      </button>
                    ))}
                  </div>
                </motion.div>
              </AnimatePresence>

              {qIdx > 0 && (
                <button onClick={goBack} className="flex items-center gap-1 text-xs text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 transition-colors">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M19 12H5M12 5l-7 7 7 7"/></svg>
                  Back
                </button>
              )}
            </motion.div>
          )}

          {step === 'result' && (
            <motion.div key="result" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}
              className="space-y-4">
              <div className="text-center space-y-2">
                <motion.h1 initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-3xl font-bold text-neutral-800 dark:text-white">
                  Your <Highlight>Vibe</Highlight>
                </motion.h1>
                <p className="text-sm text-neutral-500 dark:text-neutral-400">Here's what we picked up.</p>
              </div>

              <div className="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-5 space-y-2 shadow-xl">
                {Object.entries(personality).map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between py-2 border-b border-neutral-100 dark:border-neutral-800 last:border-0">
                    <span className="text-xs font-semibold uppercase tracking-widest text-neutral-400">{k.replace('_',' ')}</span>
                    <span className="text-sm font-semibold text-indigo-500 dark:text-indigo-400">{DIM_DISPLAY[k]?.[v] ?? v}</span>
                  </div>
                ))}
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-widest text-neutral-400 mb-2">Custom Vibe (optional)</label>
                <textarea value={vibe} onChange={e => setVibe(e.target.value)} rows={2} maxLength={400}
                  placeholder="e.g. chaotic Delhi college kid who laughs at everything…"
                  className="w-full rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-4 py-2.5 text-sm text-neutral-700 dark:text-white/80 placeholder-neutral-400 outline-none resize-none focus:border-indigo-400 transition-colors" />
              </div>

              <button onClick={save} disabled={saving}
                className="w-full py-4 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 text-white font-semibold disabled:opacity-50 hover:from-indigo-400 hover:to-purple-500 transition-all shadow-lg">
                {saving ? 'Saving…' : 'Save Profile & Continue →'}
              </button>
              <button onClick={() => { setStep('quiz'); setQIdx(0); setVotes({ energy:[], filter:[], style:[], tone:[], lang_lean:[] }); setHistory([]) }}
                className="w-full text-xs text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 transition-colors py-2">
                ↺ Retake quiz
              </button>
            </motion.div>
          )}

        </AnimatePresence>
      </div>
    </HeroHighlight>
  )
}
