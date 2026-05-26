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
    <div className="relative bg-[#0A0A0A] min-h-screen overflow-y-auto">

      {/* ── Hero ─────────────────────────────────────────────────── */}
      <div className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden">
        <AnimatedGradientBackground
          Breathing={true}
          breathingRange={5}
          animationSpeed={0.02}
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
      <div className="bg-[#0A0A0A]">
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
          {/* ── Faithful replica of the real empty-state UI ── */}
          <div className="h-full rounded-2xl flex flex-col overflow-hidden relative"
            style={{ background: '#000' }}
          >
            {/* Blue-purple orb — matches the actual app background */}
            <div className="absolute inset-0 rounded-2xl" style={{
              background: [
                'radial-gradient(ellipse 160% 110% at 50% 125%, #4040b8 0%, #3030a8 12%, #202080 25%, #121250 40%, #080830 55%, transparent 70%)',
                'radial-gradient(ellipse 100% 70% at 50% 120%, rgba(80,70,200,0.35) 0%, transparent 55%)',
              ].join(', '),
            }} />

            {/* Header */}
            <div className="relative z-10 flex items-center justify-between px-4 py-3 border-b border-white/10 flex-shrink-0">
              <span className="text-white font-black text-sm tracking-[-0.04em]">AWAAZ</span>
              <div className="w-7 h-7 rounded-full bg-indigo-500/40 border border-indigo-400/30 flex items-center justify-center text-[10px] font-bold text-indigo-200">
                D
              </div>
            </div>

            {/* Example chat exchanges */}
            <div className="relative z-10 flex-1 flex flex-col justify-end px-3 py-2 gap-2 overflow-hidden">

              {/* Exchange 1 */}
              <div className="space-y-1">
                <div className="bg-white/4 border border-white/8 rounded-xl p-2.5">
                  <p className="text-[8px] text-white/25 uppercase tracking-widest mb-1">They said</p>
                  <p className="text-white/55 text-[10px] leading-relaxed">Yaar sun, I have this amazing idea—</p>
                </div>
                <div className="bg-indigo-900/15 border border-indigo-500/20 rounded-xl p-2.5">
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="text-[8px] bg-indigo-500/15 text-indigo-300 px-1.5 py-0.5 rounded-full font-mono">excited</span>
                    <span className="text-[8px] text-emerald-400/70 font-mono">2.3s</span>
                  </div>
                  <p className="text-white/70 text-[10px] leading-relaxed font-mono">
                    Haan bata! <span className="text-yellow-300/80">&lt;excited&gt;</span> kya idea hai yaar?
                  </p>
                </div>
              </div>

              {/* Exchange 2 */}
              <div className="space-y-1">
                <div className="bg-white/4 border border-white/8 rounded-xl p-2.5">
                  <p className="text-[8px] text-white/25 uppercase tracking-widest mb-1">They said</p>
                  <p className="text-white/55 text-[10px] leading-relaxed">Seriously bro, you're gonna love this</p>
                </div>
                <div className="bg-indigo-900/15 border border-indigo-500/20 rounded-xl p-2.5">
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="text-[8px] bg-indigo-500/15 text-indigo-300 px-1.5 py-0.5 rounded-full font-mono">laughing</span>
                    <span className="text-[8px] text-emerald-400/70 font-mono">1.8s</span>
                  </div>
                  <p className="text-white/70 text-[10px] leading-relaxed font-mono">
                    <span className="text-yellow-300/80">&lt;chuckle&gt;</span> pakka yaar, jaldi bol na!
                  </p>
                </div>
              </div>

            </div>

            {/* Emotion dock — white pill, matches real dock exactly */}
            <div className="relative z-10 flex justify-center pb-2.5">
              <div className="flex items-center gap-0.5 bg-white shadow-2xl rounded-full px-2.5 py-1.5">
                {[
                  { e: '🎭', dot: true },
                  { e: '😊', dot: false },
                  { e: '🤩', dot: false },
                  { e: '😌', dot: false },
                  { e: '😏', dot: false },
                  { e: '😠', dot: false },
                  { e: '🤫', dot: false },
                  { e: '😐', dot: false },
                ].map(({ e, dot }, i) => (
                  <div key={i} className="relative w-7 h-7 flex items-center justify-center text-base">
                    {e}
                    {dot && <div className="absolute bottom-0 right-0 w-2 h-2 bg-green-500 border-2 border-white rounded-full" />}
                  </div>
                ))}
                <div className="w-px h-4 bg-gray-200 mx-1" />
                <div className="w-7 h-7 flex items-center justify-center text-gray-400 text-sm font-semibold">+</div>
              </div>
            </div>

            {/* Input bar */}
            <div className="relative z-10 px-2.5 pb-3">
              <div className="bg-white/8 border border-white/10 rounded-2xl flex items-center gap-2 px-2 py-1.5">
                <div className="w-8 h-8 rounded-xl bg-white/10 flex items-center justify-center flex-shrink-0">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.5)" strokeWidth="1.8">
                    <rect x="9" y="2" width="6" height="12" rx="3" />
                    <path d="M5 10a7 7 0 0 0 14 0" />
                    <line x1="12" y1="19" x2="12" y2="22" />
                    <line x1="8" y1="22" x2="16" y2="22" />
                  </svg>
                </div>
                <div className="flex-1 text-white/25 text-[10px]">Type what you want to say… (Enter to send)</div>
                <div className="w-8 h-8 rounded-xl bg-white/90 flex items-center justify-center flex-shrink-0">
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#050508" strokeWidth="2.5">
                    <path d="M12 19V5M5 12l7-7 7 7" />
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </ContainerScroll>
      </div>

      {/* ── Footer ───────────────────────────────────────────────── */}
      <div className="relative bg-[#0A0A0A] py-12 text-center border-t border-white/5">
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
