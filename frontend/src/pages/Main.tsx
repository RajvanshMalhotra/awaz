import { useState, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { GlassEffect, GlassFilter } from '@/components/ui/liquid-glass'
import { api, type VoiceResponse, type Profile } from '@/lib/api'
import { useRecorder } from '@/hooks/useRecorder'
import { useLatency } from '@/hooks/useLatency'
import { toast } from '@/components/Toast'
import { AudioPlayer } from '@/components/AudioPlayer'

const MOODS = ['auto', 'happy', 'excited', 'calm', 'sarcastic', 'angry', 'neutral', 'whispering'] as const
type Mood = typeof MOODS[number]

const MOOD_STYLE: Record<string, string> = {
  auto:       'border-white/30 text-white/70',
  happy:      'border-yellow-400/50 text-yellow-300',
  excited:    'border-orange-400/50 text-orange-300',
  calm:       'border-blue-400/50 text-blue-300',
  sarcastic:  'border-purple-400/50 text-purple-300',
  angry:      'border-red-400/50 text-red-300',
  neutral:    'border-zinc-400/50 text-zinc-300',
  whispering: 'border-indigo-400/50 text-indigo-300',
}

interface MainProps {
  profiles: Profile[]
  activeProfile: Profile
  onProfileUpdate: (p: Profile) => void
  onAddProfile: () => void
  onDeleteProfile: (id: string) => void
}

export function Main({ profiles, activeProfile, onProfileUpdate, onAddProfile, onDeleteProfile }: MainProps) {
  const [mood, setMood] = useState<Mood>('auto')
  const [inputText, setInputText] = useState('')
  const [result, setResult] = useState<VoiceResponse | null>(null)
  const [processing, setProcessing] = useState(false)
  const [showProfileMenu, setShowProfileMenu] = useState(false)

  const recorder = useRecorder()
  const latency = useLatency()
  const profileMenuRef = useRef<HTMLDivElement>(null)
  const textInputRef = useRef<HTMLTextAreaElement>(null)
  const processingRef = useRef(false)

  // ── Submit audio blob ──────────────────────────────────────────────────────
  const submitAudio = useCallback(async (blob: Blob) => {
    if (processingRef.current) return
    processingRef.current = true
    setProcessing(true)
    setResult(null)
    latency.start()
    try {
      const res = await api.voice(blob, mood)
      latency.stop()
      setResult(res)
    } catch (err) {
      latency.stop()
      toast(err instanceof Error ? err.message : 'Processing failed', 'error')
    } finally {
      setProcessing(false)
      processingRef.current = false
    }
  }, [mood, latency])

  // ── Submit text ────────────────────────────────────────────────────────────
  const submitText = useCallback(async (text: string) => {
    const t = text.trim()
    if (!t || processingRef.current) return
    processingRef.current = true
    setProcessing(true)
    setResult(null)
    setInputText('')
    latency.start()
    try {
      const res = await api.speak(t, mood)
      latency.stop()
      setResult(res)
    } catch (err) {
      latency.stop()
      toast(err instanceof Error ? err.message : 'Processing failed', 'error')
    } finally {
      setProcessing(false)
      processingRef.current = false
    }
  }, [mood, latency])

  // ── Recorder: auto-submit when recording stops ─────────────────────────────
  const handleToggleMic = useCallback(async () => {
    if (recorder.state === 'recording') {
      recorder.stop()
      // blob arrives via useEffect below — handled in useRecorder hook
    } else {
      await recorder.start()
    }
  }, [recorder])

  // When recorder produces a blob, submit it
  const prevBlobRef = useRef<Blob | null>(null)
  if (recorder.blob && recorder.blob !== prevBlobRef.current) {
    prevBlobRef.current = recorder.blob
    submitAudio(recorder.blob)
  }

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submitText(inputText)
    }
  }, [inputText, submitText])

  const handleReset = useCallback(() => {
    setResult(null)
    recorder.reset()
    latency.reset()
    setTimeout(() => textInputRef.current?.focus(), 50)
  }, [recorder, latency])

  const handleSwitchProfile = useCallback(async (profileId: string) => {
    try {
      await api.activateProfile(profileId)
      const found = profiles.find(p => p.profile_id === profileId)
      if (found) onProfileUpdate(found)
      setShowProfileMenu(false)
    } catch { toast('Failed to switch profile', 'error') }
  }, [profiles, onProfileUpdate])

  const isRecording = recorder.state === 'recording'

  return (
    <div
      className="relative w-full h-screen overflow-hidden flex flex-col bg-cover bg-center"
      style={{
        backgroundImage: `url('https://pub-940ccf6255b54fa799a9b01050e6c227.r2.dev/ruixen_moon_2.png')`,
        backgroundAttachment: 'fixed',
      }}
    >
      <GlassFilter />
      <div className="absolute inset-0 bg-black/45 pointer-events-none z-0" />

      {/* ── Header ── */}
      <div className="relative z-30 flex items-center justify-between px-6 py-4 border-b border-white/10">
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
                  className="absolute right-0 top-10 w-52 bg-black/80 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl overflow-hidden z-50"
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
                        </button>
                        <button
                          onClick={() => { onDeleteProfile(p.profile_id); setShowProfileMenu(false) }}
                          className="opacity-0 group-hover:opacity-100 transition-opacity text-red-400/60 hover:text-red-400 p-1 rounded-lg"
                        >
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" />
                          </svg>
                        </button>
                      </div>
                    ))}
                  </div>
                  <div className="border-t border-white/8 p-2">
                    <button
                      onClick={() => { setShowProfileMenu(false); onAddProfile() }}
                      className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl hover:bg-white/5 text-white/40 hover:text-white/70 transition-colors text-sm"
                    >
                      <div className="w-6 h-6 rounded-full border border-dashed border-white/20 flex items-center justify-center text-white/30 text-xs">+</div>
                      Add profile
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* ── Main content ── */}
      <div className="relative z-10 flex-1 flex flex-col items-center justify-center px-6 gap-5 overflow-y-auto pb-40">

        <AnimatePresence mode="wait">

          {/* Idle */}
          {!processing && !result && (
            <motion.div
              key="idle"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              className="text-center space-y-2"
            >
              {isRecording ? (
                <>
                  <motion.div
                    animate={{ scale: [1, 1.3, 1] }}
                    transition={{ duration: 0.7, repeat: Infinity }}
                    className="w-4 h-4 rounded-full bg-rose-500 mx-auto"
                  />
                  <p className="text-white/50 text-sm font-mono">{recorder.formattedTime}</p>
                  <p className="text-white/25 text-xs">Recording… tap mic to stop</p>
                </>
              ) : (
                <>
                  <p className="text-5xl font-black text-white/10 tracking-tight">Say something</p>
                  <p className="text-white/20 text-sm">Tap the mic · or type below · Enter to send</p>
                </>
              )}
            </motion.div>
          )}

          {/* Processing */}
          {processing && (
            <motion.div
              key="processing"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center gap-3"
            >
              <div className="w-9 h-9 rounded-full border-2 border-white/10 border-t-indigo-400 animate-spin" />
              <p className="text-white/40 text-sm">Generating your voice…</p>
            </motion.div>
          )}

          {/* Result */}
          {!processing && result && (
            <motion.div
              key="result"
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ type: 'spring', stiffness: 360, damping: 30 }}
              className="w-full max-w-lg space-y-3"
            >
              {/* Mood chip */}
              <div className="flex items-center gap-2">
                <span className="text-[10px] bg-indigo-500/15 text-indigo-300 px-2.5 py-1 rounded-full font-mono font-semibold">
                  {result.detected_mood}
                </span>
                <span className="text-[10px] text-white/20 italic truncate">{result.reasoning}</span>
              </div>

              {/* Audio — auto-plays */}
              <div className="bg-emerald-900/20 border border-emerald-500/20 rounded-2xl p-4">
                <p className="text-[10px] text-emerald-300/50 uppercase tracking-widest mb-2">Voice</p>
                <AudioPlayer url={result.tts_audio_url} />
              </div>

              {/* What was heard */}
              <div className="bg-white/4 border border-white/8 rounded-2xl p-4">
                <p className="text-[10px] text-white/25 uppercase tracking-widest mb-2">You said</p>
                <p className="text-white/60 text-sm leading-relaxed">{result.transcript}</p>
              </div>

              {/* Expressive text */}
              <div className="bg-indigo-900/15 border border-indigo-500/20 rounded-2xl p-4">
                <p className="text-[10px] text-indigo-300/40 uppercase tracking-widest mb-2">Spoken as</p>
                <p className="text-white/70 text-sm leading-relaxed font-mono break-words">
                  {result.expressive_text}
                </p>
              </div>

              <button
                onClick={handleReset}
                className="w-full bg-white/6 hover:bg-white/10 active:scale-95 text-white/40 font-semibold py-3 rounded-2xl transition-all text-sm"
              >
                ← Say something else
              </button>
            </motion.div>
          )}

        </AnimatePresence>
      </div>

      {/* ── Mood selector ── */}
      <div className="absolute z-10 left-0 right-0 px-5" style={{ bottom: '5.2rem' }}>
        <div className="flex flex-wrap gap-1.5">
          {MOODS.map(m => (
            <button
              key={m}
              onClick={() => setMood(m)}
              className={`px-3 py-1 rounded-full text-xs font-semibold border transition-all ${
                mood === m
                  ? MOOD_STYLE[m] + ' bg-white/5 scale-105'
                  : 'border-white/8 text-white/20 hover:text-white/40 hover:border-white/15'
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      {/* ── Input bar ── */}
      <div className="absolute z-20 left-0 right-0 px-4 pb-4" style={{ bottom: 0 }}>
        <GlassEffect className="rounded-2xl">
          <div className="flex items-end gap-2 p-2">

            {/* Mic button */}
            <button
              onClick={handleToggleMic}
              disabled={processing}
              className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
                isRecording
                  ? 'bg-rose-500 text-white shadow-lg shadow-rose-500/30'
                  : 'bg-white/10 text-white/50 hover:bg-white/20 hover:text-white/80'
              } disabled:opacity-30 disabled:cursor-not-allowed`}
            >
              {isRecording ? (
                <motion.div
                  animate={{ scale: [1, 1.2, 1] }}
                  transition={{ duration: 0.7, repeat: Infinity }}
                  className="w-3 h-3 rounded-sm bg-white"
                />
              ) : (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <rect x="9" y="2" width="6" height="12" rx="3" />
                  <path d="M5 10a7 7 0 0 0 14 0" />
                  <line x1="12" y1="19" x2="12" y2="22" />
                  <line x1="8" y1="22" x2="16" y2="22" />
                </svg>
              )}
            </button>

            {/* Text area */}
            <textarea
              ref={textInputRef}
              value={inputText}
              onChange={e => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type what you want to say… (Enter to send)"
              rows={1}
              disabled={processing || isRecording}
              className="flex-1 bg-transparent text-white text-sm outline-none resize-none placeholder:text-white/25 py-2 px-1 min-h-[2.5rem] max-h-32 disabled:opacity-40"
              style={{ lineHeight: '1.5' }}
            />

            {/* Send button */}
            <button
              onClick={() => submitText(inputText)}
              disabled={!inputText.trim() || processing || isRecording}
              className="flex-shrink-0 w-10 h-10 rounded-xl bg-white/90 flex items-center justify-center transition-all hover:bg-white active:scale-95 disabled:opacity-20 disabled:cursor-not-allowed"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#050508" strokeWidth="2.5">
                <path d="M12 19V5M5 12l7-7 7 7" />
              </svg>
            </button>
          </div>
        </GlassEffect>
      </div>
    </div>
  )
}
