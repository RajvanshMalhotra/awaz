import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'
import type { VoiceResponse } from '@/lib/api'
type ProcessResponse = VoiceResponse & { session_id: string; speaker: any; save_voice_prompt: boolean; effective_relationship: string; relationship_source: string; llm: any; detected_language: string | null }
type ApproveResponse = { tts_audio_url: string | null; tts_payload: any; expressive_text: string }
import { AudioPlayer } from './AudioPlayer'

const EMOTIONS: Record<string, { bg: string; color: string; border: string }> = {
  laughing:  { bg: 'rgba(251,191,36,.14)',  color: '#fcd34d', border: 'rgba(251,191,36,.3)' },
  shocked:   { bg: 'rgba(249,115,22,.14)',  color: '#fb923c', border: 'rgba(249,115,22,.3)' },
  whispering:{ bg: 'rgba(167,139,250,.14)', color: '#c4b5fd', border: 'rgba(167,139,250,.3)' },
  sad:       { bg: 'rgba(96,165,250,.14)',  color: '#93c5fd', border: 'rgba(96,165,250,.3)' },
  angry:     { bg: 'rgba(239,68,68,.14)',   color: '#f87171', border: 'rgba(239,68,68,.3)' },
  scared:    { bg: 'rgba(139,92,246,.14)',  color: '#a78bfa', border: 'rgba(139,92,246,.3)' },
  sarcastic: { bg: 'rgba(52,211,153,.14)',  color: '#6ee7b7', border: 'rgba(52,211,153,.3)' },
  happy:     { bg: 'rgba(251,191,36,.14)',  color: '#fbbf24', border: 'rgba(251,191,36,.3)' },
  neutral:   { bg: 'rgba(156,163,175,.1)',  color: '#9ca3af', border: 'rgba(156,163,175,.2)' },
  excited:   { bg: 'rgba(251,146,60,.14)',  color: '#fb923c', border: 'rgba(251,146,60,.3)' },
}

function parseExpr(text: string): React.ReactNode[] {
  const parts = text.split(/(\([a-z]+\))/gi)
  let cur: string | null = null
  return parts.flatMap((p, i) => {
    const m = p.match(/^\(([a-z]+)\)$/i)
    if (m) { cur = m[1].toLowerCase(); return [] }
    if (!p) return []
    const s = cur ? EMOTIONS[cur] : null
    if (s) return [
      <span key={i} style={{ color: s.color }}>
        <span style={{
          background: s.bg, color: s.color, border: `1px solid ${s.border}`,
          fontSize: 10, fontWeight: 700, textTransform: 'uppercase' as const,
          letterSpacing: '0.08em', padding: '2px 7px', borderRadius: 4,
          marginRight: 3, verticalAlign: 'middle' as const, position: 'relative' as const, top: -1,
          display: 'inline-block',
        }}>
          {cur}
        </span>
        {p}
      </span>,
    ]
    return [<span key={i}>{p}</span>]
  })
}

type StageStatus = 'pending' | 'running' | 'done'

function LiveTimer({ isRunning, frozenMs }: { isRunning: boolean; frozenMs: number | null }) {
  const [elapsed, setElapsed] = useState(0)
  const startRef = useRef<number | null>(null)
  const rafRef = useRef<number | null>(null)

  useEffect(() => {
    if (isRunning) {
      startRef.current = Date.now()
      const tick = () => {
        setElapsed(Date.now() - (startRef.current ?? Date.now()))
        rafRef.current = requestAnimationFrame(tick)
      }
      rafRef.current = requestAnimationFrame(tick)
    } else {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
    }
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current) }
  }, [isRunning])

  const ms = frozenMs ?? elapsed
  const fmt = ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(2)}s`

  if (!isRunning && frozenMs === null) return null
  return (
    <span className={cn('text-xs tabular-nums font-medium', frozenMs !== null ? 'text-emerald-400' : 'text-indigo-400')}>
      {fmt}
    </span>
  )
}

function StageRow({
  icon, label, status, latencyMs, children,
}: {
  icon: string; label: string; status: StageStatus; latencyMs: number | null; children?: React.ReactNode
}) {
  return (
    <div className="relative pl-9 mb-5 last:mb-0">
      <div className="absolute left-3.5 top-7 bottom-0 w-px bg-white/5" />
      <div className={cn(
        'absolute left-0 top-1 w-7 h-7 rounded-full flex items-center justify-center text-xs border transition-all duration-300',
        status === 'done'    && 'bg-emerald-500/15 border-emerald-500/40 text-emerald-400',
        status === 'running' && 'bg-indigo-500/15 border-indigo-500/50 text-indigo-400 animate-pulse',
        status === 'pending' && 'bg-white/5 border-white/10 text-white/30',
      )}>
        {icon}
      </div>
      <div className="flex items-center justify-between mb-2">
        <span className={cn('text-xs font-semibold uppercase tracking-widest',
          status === 'done'    && 'text-white/60',
          status === 'running' && 'text-indigo-300',
          status === 'pending' && 'text-white/25',
        )}>
          {label}
        </span>
        <LiveTimer isRunning={status === 'running'} frozenMs={latencyMs} />
      </div>
      <AnimatePresence>
        {status === 'done' && children && (
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ type: 'spring', stiffness: 400, damping: 32 }}
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export interface PipelineStagesProps {
  processResult: ProcessResponse | null
  approveResult: ApproveResponse | null
  processLatencyMs: number | null
  ttsLatencyMs: number | null
  isProcessing: boolean
  isApproving: boolean
  sessionId: string | null
  onApprove: () => void
  onDeny: (overrides: { mood_override?: string; relationship_override?: string; extra_text?: string }) => void
  onSaveSpeaker: (name: string, relationship: string) => void
}

const RELATIONSHIPS = ['friend','best_friend','parent','sibling','romantic','colleague','boss','stranger']
const MOOD_EMOJIS: Record<string, string> = {
  happy:'😊', excited:'🤩', laughing:'😂', sad:'😢', angry:'😠',
  shocked:'😱', scared:'😨', sarcastic:'😏', whispering:'🤫', neutral:'😐', auto:'🎭',
}
const MOODS_LIST = ['','happy','excited','laughing','sad','angry','shocked','scared','sarcastic','whispering','neutral']

export function PipelineStages({
  processResult, approveResult, processLatencyMs, ttsLatencyMs,
  isProcessing, isApproving, sessionId,
  onApprove, onDeny, onSaveSpeaker,
}: PipelineStagesProps) {
  const [denyOpen, setDenyOpen] = useState(false)
  const [denyMood, setDenyMood] = useState('')
  const [denyRel, setDenyRel] = useState('')
  const [denyExtra, setDenyExtra] = useState('')
  const [speakerName, setSpeakerName] = useState('')
  const [speakerRel, setSpeakerRel] = useState('friend')
  const [totalMs, setTotalMs] = useState<number | null>(null)

  useEffect(() => {
    if (processLatencyMs !== null && ttsLatencyMs !== null) {
      setTotalMs(processLatencyMs + ttsLatencyMs)
    }
  }, [processLatencyMs, ttsLatencyMs])

  const sttStatus: StageStatus = isProcessing ? 'running' : processResult ? 'done' : 'pending'
  const spkStatus: StageStatus = isProcessing ? 'running' : processResult ? 'done' : 'pending'
  const llmStatus: StageStatus = isProcessing ? 'running' : processResult ? 'done' : 'pending'
  const ttsStatus: StageStatus = isApproving ? 'running' : approveResult ? 'done' : 'pending'

  return (
    <div className="rounded-2xl border border-white/8 bg-white/3 backdrop-blur-sm px-5 py-5">
      <div className="flex items-center justify-between mb-5">
        <p className="text-xs font-semibold uppercase tracking-widest text-white/30">Pipeline</p>
        {totalMs !== null && (
          <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            className="text-xs font-bold text-emerald-400 tabular-nums">
            Total {totalMs < 1000 ? `${totalMs}ms` : `${(totalMs / 1000).toFixed(2)}s`}
          </motion.span>
        )}
      </div>

      <StageRow icon="🎙" label="Speech to Text" status={sttStatus} latencyMs={sttStatus === 'done' ? processLatencyMs : null}>
        {processResult && (
          <p className="text-sm text-white/75 leading-relaxed bg-white/5 rounded-xl px-3 py-2.5">
            {processResult.transcript}
          </p>
        )}
      </StageRow>

      <StageRow icon="👤" label="Speaker Recognition" status={spkStatus} latencyMs={null}>
        {processResult && (
          <div className="flex flex-wrap gap-2">
            {processResult.speaker.name ? (
              <>
                <span className="px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                  👤 {processResult.speaker.name}
                </span>
                <span className="px-3 py-1 rounded-full text-xs font-medium bg-white/5 text-white/50 border border-white/10">
                  {(processResult.speaker.similarity * 100).toFixed(0)}% match
                </span>
              </>
            ) : (
              <span className="px-3 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-300 border border-amber-500/20">
                👤 Unknown speaker
              </span>
            )}
            <span className="px-3 py-1 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
              {MOOD_EMOJIS[processResult.llm.detected_mood] ?? '🎭'} {processResult.llm.detected_mood}
            </span>
          </div>
        )}
      </StageRow>

      <StageRow icon="🧠" label="LLM · Expressive Text" status={llmStatus} latencyMs={llmStatus === 'done' ? processLatencyMs : null}>
        {processResult && (
          <div className="space-y-3">
            <div className="text-sm text-white/80 leading-loose bg-white/5 rounded-xl px-3 py-2.5">
              {parseExpr(processResult.llm.expressive_text)}
            </div>
            {processResult.llm.reasoning && (
              <p className="text-xs text-white/35 italic leading-relaxed">{processResult.llm.reasoning}</p>
            )}

            {processResult.save_voice_prompt && (
              <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3">
                <p className="text-xs font-semibold text-amber-300 mb-2">🎤 New voice — save this speaker?</p>
                <div className="flex gap-2">
                  <input value={speakerName} onChange={e => setSpeakerName(e.target.value)}
                    placeholder="Speaker's name"
                    className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white/80 placeholder-white/25 outline-none" />
                  <select value={speakerRel} onChange={e => setSpeakerRel(e.target.value)}
                    className="bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-sm text-white/80 outline-none">
                    {RELATIONSHIPS.map(r => <option key={r} value={r}>{r.replace('_', ' ')}</option>)}
                  </select>
                </div>
                <button onClick={() => onSaveSpeaker(speakerName, speakerRel)}
                  className="mt-2 px-3 py-1.5 text-xs font-medium rounded-lg bg-white/10 hover:bg-white/15 text-white/70 transition-colors">
                  Save Voice Profile
                </button>
              </div>
            )}

            {sessionId && !approveResult && (
              <div className="grid grid-cols-2 gap-2 pt-1">
                <button onClick={onApprove}
                  className="py-2.5 rounded-xl text-sm font-semibold bg-emerald-500/10 hover:bg-emerald-500/18 text-emerald-300 border border-emerald-500/20 transition-colors">
                  ✓ Sounds good
                </button>
                <button onClick={() => setDenyOpen(d => !d)}
                  className="py-2.5 rounded-xl text-sm font-semibold bg-red-500/10 hover:bg-red-500/18 text-red-300 border border-red-500/20 transition-colors">
                  ↺ Try again
                </button>
              </div>
            )}

            <AnimatePresence>
              {denyOpen && (
                <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
                  className="overflow-hidden border-t border-white/8 pt-3 space-y-2">
                  <div className="grid grid-cols-2 gap-2">
                    <select value={denyMood} onChange={e => setDenyMood(e.target.value)}
                      className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white/70 outline-none">
                      {MOODS_LIST.map(m => <option key={m} value={m}>{m ? (MOOD_EMOJIS[m] ?? '') + ' ' + m : 'Keep mood'}</option>)}
                    </select>
                    <select value={denyRel} onChange={e => setDenyRel(e.target.value)}
                      className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white/70 outline-none">
                      <option value="">Keep relationship</option>
                      {RELATIONSHIPS.map(r => <option key={r} value={r}>{r.replace('_', ' ')}</option>)}
                    </select>
                  </div>
                  <input value={denyExtra} onChange={e => setDenyExtra(e.target.value)}
                    placeholder="Add clarification…"
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white/70 placeholder-white/25 outline-none" />
                  <button onClick={() => {
                    onDeny({ mood_override: denyMood || undefined, relationship_override: denyRel || undefined, extra_text: denyExtra || undefined })
                    setDenyOpen(false)
                  }}
                    className="w-full py-2.5 rounded-xl text-sm font-semibold bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white transition-all">
                    Regenerate →
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}
      </StageRow>

      <StageRow icon="🔊" label="Silk Mulberry TTS" status={ttsStatus} latencyMs={ttsStatus === 'done' ? ttsLatencyMs : null}>
        {approveResult && approveResult.tts_audio_url && (
          <div className="space-y-3">
            <AudioPlayer url={approveResult.tts_audio_url} />
            <div className="text-xs font-mono text-white/30 bg-white/3 rounded-xl px-3 py-2 space-y-0.5">
              <p><span className="text-indigo-400">model</span>: {approveResult.tts_payload.model}</p>
              <p><span className="text-indigo-400">text</span>: {approveResult.tts_payload.text}</p>
              <p><span className="text-indigo-400">description</span>: {approveResult.tts_payload.description}</p>
            </div>
          </div>
        )}
      </StageRow>
    </div>
  )
}
