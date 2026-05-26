import { useState, useCallback, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { GlassEffect, GlassFilter } from '@/components/ui/liquid-glass'
import { EmotionDock } from '@/components/ui/emotion-dock'
import { api, type Profile } from '@/lib/api'
import { useRecorder } from '@/hooks/useRecorder'
import { useLatency } from '@/hooks/useLatency'
import { useVoiceWS } from '@/hooks/useVoiceWS'
import { toast } from '@/components/Toast'
import { AudioPlayer } from '@/components/AudioPlayer'

type Mood = string

type ChatEntry = {
  id: string
  transcript: string
  expressiveText: string
  detectedMood: string
  reasoning: string
  latencyMs: number
  audioUrl?: string
}

interface MainProps {
  profiles: Profile[]
  activeProfile: Profile
  onProfileUpdate: (p: Profile) => void
  onAddProfile: () => void
  onDeleteProfile: (id: string) => void
  onGoHome: () => void
}

function fmtMs(ms: number) {
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(2)}s`
}

export function Main({ profiles, activeProfile, onProfileUpdate, onAddProfile, onDeleteProfile, onGoHome }: MainProps) {
  const [mood, setMood] = useState<Mood>('auto')
  const [inputText, setInputText] = useState('')
  const [messages, setMessages] = useState<ChatEntry[]>([])
  const [processing, setProcessing] = useState(false)
  const [showProfileMenu, setShowProfileMenu] = useState(false)

  const recorder = useRecorder()
  const latency = useLatency()
  const voiceWS = useVoiceWS()
  const profileMenuRef = useRef<HTMLDivElement>(null)
  const textInputRef = useRef<HTMLTextAreaElement>(null)
  const processingRef = useRef(false)
  const chatEndRef = useRef<HTMLDivElement>(null)
  const prevBlobRef = useRef<Blob | null>(null)
  const prevErrorRef = useRef<string | null>(null)
  const wasPlayingRef = useRef(false)
  const latencyFrozenRef = useRef<number>(0)

  // Auto-scroll to bottom whenever chat changes
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, voiceWS.state.transcript, voiceWS.state.isPlayingAudio, processing])

  // Stop latency timer the moment first audio arrives (audio_start) — true perceived latency
  useEffect(() => {
    if (voiceWS.state.isPlayingAudio && latency.isRunning) {
      latencyFrozenRef.current = latency.stop()
    }
  }, [voiceWS.state.isPlayingAudio]) // eslint-disable-line

  // Commit exchange to chat when audio finishes playing
  useEffect(() => {
    const isPlaying = !!voiceWS.state.isPlayingAudio
    if (wasPlayingRef.current && !isPlaying && voiceWS.state.transcript) {
      const { transcript, expressiveText, detectedMood, reasoning } = voiceWS.state
      setMessages(prev => [...prev, {
        id: `v${Date.now()}`,
        transcript: transcript!,
        expressiveText: expressiveText ?? '',
        detectedMood: detectedMood ?? '',
        reasoning: reasoning ?? '',
        latencyMs: latencyFrozenRef.current,
      }])
      voiceWS.reset()
      processingRef.current = false
    }
    wasPlayingRef.current = isPlaying
  }, [voiceWS.state.isPlayingAudio, voiceWS.state.transcript]) // eslint-disable-line

  // Surface WS errors
  useEffect(() => {
    if (voiceWS.state.error && voiceWS.state.error !== prevErrorRef.current) {
      prevErrorRef.current = voiceWS.state.error
      processingRef.current = false
      latency.reset()
      toast(voiceWS.state.error, 'error')
    }
  }, [voiceWS.state.error, latency])

  // Submit audio blob — latency starts when recording stops (blob ready)
  const submitAudio = useCallback((blob: Blob) => {
    if (processingRef.current) return
    processingRef.current = true
    latency.start()
    voiceWS.submit(blob, mood)
  }, [mood, latency, voiceWS])

  // When recorder produces a new blob, submit it
  useEffect(() => {
    if (recorder.blob && recorder.blob !== prevBlobRef.current) {
      prevBlobRef.current = recorder.blob
      submitAudio(recorder.blob)
    }
  }, [recorder.blob, submitAudio])

  // Text path: latency spans API call start → response received
  const submitText = useCallback(async (text: string) => {
    const t = text.trim()
    if (!t || processingRef.current) return
    processingRef.current = true
    setProcessing(true)
    setInputText('')
    latency.start()
    try {
      const res = await api.speak(t, mood)
      const ms = latency.stop()
      setMessages(prev => [...prev, {
        id: `t${Date.now()}`,
        transcript: t,
        expressiveText: res.expressive_text,
        detectedMood: res.detected_mood,
        reasoning: res.reasoning,
        latencyMs: ms,
        audioUrl: res.tts_audio_url,
      }])
    } catch (err) {
      latency.reset()
      toast(err instanceof Error ? err.message : 'Processing failed', 'error')
    } finally {
      setProcessing(false)
      processingRef.current = false
    }
  }, [mood, latency])

  const handleToggleMic = useCallback(async () => {
    if (recorder.state === 'recording') {
      recorder.stop()
    } else {
      await recorder.start()
    }
  }, [recorder])

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submitText(inputText)
    }
  }, [inputText, submitText])

  const handleSwitchProfile = useCallback(async (profileId: string) => {
    try {
      await api.activateProfile(profileId)
      const found = profiles.find(p => p.profile_id === profileId)
      if (found) onProfileUpdate(found)
      setShowProfileMenu(false)
    } catch { toast('Failed to switch profile', 'error') }
  }, [profiles, onProfileUpdate])

  const isRecording = recorder.state === 'recording'
  // Disable mic during processing or playback (not during recording itself)
  const micDisabled = (voiceWS.state.isProcessing || voiceWS.state.isPlayingAudio || processing) && !isRecording

  const hasPending = voiceWS.state.isProcessing || voiceWS.state.isPlayingAudio || !!voiceWS.state.transcript

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
      <div className="relative z-30 flex items-center justify-between px-6 py-4 border-b border-white/10 flex-shrink-0">
        <button
          onClick={onGoHome}
          className="text-white font-black text-lg tracking-[-0.04em] hover:text-white/70 transition-colors"
        >
          AWAAZ
        </button>
        <div className="flex items-center gap-3">
          {/* Latency badge */}
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

          {/* Profile switcher */}
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

      {/* ── Chat area — flex-col so content stays pinned to the bottom ── */}
      <div className="relative z-10 flex-1 overflow-y-auto flex flex-col px-4 pb-48">

        {/* Spacer: fills empty space, pushing messages to the bottom */}
        <div className="flex-1 min-h-8" />

        {/* Empty state */}
        {messages.length === 0 && !hasPending && !processing && (
          <div className="flex items-center justify-center py-10 pointer-events-none">
            <p className="text-5xl font-black text-white/10 tracking-tight">Say something</p>
          </div>
        )}

        <div className="max-w-lg mx-auto w-full pt-4 space-y-5">

          {/* Completed messages */}
          {messages.map(msg => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ type: 'spring', stiffness: 400, damping: 30 }}
              className="space-y-1.5"
            >
              {/* They said */}
              <div className="bg-white/4 border border-white/8 rounded-2xl p-3.5">
                <p className="text-[10px] text-white/25 uppercase tracking-widest mb-1.5">They said</p>
                <p className="text-white/60 text-sm leading-relaxed">{msg.transcript}</p>
              </div>

              {/* Your response */}
              <div className="bg-indigo-900/15 border border-indigo-500/20 rounded-2xl p-3.5">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-[10px] bg-indigo-500/15 text-indigo-300 px-2 py-0.5 rounded-full font-mono font-semibold">
                    {msg.detectedMood}
                  </span>
                  <span className="text-[10px] text-emerald-400/70 font-mono font-semibold">
                    {fmtMs(msg.latencyMs)}
                  </span>
                  {msg.reasoning && (
                    <span className="text-[10px] text-white/20 italic truncate flex-1">{msg.reasoning}</span>
                  )}
                </div>
                <p className="text-white/75 text-sm leading-relaxed font-mono break-words">{msg.expressiveText}</p>
                {msg.audioUrl && (
                  <div className="mt-3">
                    <AudioPlayer url={msg.audioUrl} />
                  </div>
                )}
              </div>
            </motion.div>
          ))}

          {/* Pending voice exchange (in-progress) */}
          {hasPending && (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-1.5"
            >
              {/* They said — shows once transcript arrives */}
              {voiceWS.state.transcript && (
                <div className="bg-white/4 border border-white/8 rounded-2xl p-3.5">
                  <p className="text-[10px] text-white/25 uppercase tracking-widest mb-1.5">They said</p>
                  <p className="text-white/60 text-sm leading-relaxed">{voiceWS.state.transcript}</p>
                </div>
              )}

              {/* Response bubble */}
              <div className="bg-indigo-900/15 border border-indigo-500/20 rounded-2xl p-3.5">
                {voiceWS.state.expressiveText ? (
                  <>
                    {voiceWS.state.detectedMood && (
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-[10px] bg-indigo-500/15 text-indigo-300 px-2 py-0.5 rounded-full font-mono font-semibold">
                          {voiceWS.state.detectedMood}
                        </span>
                        {voiceWS.state.isPlayingAudio && (
                          <div className="flex items-center gap-1.5 text-emerald-300/80 text-[10px]">
                            <motion.div
                              animate={{ scale: [1, 1.4, 1] }}
                              transition={{ duration: 0.55, repeat: Infinity }}
                              className="w-1.5 h-1.5 rounded-full bg-emerald-400"
                            />
                            Playing
                          </div>
                        )}
                      </div>
                    )}
                    <p className="text-white/75 text-sm leading-relaxed font-mono break-words">
                      {voiceWS.state.expressiveText}
                    </p>
                  </>
                ) : (
                  <div className="flex items-center gap-2 text-white/30 text-xs py-0.5">
                    <div className="w-3.5 h-3.5 rounded-full border border-white/15 border-t-indigo-400 animate-spin flex-shrink-0" />
                    {voiceWS.state.transcript ? 'Generating reply…' : 'Transcribing…'}
                  </div>
                )}
              </div>
            </motion.div>
          )}

          {/* Text path processing indicator */}
          {processing && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex justify-center py-2"
            >
              <div className="flex items-center gap-2 bg-white/5 border border-white/8 rounded-full px-4 py-2 text-white/30 text-xs">
                <div className="w-3 h-3 rounded-full border border-white/15 border-t-white/50 animate-spin" />
                Generating…
              </div>
            </motion.div>
          )}

          <div ref={chatEndRef} />
        </div>
      </div>

      {/* ── Recording indicator (floating pill below header) ── */}
      <AnimatePresence>
        {isRecording && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="absolute z-20 top-16 left-0 right-0 flex justify-center pt-3 pointer-events-none"
          >
            <div className="flex items-center gap-2 bg-rose-500/15 border border-rose-500/25 backdrop-blur rounded-full px-4 py-2">
              <motion.div
                animate={{ scale: [1, 1.35, 1] }}
                transition={{ duration: 0.7, repeat: Infinity }}
                className="w-2 h-2 rounded-full bg-rose-500"
              />
              <span className="text-rose-300 text-xs font-mono">{recorder.formattedTime}</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Emotion dock ── */}
      <div className="absolute z-20 left-0 right-0 flex justify-center" style={{ bottom: '5.2rem' }}>
        <EmotionDock selected={mood} onSelect={setMood} />
      </div>

      {/* ── Input bar ── */}
      <div className="absolute z-20 left-0 right-0 px-4 pb-4" style={{ bottom: 0 }}>
        <GlassEffect className="rounded-2xl">
          <div className="flex items-end gap-2 p-2">

            {/* Mic button */}
            <button
              onClick={handleToggleMic}
              disabled={micDisabled}
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
              disabled={voiceWS.state.isProcessing || voiceWS.state.isPlayingAudio || processing || isRecording}
              className="flex-1 bg-transparent text-white text-sm outline-none resize-none placeholder:text-white/25 py-2 px-1 min-h-[2.5rem] max-h-32 disabled:opacity-40"
              style={{ lineHeight: '1.5' }}
            />

            {/* Send button */}
            <button
              onClick={() => submitText(inputText)}
              disabled={!inputText.trim() || voiceWS.state.isProcessing || voiceWS.state.isPlayingAudio || processing || isRecording}
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
