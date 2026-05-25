import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { HeroHighlight } from '@/components/ui/hero-highlight'
import { VerticalMoodDock } from '@/components/ui/vertical-mood-dock'
import { Pipeline } from '@/components/Pipeline'
import { PipelineStages } from '@/components/PipelineStages'
import { Profile } from '@/components/Profile'
import { useRecorder } from '@/hooks/useRecorder'
import { useLatency } from '@/hooks/useLatency'
import { api, type Profile as ProfileData, type ProcessResponse, type ApproveResponse } from '@/lib/api'
import { toast } from '@/components/Toast'
import { Overlay } from '@/components/Overlay'
import { cn } from '@/lib/utils'

interface MainProps {
  profiles: ProfileData[]
  activeProfile: ProfileData
  onProfileUpdate: (p: ProfileData) => void
}

type Tab = 'pipeline' | 'profile'

export function Main({ profiles, activeProfile, onProfileUpdate }: MainProps) {
  const [tab, setTab] = useState<Tab>('pipeline')
  const [relationship, setRelationship] = useState('friend')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [processResult, setProcessResult] = useState<ProcessResponse | null>(null)
  const [approveResult, setApproveResult] = useState<ApproveResponse | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [isApproving, setIsApproving] = useState(false)
  const [processLatencyMs, setProcessLatencyMs] = useState<number | null>(null)
  const [ttsLatencyMs, setTtsLatencyMs] = useState<number | null>(null)
  const [overlayMsg, setOverlayMsg] = useState('')

  const recorder = useRecorder()
  const processLatency = useLatency()
  const ttsLatency = useLatency()

  const showStages = isProcessing || processResult !== null

  const handleProcess = async (moodId: string, extraText: string) => {
    if (!recorder.blob) { toast('Record something first', 'error'); return }
    setIsProcessing(true)
    setProcessResult(null)
    setApproveResult(null)
    setSessionId(null)
    setProcessLatencyMs(null)
    setTtsLatencyMs(null)
    setOverlayMsg('STT · Speaker ID · LLM…')
    processLatency.start()

    try {
      const result = await api.processAudio(recorder.blob, relationship, moodId, extraText)
      const ms = processLatency.stop()
      setProcessLatencyMs(ms)
      setProcessResult(result)
      setSessionId(result.session_id)
    } catch (e) {
      processLatency.stop()
      toast('Processing failed — is the server running?', 'error')
      console.error(e)
    } finally {
      setIsProcessing(false)
      setOverlayMsg('')
    }
  }

  const handleApprove = async () => {
    if (!sessionId) return
    setIsApproving(true)
    setOverlayMsg('Synthesizing with Silk mulberry…')
    ttsLatency.start()

    try {
      const result = await api.approve(sessionId)
      const ms = ttsLatency.stop()
      setTtsLatencyMs(ms)
      setApproveResult(result)
      setSessionId(null)
    } catch {
      ttsLatency.stop()
      toast('TTS failed — check server logs', 'error')
    } finally {
      setIsApproving(false)
      setOverlayMsg('')
    }
  }

  const handleDeny = async (overrides: { mood_override?: string; relationship_override?: string; extra_text?: string }) => {
    if (!sessionId) return
    setIsProcessing(true)
    setOverlayMsg('Regenerating response…')
    processLatency.start()

    try {
      const result = await api.deny(sessionId, overrides)
      const ms = processLatency.stop()
      setProcessLatencyMs(ms)
      setProcessResult(prev => prev ? { ...prev, llm: result.llm } : null)
      setSessionId(result.session_id)
      toast('Regenerated!', 'success')
    } catch {
      processLatency.stop()
      toast('Regeneration failed', 'error')
    } finally {
      setIsProcessing(false)
      setOverlayMsg('')
    }
  }

  const handleSaveSpeaker = async (name: string, rel: string) => {
    if (!sessionId) return
    try {
      await api.saveSpeaker(sessionId, name, rel)
      toast(`Voice saved for ${name}!`, 'success')
    } catch {
      toast('Failed to save voice profile', 'error')
    }
  }

  const handleReset = () => {
    recorder.reset()
    setProcessResult(null)
    setApproveResult(null)
    setSessionId(null)
    setProcessLatencyMs(null)
    setTtsLatencyMs(null)
  }

  const handleProfileSaved = (p: ProfileData) => {
    onProfileUpdate(p)
  }

  return (
    <HeroHighlight containerClassName="min-h-screen">
      <Overlay isVisible={isProcessing || isApproving} message={overlayMsg} />

      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-white/5 bg-black/20 backdrop-blur-md px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="white">
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3zm-1 3a1 1 0 0 1 2 0v7a1 1 0 0 1-2 0V5zm8 5v1a7 7 0 0 1-14 0v-1H3v1a9 9 0 0 0 8 8.94V22h-3v2h8v-2h-3v-2.06A9 9 0 0 0 21 11v-1h-2z"/>
            </svg>
          </div>
          <span className="text-base font-semibold text-white tracking-tight">Awa<em className="not-italic text-indigo-400">az</em></span>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-white/5 border border-white/8 rounded-xl p-1">
          {(['pipeline','profile'] as Tab[]).map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={cn('px-4 py-1.5 rounded-lg text-xs font-semibold capitalize transition-all',
                tab === t ? 'bg-white/10 text-white' : 'text-white/35 hover:text-white/60'
              )}>
              {t}
            </button>
          ))}
        </div>

        {/* Profile chips */}
        <div className="flex items-center gap-2">
          {profiles.map(p => (
            <button key={p.profile_id}
              onClick={() => api.activateProfile(p.profile_id).then(() => onProfileUpdate(p)).catch(() => {})}
              className={cn('w-8 h-8 rounded-full text-xs font-bold flex items-center justify-center border transition-all',
                p.profile_id === activeProfile.profile_id
                  ? 'bg-indigo-500/20 border-indigo-500/50 text-indigo-300'
                  : 'bg-white/5 border-white/10 text-white/40 hover:border-white/25'
              )}>
              {p.name.slice(0,2).toUpperCase()}
            </button>
          ))}
        </div>
      </header>

      {/* Body */}
      <main className="max-w-xl mx-auto px-6 py-10 pb-24">
        <AnimatePresence mode="wait">
          {tab === 'pipeline' ? (
            <motion.div key="pipeline" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              className="space-y-6">
              <Pipeline
                recorderState={recorder.state}
                formattedTime={recorder.formattedTime}
                onToggle={async () => {
                  if (recorder.state === 'recording') recorder.stop()
                  else {
                    handleReset()
                    await recorder.start()
                  }
                }}
                onReset={handleReset}
                relationship={relationship}
                onRelationshipChange={setRelationship}
                showReset={approveResult !== null}
              />

              <AnimatePresence>
                {showStages && (
                  <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                    transition={{ type: 'spring', stiffness: 300, damping: 28 }}>
                    <PipelineStages
                      processResult={processResult}
                      approveResult={approveResult}
                      processLatencyMs={processLatencyMs}
                      ttsLatencyMs={ttsLatencyMs}
                      isProcessing={isProcessing}
                      isApproving={isApproving}
                      sessionId={sessionId}
                      onApprove={handleApprove}
                      onDeny={handleDeny}
                      onSaveSpeaker={handleSaveSpeaker}
                    />
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ) : (
            <motion.div key="profile" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <Profile
                onSave={handleProfileSaved}
                onClose={() => setTab('pipeline')}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Vertical mood dock — only on pipeline tab */}
      {tab === 'pipeline' && (
        <VerticalMoodDock
          canProcess={recorder.state === 'ready'}
          onProcess={handleProcess}
        />
      )}
    </HeroHighlight>
  )
}
