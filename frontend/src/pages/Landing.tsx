import { motion } from 'framer-motion'
import AnimatedGradientBackground from '@/components/ui/animated-gradient-background'
import { ContainerScroll } from '@/components/ui/container-scroll-animation'

interface LandingProps {
  onEnter: () => void
}

const features = [
  { icon: '🎙️', title: 'Voice Identity', desc: 'Recognises who is speaking from your enrolled voices' },
  { icon: '🧠', title: 'Emotion AI', desc: 'Infers or applies your chosen mood — never rewrites your words' },
  { icon: '🔊', title: 'Silk Mulberry TTS', desc: 'Mulberry-native tags deliver perfectly expressive speech' },
]

export function Landing({ onEnter }: LandingProps) {
  return (
    <div className="relative bg-[#050508] min-h-screen overflow-y-auto">

      {/* ── Hero ─────────────────────────────────────────────────── */}
      <div className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden">
        <AnimatedGradientBackground
          gradientColors={['#050508', '#0d1240', '#1a0533', '#080e38', '#1a1040', '#0a0820', '#050508']}
          gradientStops={[30, 48, 58, 68, 78, 90, 100]}
          Breathing={true}
          breathingRange={10}
          animationSpeed={0.012}
        />

        <div className="relative z-10 text-center px-6 max-w-4xl mx-auto space-y-8">

          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.6 }}
            className="inline-flex items-center gap-2 bg-white/8 border border-white/15 rounded-full px-5 py-2 text-xs text-white/50 tracking-widest uppercase"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Voice-first AI for Hinglish conversations
          </motion.div>

          {/* Title */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.45, duration: 0.7 }}
            className="text-[clamp(4rem,16vw,9rem)] font-black text-white tracking-[-0.04em] leading-none"
          >
            AWAAZ
          </motion.h1>

          {/* Tagline */}
          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6, duration: 0.6 }}
            className="text-xl md:text-2xl text-white/40 font-light max-w-md mx-auto leading-relaxed"
          >
            Your words.&nbsp; Your emotion.&nbsp;
            <span className="text-white/70">Delivered perfectly.</span>
          </motion.p>

          {/* Feature cards */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.75, duration: 0.6 }}
            className="grid grid-cols-3 gap-3 max-w-2xl mx-auto"
          >
            {features.map(f => (
              <div
                key={f.title}
                className="bg-white/5 border border-white/10 rounded-2xl p-4 text-left hover:bg-white/8 transition-colors"
              >
                <div className="text-2xl mb-2">{f.icon}</div>
                <div className="text-white font-semibold text-sm">{f.title}</div>
                <div className="text-white/35 text-xs mt-1 leading-snug">{f.desc}</div>
              </div>
            ))}
          </motion.div>

          {/* CTA */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.9, duration: 0.5 }}
          >
            <button
              onClick={onEnter}
              className="group relative bg-white text-black font-bold text-base px-10 py-4 rounded-full hover:scale-105 active:scale-95 transition-transform shadow-2xl shadow-white/10"
            >
              Enter Awaaz
              <span className="ml-2 inline-block transition-transform group-hover:translate-x-1">→</span>
            </button>
          </motion.div>

          {/* Scroll hint */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.4, duration: 0.8 }}
            className="flex flex-col items-center gap-2 pt-4"
          >
            <span className="text-white/20 text-xs tracking-widest uppercase">Scroll to explore</span>
            <motion.div
              animate={{ y: [0, 6, 0] }}
              transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
              className="w-px h-6 bg-gradient-to-b from-white/30 to-transparent"
            />
          </motion.div>
        </div>
      </div>

      {/* ── Scroll Demo ──────────────────────────────────────────── */}
      <div className="bg-[#050508]">
        <ContainerScroll
          titleComponent={
            <div className="text-center space-y-3">
              <p className="text-white/30 text-xs font-semibold uppercase tracking-widest">How it works</p>
              <h2 className="text-3xl md:text-4xl font-bold text-white leading-tight">
                Voice in. Expression out.
              </h2>
              <p className="text-white/40 text-sm max-w-sm mx-auto">
                Under 5 seconds from mic tap to expressive speech — every time.
              </p>
            </div>
          }
        >
          {/* ── Mock app UI ── */}
          <div className="h-full bg-[#0a0a12] rounded-2xl p-5 flex flex-col gap-3 font-mono text-xs">

            {/* Top bar */}
            <div className="flex items-center justify-between">
              <span className="text-white/60 font-black text-sm tracking-tight">AWAAZ</span>
              <div className="flex items-center gap-2">
                <span className="bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full text-[10px] font-semibold">2.3s</span>
                <div className="w-6 h-6 rounded-full bg-indigo-500/30 flex items-center justify-center text-[10px] text-indigo-300">R</div>
              </div>
            </div>

            {/* Speaker row */}
            <div className="flex items-center gap-2 bg-white/5 rounded-xl p-2.5">
              <div className="relative">
                <div className="w-7 h-7 rounded-full bg-indigo-500/30 flex items-center justify-center text-[10px] font-bold text-indigo-300">R</div>
                <div className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 bg-green-500 border border-[#0a0a12] rounded-full" />
              </div>
              <div>
                <div className="text-white/70 font-semibold">Raj</div>
                <div className="text-white/25 text-[10px]">friend · 94% match</div>
              </div>
            </div>

            {/* Transcript card */}
            <div className="bg-white/5 rounded-xl p-3">
              <div className="text-white/30 text-[10px] mb-1 uppercase tracking-widest">Transcript</div>
              <div className="text-white/65">Yaar sun, I have this amazing idea for the app, you have to hear this—</div>
            </div>

            {/* Expressive text card */}
            <div className="bg-indigo-900/30 border border-indigo-500/20 rounded-xl p-3">
              <div className="text-indigo-300/60 text-[10px] mb-1 uppercase tracking-widest">Expressive · auto-inferred: excited</div>
              <div className="text-white/75">
                Yaar sun, <span className="text-yellow-300/80">&lt;excited&gt;</span> I have this amazing idea for the app,{' '}
                <span className="text-yellow-300/80">&lt;gasp&gt;</span> you have to hear this—
              </div>
            </div>

            {/* Waveform */}
            <div className="flex-1 flex items-end gap-px px-1">
              {Array.from({ length: 48 }, (_, i) => {
                const h = Math.abs(Math.sin(i * 0.35) * 0.6 + Math.sin(i * 0.8) * 0.4)
                return (
                  <div
                    key={i}
                    className="flex-1 rounded-full"
                    style={{
                      height: `${Math.max(10, h * 100)}%`,
                      background: `rgba(99,102,241,${0.2 + h * 0.5})`,
                    }}
                  />
                )
              })}
            </div>

            {/* Action buttons */}
            <div className="flex gap-2">
              <div className="flex-1 bg-emerald-500 rounded-xl py-2 text-center text-white font-semibold text-xs">
                ▶ Speak It
              </div>
              <div className="flex-1 bg-white/8 rounded-xl py-2 text-center text-white/40 text-xs">
                ↺ Retry
              </div>
            </div>

            {/* Voice dock mock */}
            <div className="flex items-center justify-center gap-2 pt-1">
              {[
                { label: 'R', color: 'indigo', active: true },
                { label: 'M', color: 'purple', active: false },
                { label: 'A', color: 'rose', active: false },
              ].map(v => (
                <div key={v.label} className="relative">
                  <div className={`w-7 h-7 rounded-full bg-${v.color}-500/20 flex items-center justify-center text-[10px] font-bold text-${v.color}-300`}>
                    {v.label}
                  </div>
                  <div className={`absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full border border-[#0a0a12] ${v.active ? 'bg-green-500' : 'bg-red-500'}`} />
                </div>
              ))}
            </div>
          </div>
        </ContainerScroll>
      </div>

      {/* ── Footer ───────────────────────────────────────────────── */}
      <div className="relative bg-[#050508] py-12 text-center border-t border-white/5">
        <p className="text-white/20 text-xs">Awaaz · Emotion-aware voice delivery for Hinglish</p>
        <button
          onClick={onEnter}
          className="mt-6 group text-white/50 hover:text-white text-sm transition-colors"
        >
          Enter now <span className="group-hover:translate-x-1 inline-block transition-transform">→</span>
        </button>
      </div>
    </div>
  )
}
