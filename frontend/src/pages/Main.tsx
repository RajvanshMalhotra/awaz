import { useState, useEffect, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import AnimatedGradientBackground from '@/components/ui/animated-gradient-background'
import { api, type ProcessResponse, type ApproveResponse, type Speaker, type Profile } from '@/lib/api'
import { useSignRecognizer } from '@/hooks/useSignRecognizer'
import { useLatency } from '@/hooks/useLatency'
import { toast } from '@/components/Toast'
import { AudioPlayer } from '@/components/AudioPlayer'

type Stage = 'idle' | 'processing' | 'review' | 'approved'

const MOODS = ['auto', 'happy', 'excited', 'calm', 'confident', 'empathetic', 'professional', 'sarcastic', 'angry', 'neutral'] as const
type Mood = typeof MOODS[number]

const MOOD_ACTIVE: Record<string, string> = {
  auto: 'border-white/30 text-white/70',
  happy: 'border-yellow-400/40 text-yellow-300',
  excited: 'border-orange-400/40 text-orange-300',
  calm: 'border-blue-400/40 text-blue-300',
  confident: 'border-indigo-400/40 text-indigo-300',
  empathetic: 'border-pink-400/40 text-pink-300',
  professional: 'border-slate-400/40 text-slate-300',
  sarcastic: 'border-purple-400/40 text-purple-300',
  angry: 'border-red-400/40 text-red-300',
  neutral: 'border-zinc-400/40 text-zinc-300',
}

interface MainProps {
  profiles: Profile[]
  activeProfile: Profile
  onProfileUpdate: (p: Profile) => void
  onAddProfile: () => void
  onDeleteProfile: (id: string) => void
}

export function Main({ profiles, activeProfile, onProfileUpdate, onAddProfile, onDeleteProfile }: MainProps) {
  const [stage, setStage] = useState<Stage>('idle')
  const [mood, setMood] = useState<Mood>('auto')
  const [speakers, setSpeakers] = useState<Speaker[]>([])
  const [inputText, setInputText] = useState('')
  const [pendingText, setPendingText] = useState<string | null>(null)
  const [showCamera, setShowCamera] = useState(false)
  const [showSignInput, setShowSignInput] = useState(false)
  const [recognizedText, setRecognizedText] = useState('')
  const [processResult, setProcessResult] = useState<ProcessResponse | null>(null)
  const [approveResult, setApproveResult] = useState<ApproveResponse | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [showProfileMenu, setShowProfileMenu] = useState(false)

  const recognizer = useSignRecognizer()
  const latency = useLatency()
  const isMounted = useRef(true)
  const processingRef = useRef(false)
  const profileMenuRef = useRef<HTMLDivElement>(null)
  const signVideoRef = useRef<HTMLVideoElement>(null)
  const signCanvasRef = useRef<HTMLCanvasElement>(null)
  const textInputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    isMounted.current = true
    return () => { isMounted.current = false }
  }, [])

  useEffect(() => {
    api.getSpeakers().then(({ speakers: s }) => setSpeakers(s)).catch(() => {})
  }, [])

  // Close profile menu on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (profileMenuRef.current && !profileMenuRef.current.contains(e.target as Node)) {
        setShowProfileMenu(false)
      }
    }
    if (showProfileMenu) document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [showProfileMenu])

  // Keyboard shortcut: Escape clears/collapses
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (showProfileMenu) { setShowProfileMenu(false); return }
        if (stage === 'review' || stage === 'approved') handleReset()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [stage, showProfileMenu]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Text processing pipeline ──────────────────────────────────────────────
  useEffect(() => {
    if (stage !== 'processing' || !pendingText || processingRef.current) return
    processingRef.current = true
    latency.start()
    ;(async () => {
      try {
        const result = await api.processText(pendingText, 'friend', mood)
        if (!isMounted.current) return
        latency.stop()
        setProcessResult(result)
        setSessionId(result.session_id)
        setStage('review')
      } catch (err) {
        if (!isMounted.current) return
        latency.stop()
        toast(err instanceof Error ? err.message : 'Processing failed', 'error')
        setStage('idle')
      } finally {
        processingRef.current = false
        setPendingText(null)
      }
    })()
  }, [stage, pendingText]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSend = useCallback((text: string) => {
    const t = text.trim()
    if (!t || stage === 'processing') return
    setPendingText(t)
    setInputText('')
    setProcessResult(null)
    setApproveResult(null)
    latency.reset()
    setStage('processing')
  }, [stage, latency])

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend(inputText)
    }
  }, [inputText, handleSend])

  // ── Camera / sign language ────────────────────────────────────────────────
  useEffect(() => {
    if (showCamera && signVideoRef.current && signCanvasRef.current && recognizer.state === 'ready') {
      recognizer.start(signVideoRef.current, signCanvasRef.current)
    }
  }, [showCamera, recognizer.state]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleToggleCamera = useCallback(async () => {
    if (recognizer.state === 'recording') {
      const text = recognizer.stop()
      setShowCamera(false)
      setRecognizedText(text)
      setShowSignInput(true)
    } else {
      setShowCamera(true)
      setShowSignInput(false)
      setRecognizedText('')
    }
  }, [recognizer])

  const handleSendSign = useCallback(() => {
    if (!recognizedText.trim()) return
    setShowSignInput(false)
    recognizer.reset()
    handleSend(recognizedText)
  }, [recognizedText, recognizer, handleSend])

  // ── Approve / Deny / Reset ────────────────────────────────────────────────
  const handleApprove = useCallback(async () => {
    if (!sessionId) return
    setStage('processing')
    latency.start()
    try {
      const result = await api.approve(sessionId)
      if (!isMounted.current) return
      latency.stop()
      setApproveResult(result)
      setStage('approved')
    } catch (err) {
      if (!isMounted.current) return
      latency.stop()
      toast(err instanceof Error ? err.message : 'TTS failed', 'error')
      setStage('review')
    }
  }, [sessionId, latency])

  const handleDeny = useCallback(async () => {
    if (!sessionId) return
    setStage('processing')
    latency.start()
    try {
      const result = await api.deny(sessionId, { mood_override: mood !== 'auto' ? mood : undefined })
      if (!isMounted.current) return
      latency.stop()
      setProcessResult(prev => prev ? { ...prev, llm: result.llm } : prev)
      setSessionId(result.session_id)
      setStage('review')
    } catch {
      if (!isMounted.current) return
      latency.stop()
      toast('Regeneration failed', 'error')
      setStage('review')
    }
  }, [sessionId, mood, latency])

  const handleReset = useCallback(() => {
    recognizer.reset()
    processingRef.current = false
    setStage('idle')
    setProcessResult(null)
    setApproveResult(null)
    setSessionId(null)
    setPendingText(null)
    setShowCamera(false)
    setShowSignInput(false)
    setRecognizedText('')
    latency.reset()
    setTimeout(() => textInputRef.current?.focus(), 50)
  }, [recognizer, latency])

  const handleSwitchProfile = useCallback(async (profileId: string) => {
    try {
      await api.activateProfile(profileId)
      const found = profiles.find(p => p.profile_id === profileId)
      if (found) onProfileUpdate(found)
      setShowProfileMenu(false)
    } catch { toast('Failed to switch profile', 'error') }
  }, [profiles, onProfileUpdate])

  const isProcessing = stage === 'processing'
  const isRecording = recognizer.state === 'recording'

  return (
    <div className="relative w-full h-screen overflow-hidden bg-[#050508] flex flex-col">
      <AnimatedGradientBackground
        gradientColors={['#050508', '#090d1f', '#0d0f2a', '#080814', '#0a0820', '#050508', '#050508']}
        gradientStops={[20, 40, 55, 68, 82, 93, 100]}
        Breathing={true}
        breathingRange={6}
        animationSpeed={0.008}
        containerClassName="pointer-events-none"
      />

      {/* ── Header ── z-30 so dropdown renders above content area */}
      <div className="relative z-30 flex items-center justify-between px-6 py-4 border-b border-white/5">
        <span className="text-white font-black text-lg tracking-[-0.04em]">AWAAZ</span>
        <div className="flex items-center gap-3">
          <AnimatePresence>
            {(latency.isRunning || latency.frozen !== null) && (
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-semibold ${
                  latency.isRunning ? 'bg-amber-500/15 text-amber-300' : 'bg-emerald-500/15 text-emerald-300'
                }`}
              >
                {latency.isRunning && <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />}
                {latency.formatted}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Profile avatar */}
          <div ref={profileMenuRef} className="relative">
            <button
              onClick={() => setShowProfileMenu(v => !v)}
              className="w-8 h-8 rounded-full bg-indigo-500/25 border border-indigo-500/30 flex items-center justify-center text-xs font-bold text-indigo-300 hover:bg-indigo-500/35 transition-colors"
            >
              {activeProfile.name[0].toUpperCase()}
            </button>

            <AnimatePresence>
              {showProfileMenu && (
                <motion.div
                  initial={{ opacity: 0, y: -8, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -8, scale: 0.95 }}
                  transition={{ duration: 0.15 }}
                  className="absolute right-0 top-10 w-56 bg-[#0d0f1a] border border-white/10 rounded-2xl shadow-2xl overflow-hidden z-50"
                >
                  <div className="p-2">
                    <p className="text-[10px] text-white/25 uppercase tracking-widest px-3 py-1.5">Profiles</p>
                    {profiles.map(p => (
                      <div key={p.profile_id} className="flex items-center gap-2 group rounded-xl hover:bg-white/5 transition-colors px-2 py-1.5">
                        <button onClick={() => handleSwitchProfile(p.profile_id)} className="flex items-center gap-2 flex-1 text-left">
                          <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold ${
                            p.profile_id === activeProfile.profile_id
                              ? 'bg-indigo-500/30 text-indigo-300 ring-1 ring-indigo-400/40'
                              : 'bg-white/8 text-white/40'
                          }`}>
                            {p.name[0].toUpperCase()}
                          </div>
                          <span className={`text-sm ${p.profile_id === activeProfile.profile_id ? 'text-white font-semibold' : 'text-white/50'}`}>
                            {p.name}
                          </span>
                          {p.profile_id === activeProfile.profile_id && (
                            <span className="ml-auto text-[10px] text-indigo-400">active</span>
                          )}
                        </button>
                        <button
                          onClick={() => { onDeleteProfile(p.profile_id); setShowProfileMenu(false) }}
                          className="opacity-0 group-hover:opacity-100 transition-opacity text-red-400/60 hover:text-red-400 p-1 rounded-lg hover:bg-red-500/10"
                        >
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" />
                          </svg>
                        </button>
                      </div>
                    ))}
                  </div>
                  <div className="border-t border-white/6 p-2">
                    <button
                      onClick={() => { setShowProfileMenu(false); onAddProfile() }}
                      className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl hover:bg-white/5 text-white/40 hover:text-white/70 transition-colors text-sm"
                    >
                      <div className="w-6 h-6 rounded-full border border-dashed border-white/20 flex items-center justify-center text-white/30 text-xs">+</div>
                      Add new profile
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* ── Main content area ── */}
      <div className="relative z-10 flex-1 flex flex-col items-center justify-center px-6 gap-6 overflow-y-auto pb-44 pr-16">

        {/* Idle prompt */}
        <AnimatePresence>
          {stage === 'idle' && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              className="text-center space-y-2"
            >
              <p className="text-5xl font-black text-white/8 tracking-tight">Say something</p>
              <p className="text-white/15 text-sm">Type below · or use the camera for sign language</p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Processing spinner */}
        <AnimatePresence>
          {isProcessing && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 rounded-full border-2 border-white/10 border-t-indigo-400 animate-spin" />
              <p className="text-white/30 text-sm">Processing…</p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Output cards */}
        <AnimatePresence>
          {(stage === 'review' || stage === 'approved') && processResult && (
            <motion.div
              initial={{ opacity: 0, y: 28 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ type: 'spring', stiffness: 380, damping: 32 }}
              className="w-full max-w-lg space-y-3"
            >
              {/* Mood chip */}
              <div className="flex items-center gap-2">
                <span className="text-[10px] bg-indigo-500/15 text-indigo-300 px-2.5 py-1 rounded-full font-mono font-semibold">
                  {processResult.llm.detected_mood}
                </span>
                <span className="text-[10px] text-white/20 italic truncate">{processResult.llm.reasoning}</span>
              </div>

              {/* Input text */}
              <div className="bg-white/4 border border-white/8 rounded-2xl p-4">
                <p className="text-[10px] text-white/25 uppercase tracking-widest mb-2">Input</p>
                <p className="text-white/65 text-sm leading-relaxed">{processResult.transcript}</p>
              </div>

              {/* Expressive text */}
              <div className="bg-indigo-900/15 border border-indigo-500/20 rounded-2xl p-4">
                <p className="text-[10px] text-indigo-300/50 uppercase tracking-widest mb-2">Expressive</p>
                <p className="text-white/70 text-sm leading-relaxed font-mono break-words">
                  {processResult.llm.expressive_text}
                </p>
              </div>

              {/* Audio */}
              {stage === 'approved' && approveResult?.tts_audio_url && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  className="bg-emerald-900/15 border border-emerald-500/20 rounded-2xl p-4"
                >
                  <p className="text-[10px] text-emerald-300/50 uppercase tracking-widest mb-2">Audio</p>
                  <AudioPlayer url={approveResult.tts_audio_url} />
                </motion.div>
              )}

              {/* Actions */}
              {stage === 'review' && (
                <div className="flex gap-3">
                  <button
                    onClick={handleApprove}
                    className="flex-1 bg-emerald-500 hover:bg-emerald-400 active:scale-95 text-black font-bold py-3.5 rounded-2xl transition-all text-sm shadow-lg shadow-emerald-500/20"
                  >
                    ▶ Speak It
                  </button>
                  <button
                    onClick={handleDeny}
                    className="flex-1 bg-white/6 hover:bg-white/10 active:scale-95 text-white/50 font-semibold py-3.5 rounded-2xl transition-all text-sm"
                  >
                    ↺ Retry
                  </button>
                </div>
              )}

              {stage === 'approved' && (
                <button
                  onClick={handleReset}
                  className="w-full bg-white/6 hover:bg-white/10 active:scale-95 text-white/40 font-semibold py-3.5 rounded-2xl transition-all text-sm"
                >
                  ← New message
                </button>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ── Right-side voice roster ── */}
      {speakers.length > 0 && (
        <div className="absolute right-4 top-1/2 -translate-y-1/2 z-20 flex flex-col gap-3">
          {speakers.map(s => (
            <div key={s.speaker_id} className="relative group">
              <div className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-all cursor-default select-none border-white/10 bg-white/5 text-white/35">
                {s.name[0].toUpperCase()}
              </div>
              <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-[#050508] bg-zinc-600" />
              <div className="absolute right-12 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap">
                <div className="bg-black/85 text-white text-xs px-2.5 py-1.5 rounded-xl border border-white/8 shadow-xl">
                  <p className="font-semibold">{s.name}</p>
                  <p className="text-white/40">{s.relationship.replace('_', ' ')}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Camera preview (sign language) ── */}
      <AnimatePresence>
        {showCamera && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            className="absolute z-20 left-1/2 -translate-x-1/2 rounded-2xl overflow-hidden border border-white/10 shadow-2xl"
            style={{ bottom: '9rem', width: '220px', height: '165px' }}
          >
            <video ref={signVideoRef} autoPlay muted playsInline className="w-full h-full object-cover scale-x-[-1]" />
            <canvas
              ref={signCanvasRef}
              width={220}
              height={165}
              className="absolute inset-0 w-full h-full scale-x-[-1] pointer-events-none"
            />
            {recognizer.state === 'initializing' && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/60 rounded-2xl">
                <span className="text-white/60 text-[10px]">Loading model…</span>
              </div>
            )}
            <div className="absolute inset-0 border-2 border-rose-500/40 rounded-2xl pointer-events-none">
              <div className="absolute top-2 left-2 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
                <span className="text-white text-[10px] font-mono">REC</span>
              </div>
              {recognizer.liveGesture && (
                <div className="absolute bottom-2 left-0 right-0 flex justify-center">
                  <span className="bg-black/70 text-white text-[10px] font-semibold px-2 py-0.5 rounded-full">
                    {recognizer.liveGesture}
                  </span>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Sign language recognition result ── */}
      <AnimatePresence>
        {showSignInput && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 12 }}
            className="absolute z-20 left-1/2 -translate-x-1/2 w-full max-w-sm px-4"
            style={{ bottom: '9rem' }}
          >
            <div className="bg-[#0d0f1a] border border-white/10 rounded-2xl p-4 space-y-3 shadow-2xl">
              <p className="text-[10px] text-white/30 uppercase tracking-widest">Recognized sign (edit if needed)</p>
              <textarea
                value={recognizedText}
                onChange={e => setRecognizedText(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendSign() } }}
                placeholder="No gesture detected — type manually"
                rows={2}
                autoFocus
                className="w-full bg-white/5 border border-white/8 rounded-xl px-3 py-2 text-white text-sm outline-none resize-none placeholder:text-white/20 focus:border-white/20"
              />
              <div className="flex gap-2">
                <button
                  onClick={handleSendSign}
                  disabled={!recognizedText.trim()}
                  className="flex-1 py-2 bg-white text-black text-xs font-bold rounded-xl disabled:opacity-30 hover:bg-white/90 transition-colors"
                >
                  Send →
                </button>
                <button
                  onClick={() => { setShowSignInput(false); recognizer.reset() }}
                  className="px-4 py-2 bg-white/6 text-white/40 text-xs rounded-xl hover:bg-white/10 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Mood selector ── */}
      <div className="absolute z-10 left-0 right-16 px-5" style={{ bottom: '5.2rem' }}>
        <div className="flex flex-wrap gap-1.5">
          {MOODS.map(m => (
            <button
              key={m}
              onClick={() => setMood(m)}
              className={`px-3 py-1 rounded-full text-xs font-semibold border transition-all ${
                mood === m
                  ? MOOD_ACTIVE[m] + ' bg-white/5 scale-105'
                  : 'border-white/6 text-white/20 hover:text-white/40 hover:border-white/12'
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      {/* ── Input bar ── */}
      <div className="absolute z-20 left-0 right-0 px-4 pb-4" style={{ bottom: 0 }}>
        <div className="flex items-end gap-2 bg-[#0c0e1a] border border-white/8 rounded-2xl p-2 shadow-2xl">

          {/* Camera toggle */}
          <button
            onClick={handleToggleCamera}
            disabled={isProcessing}
            className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
              isRecording
                ? 'bg-rose-500 text-white'
                : 'bg-white/6 text-white/40 hover:bg-white/10 hover:text-white/70'
            } disabled:opacity-30 disabled:cursor-not-allowed`}
            title={isRecording ? 'Stop sign language recording' : 'Sign language (camera)'}
          >
            {isRecording ? (
              <motion.div animate={{ scale: [1, 1.2, 1] }} transition={{ duration: 1, repeat: Infinity }}
                className="w-3 h-3 rounded-sm bg-white" />
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M23 7l-7 5 7 5V7z" />
                <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
              </svg>
            )}
          </button>

          {/* Text area */}
          <textarea
            ref={textInputRef}
            value={inputText}
            onChange={e => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message… (Enter to send)"
            rows={1}
            disabled={isProcessing || isRecording}
            className="flex-1 bg-transparent text-white text-sm outline-none resize-none placeholder:text-white/20 py-2 px-1 min-h-[2.5rem] max-h-32 disabled:opacity-40"
            style={{ lineHeight: '1.5' }}
          />

          {/* Send button */}
          <button
            onClick={() => handleSend(inputText)}
            disabled={!inputText.trim() || isProcessing || isRecording}
            className="flex-shrink-0 w-10 h-10 rounded-xl bg-white flex items-center justify-center transition-all hover:bg-white/90 active:scale-95 disabled:opacity-20 disabled:cursor-not-allowed"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#050508" strokeWidth="2.5">
              <path d="M12 19V5M5 12l7-7 7 7" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}
