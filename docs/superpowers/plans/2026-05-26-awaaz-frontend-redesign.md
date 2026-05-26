# Awaaz Frontend Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `frontend.html` with a modular Vite + React + TypeScript + Tailwind SPA featuring three Aceternity UI components recontextualized for the Awaaz voice pipeline, with live per-stage latency counters.

**Architecture:** Single-page React app in `frontend/`. HeroHighlight is the full-screen dark background shell. ContainerScroll provides a scroll-animated entry on Onboarding. A vertical VerticalMoodDock sits fixed on the right side of the Main screen — clicking a mood slides open an input panel leftward; submitting triggers the pipeline. Live latency ticks via `requestAnimationFrame` inside a `useLatency` hook; each pipeline stage owns its own latency state. Built by Vite, served from `frontend/dist/` via FastAPI `StaticFiles` at `/ui`.

**Tech Stack:** Vite 5, React 18, TypeScript 5, Tailwind CSS 3, framer-motion 11, clsx, tailwind-merge

---

## File Map

| File | Responsibility |
|------|---------------|
| `frontend/package.json` | deps, scripts |
| `frontend/vite.config.ts` | proxy `/api` → `localhost:8000`, output to `dist/` |
| `frontend/tsconfig.json` | strict TS config |
| `frontend/tailwind.config.js` | content paths, dark mode: `class` |
| `frontend/postcss.config.js` | tailwind + autoprefixer |
| `frontend/index.html` | SPA root |
| `frontend/src/main.tsx` | React root, adds `dark` class to html |
| `frontend/src/index.css` | Tailwind directives |
| `frontend/src/lib/utils.ts` | `cn()` helper |
| `frontend/src/lib/api.ts` | all fetch wrappers |
| `frontend/src/hooks/useRecorder.ts` | MediaRecorder logic |
| `frontend/src/hooks/useLatency.ts` | live rAF-based elapsed timer |
| `frontend/src/components/ui/hero-highlight.tsx` | HeroHighlight + Highlight (from spec) |
| `frontend/src/components/ui/container-scroll-animation.tsx` | ContainerScroll (from spec) |
| `frontend/src/components/ui/vertical-mood-dock.tsx` | Vertical right-side mood dock (adapted MessageDock) |
| `frontend/src/components/Toast.tsx` | toast notification system |
| `frontend/src/components/AudioPlayer.tsx` | TTS audio player |
| `frontend/src/components/PipelineStages.tsx` | STT/Speaker/LLM/TTS stage cards with live latency |
| `frontend/src/components/Pipeline.tsx` | mic button + form controls |
| `frontend/src/components/Profile.tsx` | personality dim editor |
| `frontend/src/pages/Onboarding.tsx` | name + 10-question quiz using ContainerScroll |
| `frontend/src/pages/Main.tsx` | HeroHighlight shell + Pipeline + PipelineStages + VerticalMoodDock |
| `frontend/src/App.tsx` | profile check → route to Onboarding or Main |
| `main.py` | update StaticFiles mount path |

---

## Task 1: Scaffold Vite project

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/postcss.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/index.css`

- [ ] **Step 1: Create `frontend/package.json`**

```json
{
  "name": "awaaz-frontend",
  "private": true,
  "version": "0.0.1",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "clsx": "^2.1.1",
    "framer-motion": "^11.3.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "tailwind-merge": "^2.4.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.40",
    "tailwindcss": "^3.4.7",
    "typescript": "^5.5.3",
    "vite": "^5.4.0"
  }
}
```

- [ ] **Step 2: Create `frontend/vite.config.ts`**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/pipeline': 'http://localhost:8000',
      '/onboarding': 'http://localhost:8000',
      '/tts_output': 'http://localhost:8000',
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
```

- [ ] **Step 3: Create `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"]
}
```

- [ ] **Step 4: Create `frontend/tailwind.config.js`**

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: { extend: {} },
  plugins: [],
}
```

- [ ] **Step 5: Create `frontend/postcss.config.js`**

```javascript
export default {
  plugins: { tailwindcss: {}, autoprefixer: {} },
}
```

- [ ] **Step 6: Create `frontend/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Awaaz — Your Voice, Your Vibe</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 7: Create `frontend/src/index.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

* { box-sizing: border-box; }

body {
  font-family: 'Inter', -apple-system, sans-serif;
  -webkit-font-smoothing: antialiased;
}

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }
```

- [ ] **Step 8: Create `frontend/src/main.tsx`**

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'

// enable dark mode globally
document.documentElement.classList.add('dark')

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

- [ ] **Step 9: Install dependencies**

```bash
cd frontend && npm install
```

Expected: `node_modules/` created, no errors.

- [ ] **Step 10: Verify dev server starts**

```bash
cd frontend && npm run dev
```

Expected: `VITE v5.x ready` on `http://localhost:5173`. Ctrl+C to stop.

- [ ] **Step 11: Commit**

```bash
git add frontend/package.json frontend/vite.config.ts frontend/tsconfig.json frontend/tailwind.config.js frontend/postcss.config.js frontend/index.html frontend/src/main.tsx frontend/src/index.css frontend/package-lock.json
git commit -m "feat: scaffold Vite + React + TS + Tailwind frontend"
```

---

## Task 2: lib/utils.ts and lib/api.ts

**Files:**
- Create: `frontend/src/lib/utils.ts`
- Create: `frontend/src/lib/api.ts`

- [ ] **Step 1: Create `frontend/src/lib/utils.ts`**

```typescript
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

- [ ] **Step 2: Create `frontend/src/lib/api.ts`**

```typescript
export interface ProfilePayload {
  profile_id?: string
  name: string
  personality: Record<string, string>
  custom_vibe?: string
}

export interface ProfilesResponse {
  profiles: Profile[]
  active_id: string | null
}

export interface Profile {
  profile_id: string
  name: string
  personality: Record<string, string>
  custom_vibe?: string
}

export interface ProcessResponse {
  session_id: string
  transcript: string
  speaker: {
    name: string | null
    similarity: number
    relationship: string | null
  }
  llm: {
    expressive_text: string
    reasoning: string
    detected_mood: string
  }
  save_voice_prompt: boolean
}

export interface ApproveResponse {
  tts_audio_url: string
  tts_payload: { speaker: string; description: string; text: string }
}

export interface DenyResponse {
  session_id: string
  llm: {
    expressive_text: string
    reasoning: string
    detected_mood: string
  }
}

export const api = {
  async getProfiles(): Promise<ProfilesResponse> {
    const r = await fetch('/onboarding/profiles')
    if (!r.ok) throw new Error('Failed to fetch profiles')
    return r.json()
  },

  async saveProfile(payload: ProfilePayload): Promise<Profile> {
    const r = await fetch('/onboarding', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!r.ok) throw new Error(await r.text())
    return r.json()
  },

  async activateProfile(profileId: string): Promise<void> {
    const r = await fetch(`/onboarding/profiles/${profileId}/activate`, { method: 'PUT' })
    if (!r.ok) throw new Error('Failed to switch profile')
  },

  async processAudio(
    blob: Blob,
    relationship: string,
    moodOverride: string,
    extraText: string,
  ): Promise<ProcessResponse> {
    const fd = new FormData()
    fd.append('audio', blob, 'recording.webm')
    fd.append('relationship', relationship)
    fd.append('mood_override', moodOverride)
    if (extraText) fd.append('extra_text', extraText)
    const r = await fetch('/pipeline/process', { method: 'POST', body: fd })
    if (!r.ok) throw new Error(await r.text())
    return r.json()
  },

  async approve(sessionId: string): Promise<ApproveResponse> {
    const r = await fetch('/pipeline/approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId }),
    })
    if (!r.ok) throw new Error(await r.text())
    return r.json()
  },

  async deny(
    sessionId: string,
    overrides: { mood_override?: string; relationship_override?: string; extra_text?: string },
  ): Promise<DenyResponse> {
    const r = await fetch('/pipeline/deny', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, ...overrides }),
    })
    if (!r.ok) throw new Error(await r.text())
    return r.json()
  },

  async saveSpeaker(sessionId: string, name: string, relationship: string): Promise<void> {
    const fd = new FormData()
    fd.append('session_id', sessionId)
    fd.append('name', name)
    fd.append('relationship', relationship)
    const r = await fetch('/pipeline/save-speaker', { method: 'POST', body: fd })
    if (!r.ok) throw new Error(await r.text())
  },

  async deleteAllSpeakers(): Promise<{ deleted: number }> {
    const r = await fetch('/pipeline/speakers', { method: 'DELETE' })
    if (!r.ok) throw new Error('Failed to delete speakers')
    return r.json()
  },
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/
git commit -m "feat: add cn utility and API client"
```

---

## Task 3: HeroHighlight UI component

**Files:**
- Create: `frontend/src/components/ui/hero-highlight.tsx`

- [ ] **Step 1: Create `frontend/src/components/ui/hero-highlight.tsx`**

```tsx
"use client";
import { cn } from "@/lib/utils";
import { useMotionValue, motion, useMotionTemplate } from "framer-motion";
import React from "react";

export const HeroHighlight = ({
  children,
  className,
  containerClassName,
}: {
  children: React.ReactNode;
  className?: string;
  containerClassName?: string;
}) => {
  let mouseX = useMotionValue(0);
  let mouseY = useMotionValue(0);

  function handleMouseMove({ currentTarget, clientX, clientY }: React.MouseEvent<HTMLDivElement>) {
    if (!currentTarget) return;
    let { left, top } = currentTarget.getBoundingClientRect();
    mouseX.set(clientX - left);
    mouseY.set(clientY - top);
  }

  const dotPattern = (color: string) => ({
    backgroundImage: `radial-gradient(circle, ${color} 1px, transparent 1px)`,
    backgroundSize: '16px 16px',
  });

  return (
    <div
      className={cn(
        "relative min-h-screen flex items-start bg-white dark:bg-black justify-center w-full group",
        containerClassName
      )}
      onMouseMove={handleMouseMove}
    >
      <div className="absolute inset-0 pointer-events-none opacity-70" style={dotPattern('rgb(212 212 212)')} />
      <div className="absolute inset-0 dark:opacity-70 opacity-0 pointer-events-none" style={dotPattern('rgb(38 38 38)')} />
      <motion.div
        className="pointer-events-none absolute inset-0 opacity-0 transition duration-300 group-hover:opacity-100"
        style={{
          ...dotPattern('rgb(99 102 241)'),
          WebkitMaskImage: useMotionTemplate`radial-gradient(200px circle at ${mouseX}px ${mouseY}px, black 0%, transparent 100%)`,
          maskImage: useMotionTemplate`radial-gradient(200px circle at ${mouseX}px ${mouseY}px, black 0%, transparent 100%)`,
        }}
      />
      <div className={cn("relative z-20 w-full", className)}>{children}</div>
    </div>
  );
};

export const Highlight = ({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) => {
  return (
    <motion.span
      initial={{ backgroundSize: "0% 100%" }}
      animate={{ backgroundSize: "100% 100%" }}
      transition={{ duration: 2, ease: "linear", delay: 0.5 }}
      style={{ backgroundRepeat: "no-repeat", backgroundPosition: "left center", display: "inline" }}
      className={cn(
        "relative inline-block pb-1 px-1 rounded-lg bg-gradient-to-r from-indigo-300 to-purple-300 dark:from-indigo-500 dark:to-purple-500",
        className
      )}
    >
      {children}
    </motion.span>
  );
};
```

Note: The `@/lib/utils` import alias requires `vite.config.ts` to resolve `@` to `src/`. Add this to `frontend/vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    proxy: {
      '/pipeline': 'http://localhost:8000',
      '/onboarding': 'http://localhost:8000',
      '/tts_output': 'http://localhost:8000',
    },
  },
  build: { outDir: 'dist', emptyOutDir: true },
})
```

Also add to `frontend/tsconfig.json` under `compilerOptions`:
```json
"paths": { "@/*": ["./src/*"] },
"baseUrl": "."
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ui/hero-highlight.tsx frontend/vite.config.ts frontend/tsconfig.json
git commit -m "feat: add HeroHighlight component"
```

---

## Task 4: ContainerScroll UI component

**Files:**
- Create: `frontend/src/components/ui/container-scroll-animation.tsx`

- [ ] **Step 1: Create `frontend/src/components/ui/container-scroll-animation.tsx`**

```tsx
"use client";
import React, { useRef } from "react";
import { useScroll, useTransform, motion, MotionValue } from "framer-motion";

export const ContainerScroll = ({
  titleComponent,
  children,
}: {
  titleComponent: string | React.ReactNode;
  children: React.ReactNode;
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: containerRef });
  const [isMobile, setIsMobile] = React.useState(false);

  React.useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth <= 768);
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  const scaleDimensions = () => isMobile ? [0.7, 0.9] : [1.05, 1];
  const rotate = useTransform(scrollYProgress, [0, 1], [20, 0]);
  const scale = useTransform(scrollYProgress, [0, 1], scaleDimensions());
  const translate = useTransform(scrollYProgress, [0, 1], [0, -100]);

  return (
    <div className="h-[60rem] md:h-[80rem] flex items-center justify-center relative p-2 md:p-20" ref={containerRef}>
      <div className="py-10 md:py-40 w-full relative" style={{ perspective: "1000px" }}>
        <Header translate={translate} titleComponent={titleComponent} />
        <Card rotate={rotate} translate={translate} scale={scale}>{children}</Card>
      </div>
    </div>
  );
};

export const Header = ({ translate, titleComponent }: { translate: MotionValue<number>; titleComponent: React.ReactNode }) => (
  <motion.div style={{ translateY: translate }} className="max-w-5xl mx-auto text-center">
    {titleComponent}
  </motion.div>
);

export const Card = ({
  rotate, scale, children,
}: {
  rotate: MotionValue<number>;
  scale: MotionValue<number>;
  translate: MotionValue<number>;
  children: React.ReactNode;
}) => (
  <motion.div
    style={{
      rotateX: rotate,
      scale,
      boxShadow: "0 0 #0000004d, 0 9px 20px #0000004a, 0 37px 37px #00000042, 0 84px 50px #00000026, 0 149px 60px #0000000a, 0 233px 65px #00000003",
    }}
    className="max-w-5xl -mt-12 mx-auto h-[30rem] md:h-[40rem] w-full border-4 border-[#6C6C6C] p-2 md:p-6 bg-[#222222] rounded-[30px] shadow-2xl"
  >
    <div className="h-full w-full overflow-hidden rounded-2xl bg-gray-100 dark:bg-zinc-900 md:rounded-2xl md:p-4">
      {children}
    </div>
  </motion.div>
);
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ui/container-scroll-animation.tsx
git commit -m "feat: add ContainerScroll component"
```

---

## Task 5: VerticalMoodDock component

**Files:**
- Create: `frontend/src/components/ui/vertical-mood-dock.tsx`

This is a vertical adaptation of the MessageDock concept. The pill is fixed to the right side, stacked vertically. When a mood is selected, a panel slides out to the LEFT.

- [ ] **Step 1: Create `frontend/src/components/ui/vertical-mood-dock.tsx`**

```tsx
import { cn } from '@/lib/utils'
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion'
import { useState, useEffect, useRef } from 'react'

export interface Mood {
  id: string
  emoji: string
  name: string
  bg: string
  gradientColors: string
}

export const MOODS: Mood[] = [
  { id: 'auto',      emoji: '🎭', name: 'Auto',      bg: 'bg-violet-300', gradientColors: '#c4b5fd, #ede9fe' },
  { id: 'happy',     emoji: '😊', name: 'Happy',     bg: 'bg-yellow-300', gradientColors: '#fde047, #fef9c3' },
  { id: 'excited',   emoji: '🤩', name: 'Excited',   bg: 'bg-orange-300', gradientColors: '#fdba74, #fff7ed' },
  { id: 'sarcastic', emoji: '😏', name: 'Sarcastic', bg: 'bg-emerald-300',gradientColors: '#6ee7b7, #d1fae5' },
  { id: 'sad',       emoji: '😢', name: 'Sad',       bg: 'bg-blue-300',   gradientColors: '#93c5fd, #eff6ff' },
  { id: 'angry',     emoji: '😠', name: 'Angry',     bg: 'bg-red-300',    gradientColors: '#fca5a5, #fef2f2' },
]

export interface VerticalMoodDockProps {
  canProcess: boolean
  onProcess: (moodId: string, extraText: string) => void
  className?: string
}

export function VerticalMoodDock({ canProcess, onProcess, className }: VerticalMoodDockProps) {
  const shouldReduceMotion = useReducedMotion()
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null)
  const [extraText, setExtraText] = useState('')
  const dockRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const selectedMood = selectedIdx !== null ? MOODS[selectedIdx] : null
  const isExpanded = selectedIdx !== null

  // focus input when expanded
  useEffect(() => {
    if (isExpanded) setTimeout(() => inputRef.current?.focus(), 200)
  }, [isExpanded])

  // click outside to close
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dockRef.current && !dockRef.current.contains(e.target as Node)) {
        setSelectedIdx(null)
        setExtraText('')
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleSelect = (idx: number) => {
    setSelectedIdx(prev => prev === idx ? null : idx)
    setExtraText('')
  }

  const handleSend = () => {
    if (!canProcess || selectedIdx === null) return
    onProcess(MOODS[selectedIdx].id, extraText)
    setSelectedIdx(null)
    setExtraText('')
  }

  const springFast = { type: 'spring' as const, stiffness: 420, damping: 32 }
  const hoverAnim = shouldReduceMotion ? {} : { scale: 1.12, x: -4, transition: springFast }

  return (
    <div ref={dockRef} className={cn('fixed right-6 top-1/2 -translate-y-1/2 z-50 flex items-center gap-3', className)}>
      {/* Expanded panel — slides LEFT from the dock */}
      <AnimatePresence>
        {isExpanded && selectedMood && (
          <motion.div
            key="panel"
            initial={{ opacity: 0, x: 24, scaleX: 0.85 }}
            animate={{ opacity: 1, x: 0, scaleX: 1 }}
            exit={{ opacity: 0, x: 24, scaleX: 0.85 }}
            transition={springFast}
            style={{
              originX: 1,
              background: `linear-gradient(135deg, ${selectedMood.gradientColors})`,
            }}
            className="w-64 rounded-2xl px-4 py-4 shadow-2xl border border-white/40"
          >
            {/* Mood label */}
            <div className="flex items-center gap-2 mb-3">
              <span className="text-2xl">{selectedMood.emoji}</span>
              <div>
                <p className="text-xs font-semibold uppercase tracking-widest text-gray-500">Mood</p>
                <p className="text-sm font-bold text-gray-800 leading-none">{selectedMood.name}</p>
              </div>
            </div>

            {/* Context input */}
            <input
              ref={inputRef}
              type="text"
              value={extraText}
              onChange={e => setExtraText(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') handleSend()
                if (e.key === 'Escape') { setSelectedIdx(null); setExtraText('') }
              }}
              placeholder="Extra context… (optional)"
              className="w-full rounded-xl bg-white/60 border border-white/50 px-3 py-2 text-sm text-gray-700 placeholder-gray-400 outline-none focus:bg-white/80 transition-colors"
            />

            {/* Send button */}
            <motion.button
              onClick={handleSend}
              disabled={!canProcess}
              whileHover={canProcess ? { scale: 1.03 } : {}}
              whileTap={canProcess ? { scale: 0.97 } : {}}
              className="mt-2 w-full rounded-xl bg-white/70 hover:bg-white py-2 text-sm font-semibold text-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
              {canProcess ? 'Generate Response' : 'Record first'}
              {canProcess && (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              )}
            </motion.button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Vertical pill */}
      <motion.div
        initial={{ opacity: 0, x: 60 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ type: 'spring', stiffness: 300, damping: 28, delay: 0.2 }}
        className="rounded-full px-2 py-3 bg-white dark:bg-neutral-900 shadow-2xl border border-gray-200/60 dark:border-neutral-700/60 flex flex-col items-center gap-1.5"
      >
        {/* Sparkle / auto button */}
        <motion.button
          className="w-11 h-11 flex items-center justify-center rounded-full"
          whileHover={hoverAnim}
          whileTap={{ scale: 0.92 }}
          onClick={() => handleSelect(0)}
          aria-label="Auto mood"
        >
          <span className="text-2xl">{MOODS[0].emoji}</span>
        </motion.button>

        {/* Separator */}
        <div className="w-6 h-px bg-gray-200 dark:bg-neutral-700 my-0.5" />

        {/* Mood characters 1–5 */}
        {MOODS.slice(1).map((mood, i) => {
          const idx = i + 1
          const isSelected = selectedIdx === idx
          return (
            <motion.button
              key={mood.id}
              className={cn(
                'relative w-10 h-10 rounded-full flex items-center justify-center text-xl transition-shadow',
                isSelected ? 'bg-white shadow-lg ring-2 ring-white/80' : mood.bg,
              )}
              onClick={() => handleSelect(idx)}
              animate={{
                opacity: isExpanded && !isSelected ? 0.35 : 1,
                scale: isSelected ? 1.15 : 1,
              }}
              transition={springFast}
              whileHover={!isExpanded ? hoverAnim : { scale: 1.08 }}
              whileTap={{ scale: 0.92 }}
              aria-label={`${mood.name} mood`}
            >
              {mood.emoji}
              {/* online dot */}
              <motion.div
                className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-green-400 border-2 border-white rounded-full"
                initial={{ scale: 0 }}
                animate={{ scale: isExpanded && !isSelected ? 0 : 1 }}
                transition={{ type: 'spring', stiffness: 500, damping: 30, delay: isSelected ? 0.2 : 0 }}
              />
            </motion.button>
          )
        })}

        {/* Separator */}
        <div className="w-6 h-px bg-gray-200 dark:bg-neutral-700 my-0.5" />

        {/* Close / menu button */}
        <motion.button
          className="w-11 h-11 flex items-center justify-center text-gray-400 dark:text-neutral-500"
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.92 }}
          onClick={() => { setSelectedIdx(null); setExtraText('') }}
          aria-label={isExpanded ? 'Close' : 'Menu'}
        >
          <AnimatePresence mode="wait">
            {isExpanded ? (
              <motion.svg key="x" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
                initial={{ rotate: -90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ rotate: 90, opacity: 0 }}
                transition={{ duration: 0.15 }}>
                <path d="M18 6L6 18M6 6l12 12" />
              </motion.svg>
            ) : (
              <motion.svg key="menu" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                initial={{ rotate: 90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ rotate: -90, opacity: 0 }}
                transition={{ duration: 0.15 }}>
                <line x1="4" y1="6" x2="20" y2="6" />
                <line x1="4" y1="12" x2="20" y2="12" />
                <line x1="4" y1="18" x2="20" y2="18" />
              </motion.svg>
            )}
          </AnimatePresence>
        </motion.button>
      </motion.div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ui/vertical-mood-dock.tsx
git commit -m "feat: add vertical mood dock (adapted MessageDock, right-side with leftward expansion)"
```

---

## Task 6: useRecorder hook

**Files:**
- Create: `frontend/src/hooks/useRecorder.ts`

- [ ] **Step 1: Create `frontend/src/hooks/useRecorder.ts`**

```typescript
import { useState, useRef, useCallback } from 'react'

export type RecorderState = 'idle' | 'recording' | 'ready'

export function useRecorder() {
  const [state, setState] = useState<RecorderState>('idle')
  const [blob, setBlob] = useState<Blob | null>(null)
  const [seconds, setSeconds] = useState(0)

  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const start = useCallback(async () => {
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      return false
    }

    chunksRef.current = []
    setBlob(null)
    setSeconds(0)

    const mime = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'].find(m =>
      MediaRecorder.isTypeSupported(m),
    ) ?? ''

    const recorder = new MediaRecorder(stream, mime ? { mimeType: mime } : {})
    recorderRef.current = recorder

    recorder.ondataavailable = e => {
      if (e.data.size > 0) chunksRef.current.push(e.data)
    }
    recorder.onstop = () => {
      const b = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' })
      setBlob(b)
      setState('ready')
      stream.getTracks().forEach(t => t.stop())
    }

    recorder.start(100)
    setState('recording')

    intervalRef.current = setInterval(() => setSeconds(s => s + 1), 1000)
    return true
  }, [])

  const stop = useCallback(() => {
    if (recorderRef.current && recorderRef.current.state !== 'inactive') {
      recorderRef.current.stop()
    }
    if (intervalRef.current) clearInterval(intervalRef.current)
    intervalRef.current = null
  }, [])

  const reset = useCallback(() => {
    stop()
    setBlob(null)
    setSeconds(0)
    setState('idle')
  }, [stop])

  const toggle = useCallback(async () => {
    if (state === 'recording') stop()
    else await start()
  }, [state, start, stop])

  const formatSeconds = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`

  return { state, blob, seconds, formattedTime: formatSeconds(seconds), start, stop, reset, toggle }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/useRecorder.ts
git commit -m "feat: add useRecorder hook"
```

---

## Task 7: useLatency hook

**Files:**
- Create: `frontend/src/hooks/useLatency.ts`

- [ ] **Step 1: Create `frontend/src/hooks/useLatency.ts`**

```typescript
import { useRef, useState, useCallback } from 'react'

export function useLatency() {
  const [elapsed, setElapsed] = useState(0)
  const [frozen, setFrozen] = useState<number | null>(null)
  const startRef = useRef<number | null>(null)
  const rafRef = useRef<number | null>(null)

  const tick = useCallback(() => {
    if (startRef.current === null) return
    setElapsed(Date.now() - startRef.current)
    rafRef.current = requestAnimationFrame(tick)
  }, [])

  const start = useCallback(() => {
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
    startRef.current = Date.now()
    setElapsed(0)
    setFrozen(null)
    rafRef.current = requestAnimationFrame(tick)
  }, [tick])

  const stop = useCallback((): number => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current)
      rafRef.current = null
    }
    const final = startRef.current !== null ? Date.now() - startRef.current : 0
    startRef.current = null
    setFrozen(final)
    return final
  }, [])

  const reset = useCallback(() => {
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
    rafRef.current = null
    startRef.current = null
    setElapsed(0)
    setFrozen(null)
  }, [])

  const format = (ms: number) =>
    ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(2)}s`

  const displayMs = frozen ?? elapsed

  return {
    elapsed,
    frozen,
    isRunning: rafRef.current !== null,
    formatted: format(displayMs),
    displayMs,
    start,
    stop,
    reset,
    format,
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/useLatency.ts
git commit -m "feat: add useLatency hook (rAF-based, freezes on stop)"
```

---

## Task 8: Toast and Overlay components

**Files:**
- Create: `frontend/src/components/Toast.tsx`
- Create: `frontend/src/components/Overlay.tsx`

- [ ] **Step 1: Create `frontend/src/components/Toast.tsx`**

```tsx
import { useState, useCallback, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface ToastItem { id: number; message: string; type: 'ok' | 'err' }

let _push: ((msg: string, type: 'ok' | 'err') => void) | null = null

export function toast(message: string, type: 'ok' | 'err' = 'ok') {
  _push?.(message, type)
}

export function ToastProvider() {
  const [items, setItems] = useState<ToastItem[]>([])
  const counter = useRef(0)

  const push = useCallback((message: string, type: 'ok' | 'err') => {
    const id = ++counter.current
    setItems(prev => [...prev, { id, message, type }])
    setTimeout(() => setItems(prev => prev.filter(t => t.id !== id)), 3000)
  }, [])

  useEffect(() => { _push = push; return () => { _push = null } }, [push])

  return (
    <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-[200] flex flex-col gap-2 pointer-events-none items-center">
      <AnimatePresence>
        {items.map(item => (
          <motion.div
            key={item.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ type: 'spring', stiffness: 400, damping: 30 }}
            className={
              item.type === 'ok'
                ? 'px-4 py-2.5 rounded-xl text-sm font-medium border bg-emerald-500/10 text-emerald-300 border-emerald-500/20 backdrop-blur-sm'
                : 'px-4 py-2.5 rounded-xl text-sm font-medium border bg-red-500/10 text-red-300 border-red-500/20 backdrop-blur-sm'
            }
          >
            {item.message}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}
```

- [ ] **Step 2: Create `frontend/src/components/Overlay.tsx`**

```tsx
import { motion, AnimatePresence } from 'framer-motion'
import { useLatency } from '@/hooks/useLatency'
import { useEffect } from 'react'

interface OverlayProps { visible: boolean; message: string }

export function Overlay({ visible, message }: OverlayProps) {
  const latency = useLatency()

  useEffect(() => {
    if (visible) latency.start()
    else latency.stop()
  }, [visible]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
          className="fixed inset-0 z-[100] flex flex-col items-center justify-center gap-3 bg-black/85 backdrop-blur-md"
        >
          <div className="w-10 h-10 rounded-full border-2 border-white/10 border-t-indigo-400 animate-spin" />
          <p className="text-sm text-white/60">{message}</p>
          <p className="text-3xl font-bold tabular-nums text-white tracking-tight">
            {latency.formatted}
          </p>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Toast.tsx frontend/src/components/Overlay.tsx
git commit -m "feat: add Toast and Overlay components"
```

---

## Task 9: AudioPlayer component

**Files:**
- Create: `frontend/src/components/AudioPlayer.tsx`

- [ ] **Step 1: Create `frontend/src/components/AudioPlayer.tsx`**

```tsx
import { useRef, useState, useEffect } from 'react'
import { motion } from 'framer-motion'

interface AudioPlayerProps { url: string }

export function AudioPlayer({ url }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const [playing, setPlaying] = useState(false)
  const [progress, setProgress] = useState(0)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)

  useEffect(() => {
    const a = audioRef.current
    if (!a) return
    a.src = url
    a.load()
    const play = () => a.play().catch(() => {})
    a.addEventListener('canplaythrough', play, { once: true })
    return () => a.removeEventListener('canplaythrough', play)
  }, [url])

  useEffect(() => {
    const a = audioRef.current
    if (!a) return
    const onTime = () => {
      setCurrentTime(a.currentTime)
      setDuration(a.duration || 0)
      setProgress(a.duration ? a.currentTime / a.duration : 0)
    }
    const onPlay = () => setPlaying(true)
    const onPause = () => setPlaying(false)
    const onEnded = () => { setPlaying(false); setProgress(0) }
    a.addEventListener('timeupdate', onTime)
    a.addEventListener('play', onPlay)
    a.addEventListener('pause', onPause)
    a.addEventListener('ended', onEnded)
    return () => {
      a.removeEventListener('timeupdate', onTime)
      a.removeEventListener('play', onPlay)
      a.removeEventListener('pause', onPause)
      a.removeEventListener('ended', onEnded)
    }
  }, [])

  const toggle = () => {
    const a = audioRef.current
    if (!a) return
    playing ? a.pause() : a.play()
  }

  const seek = (e: React.MouseEvent<HTMLDivElement>) => {
    const a = audioRef.current
    if (!a || !a.duration) return
    const rect = e.currentTarget.getBoundingClientRect()
    a.currentTime = ((e.clientX - rect.left) / rect.width) * a.duration
  }

  const fmt = (s: number) => `${Math.floor(s / 60)}:${Math.floor(s % 60).toString().padStart(2, '0')}`

  return (
    <div className="flex items-center gap-4 px-4 py-3 rounded-2xl bg-white/5 border border-white/10">
      <audio ref={audioRef} />
      <motion.button
        onClick={toggle}
        whileHover={{ scale: 1.08 }}
        whileTap={{ scale: 0.94 }}
        className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg flex-shrink-0"
      >
        {playing ? (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="white">
            <rect x="6" y="4" width="4" height="16" /><rect x="14" y="4" width="4" height="16" />
          </svg>
        ) : (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="white">
            <path d="M8 5v14l11-7z" />
          </svg>
        )}
      </motion.button>
      <div className="flex-1 min-w-0">
        <div
          className="h-1.5 bg-white/10 rounded-full cursor-pointer overflow-hidden mb-1.5"
          onClick={seek}
        >
          <motion.div
            className="h-full bg-gradient-to-r from-indigo-400 to-purple-500 rounded-full"
            style={{ width: `${progress * 100}%` }}
            transition={{ duration: 0.1 }}
          />
        </div>
        <p className="text-xs text-white/40 tabular-nums">{fmt(currentTime)} / {fmt(duration)}</p>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/AudioPlayer.tsx
git commit -m "feat: add AudioPlayer component"
```

---

## Task 10: PipelineStages component

**Files:**
- Create: `frontend/src/components/PipelineStages.tsx`

This component renders the 4 pipeline stages with live latency ticking. It receives `ProcessResponse` and `ApproveResponse` from the parent and manages stage rendering.

- [ ] **Step 1: Create `frontend/src/components/PipelineStages.tsx`**

```tsx
import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'
import type { ProcessResponse, ApproveResponse } from '@/lib/api'
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
        <span style={{ background: s.bg, color: s.color, border: `1px solid ${s.border}`,
          fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em',
          padding: '2px 7px', borderRadius: 4, marginRight: 3, verticalAlign: 'middle', position: 'relative', top: -1 }}>
          {cur}
        </span>
        {p}
      </span>
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
      {/* connector line */}
      <div className="absolute left-3.5 top-7 bottom-0 w-px bg-white/5 last:hidden" />

      {/* dot */}
      <div className={cn(
        'absolute left-0 top-1 w-7 h-7 rounded-full flex items-center justify-center text-xs border transition-all duration-300',
        status === 'done'    && 'bg-emerald-500/15 border-emerald-500/40 text-emerald-400',
        status === 'running' && 'bg-indigo-500/15 border-indigo-500/50 text-indigo-400 animate-pulse',
        status === 'pending' && 'bg-white/5 border-white/10 text-white/30',
      )}>
        {icon}
      </div>

      {/* header */}
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

      {/* content */}
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

  const MOOD_EMOJIS: Record<string, string> = { happy:'😊',excited:'🤩',laughing:'😂',sad:'😢',angry:'😠',shocked:'😱',scared:'😨',sarcastic:'😏',whispering:'🤫',neutral:'😐',auto:'🎭' }
  const MOODS = ['','happy','excited','laughing','sad','angry','shocked','scared','sarcastic','whispering','neutral']

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

            {/* Save speaker banner */}
            {processResult.save_voice_prompt && (
              <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3">
                <p className="text-xs font-semibold text-amber-300 mb-2">🎤 New voice — save this speaker?</p>
                <div className="flex gap-2">
                  <input value={speakerName} onChange={e => setSpeakerName(e.target.value)}
                    placeholder="Speaker's name"
                    className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white/80 placeholder-white/25 outline-none" />
                  <select value={speakerRel} onChange={e => setSpeakerRel(e.target.value)}
                    className="bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-sm text-white/80 outline-none">
                    {RELATIONSHIPS.map(r => <option key={r} value={r}>{r.replace('_',' ')}</option>)}
                  </select>
                </div>
                <button onClick={() => onSaveSpeaker(speakerName, speakerRel)}
                  className="mt-2 px-3 py-1.5 text-xs font-medium rounded-lg bg-white/10 hover:bg-white/15 text-white/70 transition-colors">
                  Save Voice Profile
                </button>
              </div>
            )}

            {/* Approve / Deny */}
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

            {/* Deny panel */}
            <AnimatePresence>
              {denyOpen && (
                <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
                  className="overflow-hidden border-t border-white/8 pt-3 space-y-2">
                  <div className="grid grid-cols-2 gap-2">
                    <select value={denyMood} onChange={e => setDenyMood(e.target.value)}
                      className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white/70 outline-none">
                      {MOODS.map(m => <option key={m} value={m}>{m ? MOOD_EMOJIS[m] + ' ' + m : 'Keep mood'}</option>)}
                    </select>
                    <select value={denyRel} onChange={e => setDenyRel(e.target.value)}
                      className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white/70 outline-none">
                      <option value="">Keep relationship</option>
                      {RELATIONSHIPS.map(r => <option key={r} value={r}>{r.replace('_',' ')}</option>)}
                    </select>
                  </div>
                  <input value={denyExtra} onChange={e => setDenyExtra(e.target.value)}
                    placeholder="Add clarification…"
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white/70 placeholder-white/25 outline-none" />
                  <button onClick={() => { onDeny({ mood_override: denyMood||undefined, relationship_override: denyRel||undefined, extra_text: denyExtra||undefined }); setDenyOpen(false) }}
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
        {approveResult && (
          <div className="space-y-3">
            <AudioPlayer url={approveResult.tts_audio_url} />
            <div className="text-xs font-mono text-white/30 bg-white/3 rounded-xl px-3 py-2 space-y-0.5">
              <p><span className="text-indigo-400">speaker</span>: {approveResult.tts_payload.speaker}</p>
              <p><span className="text-indigo-400">text</span>: {approveResult.tts_payload.text}</p>
            </div>
          </div>
        )}
      </StageRow>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/PipelineStages.tsx
git commit -m "feat: add PipelineStages with per-stage live latency timers"
```

---

## Task 11: Pipeline component (mic button)

**Files:**
- Create: `frontend/src/components/Pipeline.tsx`

- [ ] **Step 1: Create `frontend/src/components/Pipeline.tsx`**

```tsx
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'
import type { RecorderState } from '@/hooks/useRecorder'

interface PipelineProps {
  recorderState: RecorderState
  formattedTime: string
  onToggle: () => void
  onReset: () => void
  relationship: string
  onRelationshipChange: (v: string) => void
  showReset: boolean
}

const RELATIONSHIPS = ['friend','best_friend','parent','sibling','romantic','colleague','boss','stranger']

export function Pipeline({ recorderState, formattedTime, onToggle, onReset, relationship, onRelationshipChange, showReset }: PipelineProps) {
  const isRecording = recorderState === 'recording'
  const isReady = recorderState === 'ready'

  return (
    <div className="flex flex-col items-center gap-6">
      {/* Mic button */}
      <div className="relative flex items-center justify-center">
        {/* pulse ring */}
        <AnimatePresence>
          {isRecording && (
            <motion.div
              className="absolute w-28 h-28 rounded-full bg-red-500/20"
              initial={{ scale: 0.8, opacity: 0.8 }}
              animate={{ scale: 1.6, opacity: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 1.4, repeat: Infinity, ease: 'easeOut' }}
            />
          )}
        </AnimatePresence>

        <motion.button
          onClick={onToggle}
          whileHover={{ scale: 1.06 }}
          whileTap={{ scale: 0.94 }}
          className={cn(
            'relative w-24 h-24 rounded-full flex items-center justify-center shadow-2xl transition-all duration-300 z-10',
            isRecording
              ? 'bg-gradient-to-br from-red-500 to-red-700 shadow-red-500/30'
              : 'bg-gradient-to-br from-indigo-500 to-purple-600 shadow-indigo-500/30',
          )}
          aria-label={isRecording ? 'Stop recording' : 'Start recording'}
        >
          {isRecording ? (
            <svg width="28" height="28" viewBox="0 0 24 24" fill="white">
              <rect x="6" y="6" width="12" height="12" rx="2.5" />
            </svg>
          ) : (
            <svg width="28" height="28" viewBox="0 0 24 24" fill="white">
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3zm-1 3a1 1 0 0 1 2 0v7a1 1 0 0 1-2 0V5zm8 5v1a7 7 0 0 1-14 0v-1H3v1a9 9 0 0 0 8 8.94V22h-3v2h8v-2h-3v-2.06A9 9 0 0 0 21 11v-1h-2z"/>
            </svg>
          )}
        </motion.button>
      </div>

      {/* Status / timer */}
      <div className="text-center space-y-1">
        {isRecording && (
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-red-400 text-sm font-semibold tabular-nums">
            {formattedTime}
          </motion.p>
        )}
        <p className="text-sm text-white/40">
          {isRecording ? 'Recording — click to stop' : isReady ? 'Ready — select a mood →' : 'Click to record · Space'}
        </p>
      </div>

      {/* Relationship selector */}
      <div className="flex items-center gap-3">
        <label className="text-xs font-semibold uppercase tracking-widest text-white/30">Relationship</label>
        <select
          value={relationship}
          onChange={e => onRelationshipChange(e.target.value)}
          className="bg-white/5 border border-white/10 rounded-xl px-3 py-1.5 text-sm text-white/70 outline-none focus:border-indigo-500/50 transition-colors appearance-none cursor-pointer"
        >
          {RELATIONSHIPS.map(r => <option key={r} value={r}>{r.replace('_', ' ')}</option>)}
        </select>
      </div>

      {/* Reset */}
      <AnimatePresence>
        {showReset && (
          <motion.button
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            onClick={onReset}
            className="text-xs text-white/25 hover:text-white/50 transition-colors"
          >
            ↺ Record another
          </motion.button>
        )}
      </AnimatePresence>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Pipeline.tsx
git commit -m "feat: add Pipeline mic button component"
```

---

## Task 12: Profile component

**Files:**
- Create: `frontend/src/components/Profile.tsx`

- [ ] **Step 1: Create `frontend/src/components/Profile.tsx`**

```tsx
import { useState } from 'react'
import { cn } from '@/lib/utils'
import type { Profile } from '@/lib/api'

const DIMS = [
  { dim: 'energy',    label: 'Energy',   desc: 'How you recharge',    a: 'Chill',      b: 'Chaotic',      av: 'chill',    bv: 'chaotic' },
  { dim: 'filter',    label: 'Filter',   desc: 'How direct you are',  a: 'Clean',      b: 'Unfiltered',   av: 'clean',    bv: 'unfiltered' },
  { dim: 'style',     label: 'Style',    desc: 'How you communicate', a: 'Punchy',     b: 'Dramatic',     av: 'punchy',   bv: 'dramatic' },
  { dim: 'tone',      label: 'Tone',     desc: 'Your emotional lean', a: 'Sincere',    b: 'Sarcastic',    av: 'sincere',  bv: 'sarcastic' },
  { dim: 'lang_lean', label: 'Language', desc: 'Your Hinglish mix',   a: 'Hindi-lean', b: 'English-lean', av: 'hindi',    bv: 'english' },
]

interface ProfileProps {
  profile: Profile
  onSave: (name: string, personality: Record<string,string>, customVibe: string) => void
  onCancel: () => void
  onDeleteSpeakers: () => void
}

export function ProfilePanel({ profile, onSave, onCancel, onDeleteSpeakers }: ProfileProps) {
  const [name, setName] = useState(profile.name)
  const [personality, setPersonality] = useState<Record<string,string>>(profile.personality ?? {})
  const [vibe, setVibe] = useState(profile.custom_vibe ?? '')

  const setDim = (dim: string, val: string) => setPersonality(p => ({ ...p, [dim]: val }))

  return (
    <div className="space-y-4">
      {/* Name */}
      <div>
        <label className="block text-xs font-semibold uppercase tracking-widest text-white/30 mb-2">Name</label>
        <input value={name} onChange={e => setName(e.target.value)} maxLength={64}
          className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white/80 placeholder-white/25 outline-none focus:border-indigo-500/40 transition-colors" />
      </div>

      {/* Dims */}
      <div className="space-y-2">
        {DIMS.map(d => (
          <div key={d.dim} className="flex items-center justify-between rounded-xl bg-white/3 border border-white/8 px-4 py-3">
            <div>
              <p className="text-sm font-medium text-white/70">{d.label}</p>
              <p className="text-xs text-white/30">{d.desc}</p>
            </div>
            <div className="flex gap-1.5">
              {[{ label: d.a, val: d.av }, { label: d.b, val: d.bv }].map(opt => (
                <button key={opt.val} onClick={() => setDim(d.dim, opt.val)}
                  className={cn('px-3 py-1.5 rounded-lg text-xs font-medium border transition-all',
                    personality[d.dim] === opt.val
                      ? 'bg-indigo-500/15 border-indigo-500/40 text-indigo-300'
                      : 'bg-white/3 border-white/10 text-white/40 hover:border-white/20 hover:text-white/60'
                  )}>
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Vibe */}
      <div>
        <label className="block text-xs font-semibold uppercase tracking-widest text-white/30 mb-2">Custom Vibe <span className="normal-case font-normal">(optional)</span></label>
        <textarea value={vibe} onChange={e => setVibe(e.target.value)} maxLength={400} rows={2}
          placeholder="e.g. like a chaotic Delhi college kid who's always running late…"
          className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white/80 placeholder-white/25 outline-none resize-none focus:border-indigo-500/40 transition-colors" />
      </div>

      {/* Actions */}
      <div className="flex gap-2 pt-1">
        <button onClick={onCancel} className="flex-1 py-2.5 rounded-xl text-sm font-medium bg-white/5 hover:bg-white/8 text-white/50 border border-white/10 transition-colors">
          Cancel
        </button>
        <button onClick={() => onSave(name, personality, vibe)}
          className="flex-[2] py-2.5 rounded-xl text-sm font-semibold bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white transition-all">
          Save Changes ✓
        </button>
      </div>

      {/* Danger */}
      <div className="pt-2 border-t border-white/8">
        <p className="text-xs font-semibold uppercase tracking-widest text-red-500/50 mb-2">Danger Zone</p>
        <button onClick={onDeleteSpeakers}
          className="px-4 py-2 rounded-xl text-xs font-medium bg-red-500/8 hover:bg-red-500/14 text-red-400 border border-red-500/20 transition-colors">
          Delete All Enrolled Voices
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Profile.tsx
git commit -m "feat: add Profile component"
```

---

## Task 13: Onboarding page

**Files:**
- Create: `frontend/src/pages/Onboarding.tsx`

- [ ] **Step 1: Create `frontend/src/pages/Onboarding.tsx`**

```tsx
import { useState } from 'react'
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
    if (!name.trim()) { toast('Enter your name first', 'err'); return }
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
      toast(`Welcome, ${saved.name}!`, 'ok')
      onComplete(saved)
    } catch {
      toast('Failed to save profile', 'err')
    } finally { setSaving(false) }
  }

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
```

- [ ] **Step 2: Add keyboard shortcuts for quiz (Y/N/Backspace)**

In `frontend/src/pages/Onboarding.tsx`, add inside the component before the return:

```tsx
// add this import at the top of the file
import { useState, useEffect } from 'react'

// add this inside the component (after state declarations, before return):
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
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Onboarding.tsx
git commit -m "feat: add Onboarding page with ContainerScroll 3D entry and quiz flow"
```

---

## Task 14: Main page

**Files:**
- Create: `frontend/src/pages/Main.tsx`

- [ ] **Step 1: Create `frontend/src/pages/Main.tsx`**

```tsx
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { HeroHighlight } from '@/components/ui/hero-highlight'
import { VerticalMoodDock } from '@/components/ui/vertical-mood-dock'
import { Pipeline } from '@/components/Pipeline'
import { PipelineStages } from '@/components/PipelineStages'
import { ProfilePanel } from '@/components/Profile'
import { useRecorder } from '@/hooks/useRecorder'
import { useLatency } from '@/hooks/useLatency'
import { api, type Profile, type ProcessResponse, type ApproveResponse } from '@/lib/api'
import { toast } from '@/components/Toast'
import { Overlay } from '@/components/Overlay'
import { cn } from '@/lib/utils'

interface MainProps {
  profiles: Profile[]
  activeProfile: Profile
  onProfileUpdate: (p: Profile) => void
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
    if (!recorder.blob) { toast('Record something first', 'err'); return }
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
      toast('Processing failed — is the server running?', 'err')
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
      toast('TTS failed — check server logs', 'err')
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
      toast('Regenerated!', 'ok')
    } catch {
      processLatency.stop()
      toast('Regeneration failed', 'err')
    } finally {
      setIsProcessing(false)
      setOverlayMsg('')
    }
  }

  const handleSaveSpeaker = async (name: string, rel: string) => {
    if (!sessionId) return
    try {
      await api.saveSpeaker(sessionId, name, rel)
      toast(`Voice saved for ${name}!`, 'ok')
    } catch {
      toast('Failed to save voice profile', 'err')
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

  const handleSaveProfile = async (name: string, personality: Record<string,string>, customVibe: string) => {
    try {
      const saved = await api.saveProfile({ profile_id: activeProfile.profile_id, name, personality, custom_vibe: customVibe })
      onProfileUpdate(saved)
      setTab('pipeline')
      toast('Profile updated!', 'ok')
    } catch {
      toast('Failed to save profile', 'err')
    }
  }

  const handleDeleteSpeakers = async () => {
    if (!confirm('Delete ALL enrolled voice profiles?')) return
    try {
      const r = await api.deleteAllSpeakers()
      toast(`Cleared ${r.deleted} speaker profile(s)`, 'ok')
    } catch {
      toast('Failed to delete speakers', 'err')
    }
  }

  return (
    <HeroHighlight containerClassName="min-h-screen">
      <Overlay visible={isProcessing || isApproving} message={overlayMsg} />

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

        {/* Profile chip */}
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
              <ProfilePanel
                profile={activeProfile}
                onSave={handleSaveProfile}
                onCancel={() => setTab('pipeline')}
                onDeleteSpeakers={handleDeleteSpeakers}
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
```

- [ ] **Step 2: Add Space bar shortcut for recording**

In `frontend/src/pages/Main.tsx`, add inside the component:

```tsx
// add this import at top: import { useState, useEffect } from 'react'

// add inside Main component, before return:
useEffect(() => {
  const handler = (e: KeyboardEvent) => {
    if (e.code !== 'Space') return
    const tag = (e.target as HTMLElement).tagName
    if (['INPUT','TEXTAREA','SELECT'].includes(tag)) return
    if (tab !== 'pipeline') return
    e.preventDefault()
    if (recorder.state === 'recording') recorder.stop()
    else if (recorder.state === 'idle') recorder.start()
  }
  window.addEventListener('keydown', handler)
  return () => window.removeEventListener('keydown', handler)
}, [tab, recorder.state]) // eslint-disable-line react-hooks/exhaustive-deps
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Main.tsx
git commit -m "feat: add Main page with HeroHighlight shell, Pipeline, PipelineStages, VerticalMoodDock"
```

---

## Task 15: App.tsx root

**Files:**
- Create: `frontend/src/App.tsx`

- [ ] **Step 1: Create `frontend/src/App.tsx`**

```tsx
import { useState, useEffect } from 'react'
import { Onboarding } from '@/pages/Onboarding'
import { Main } from '@/pages/Main'
import { ToastProvider } from '@/components/Toast'
import { api, type Profile } from '@/lib/api'

type AppState = 'loading' | 'onboarding' | 'main'

export default function App() {
  const [appState, setAppState] = useState<AppState>('loading')
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [activeProfile, setActiveProfile] = useState<Profile | null>(null)

  useEffect(() => {
    api.getProfiles()
      .then(({ profiles: ps, active_id }) => {
        if (ps.length === 0) {
          setAppState('onboarding')
        } else {
          setProfiles(ps)
          setActiveProfile(ps.find(p => p.profile_id === active_id) ?? ps[0])
          setAppState('main')
        }
      })
      .catch(() => setAppState('onboarding'))
  }, [])

  const handleOnboardingComplete = (profile: Profile) => {
    setProfiles([profile])
    setActiveProfile(profile)
    setAppState('main')
  }

  const handleProfileUpdate = (profile: Profile) => {
    setProfiles(prev => {
      const idx = prev.findIndex(p => p.profile_id === profile.profile_id)
      if (idx >= 0) { const next = [...prev]; next[idx] = profile; return next }
      return [...prev, profile]
    })
    setActiveProfile(profile)
  }

  return (
    <>
      <ToastProvider />
      {appState === 'loading' && (
        <div className="min-h-screen bg-black flex items-center justify-center">
          <div className="w-8 h-8 rounded-full border-2 border-white/10 border-t-indigo-400 animate-spin" />
        </div>
      )}
      {appState === 'onboarding' && <Onboarding onComplete={handleOnboardingComplete} />}
      {appState === 'main' && activeProfile && (
        <Main profiles={profiles} activeProfile={activeProfile} onProfileUpdate={handleProfileUpdate} />
      )}
    </>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: add App root with profile-gated routing"
```

---

## Task 16: Update main.py to serve built frontend

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Read current main.py StaticFiles mount**

Check how `main.py` currently mounts the frontend. Look for `StaticFiles` and the `/ui` route.

- [ ] **Step 2: Update the StaticFiles mount**

Find the section in `main.py` that mounts static files or returns `frontend.html`. Replace it so that:
- The built `frontend/dist/` is mounted at `/ui`
- Any sub-path under `/ui` that isn't a file returns `frontend/dist/index.html` (SPA fallback)

The mount should look like this (add after all API routers are included):

```python
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")

if os.path.isdir(FRONTEND_DIST):
    app.mount("/ui", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
```

If `main.py` already has a `/ui` route that returns `frontend.html`, replace that route with the StaticFiles mount above. The `html=True` flag on `StaticFiles` automatically serves `index.html` for any path not found — this is the SPA fallback.

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: mount frontend/dist at /ui via StaticFiles"
```

---

## Task 17: Build and verify

**Files:** none new

- [ ] **Step 1: Build the frontend**

```bash
cd frontend && npm run build
```

Expected: `frontend/dist/` created with `index.html` and `assets/`. No TypeScript errors.

If you see TS errors about unused variables, fix them (the `noUnusedLocals`/`noUnusedParameters` flags are strict). Common fix: prefix unused params with `_`.

- [ ] **Step 2: Start the API server**

```bash
cd .. && uvicorn main:app --reload --port 8000
```

- [ ] **Step 3: Open the app**

Open `http://localhost:8000/ui` in a browser.

Expected:
- If no profile exists: Onboarding screen with the HeroHighlight dot background, ContainerScroll 3D card entry, name input inside the card
- If profile exists: Main screen with dark HeroHighlight background, mic button centered, VerticalMoodDock on the right side

- [ ] **Step 4: Test the onboarding flow**

1. Enter a name, click Start Quiz
2. Answer all 10 questions (use Y/N keyboard shortcuts)
3. See the result/vibe screen
4. Click Save Profile & Continue
5. Confirm Main screen loads

- [ ] **Step 5: Test the pipeline flow**

1. Press Space or click mic to record — confirm pulse ring appears and timer ticks
2. Press Space again to stop — button should say "Ready — select a mood →"
3. Click a mood in the VerticalMoodDock (right side) — panel slides left, shows input
4. Optionally type extra context, click "Generate Response"
5. Confirm Overlay shows live elapsed timer
6. Confirm pipeline stages appear: STT transcript, Speaker badge, LLM expressive text with color emotion tags
7. Click "Sounds good" → confirm TTS overlay runs, audio player appears and auto-plays
8. Confirm per-stage latency times and "Total Xs" banner appear

- [ ] **Step 6: Commit any fixups**

```bash
git add -A
git commit -m "fix: post-build verification fixes"
```
