# Awaaz Frontend Redesign

## Overview

Replace the monolithic `frontend.html` with a proper Vite + React + TypeScript + Tailwind frontend, served via FastAPI StaticFiles. Three Aceternity UI components are recontextualized to fit the Awaaz voice pipeline product.

## Stack

- Vite 5, React 18, TypeScript, Tailwind CSS v3
- framer-motion (all three components depend on it)
- shadcn/ui `cn` utility (`clsx` + `tailwind-merge`)
- Served from `frontend/dist/` via FastAPI `StaticFiles` mount at `/ui`

## Components & Recontextualization

### 1. HeroHighlight (`components/ui/hero-highlight.tsx`)
**Original:** Hero section with interactive dot-grid background and mouse-reactive radial glow.  
**Awaaz use:** Full-screen app shell. The dot grid covers the entire viewport; mouse movement makes the whole app feel alive. Both the onboarding and main pipeline screens sit inside `<HeroHighlight>`.

### 2. ContainerScroll (`components/ui/container-scroll-animation.tsx`)
**Original:** Scroll-driven 3D card that tilts into view as the user scrolls.  
**Awaaz use:** Onboarding landing section. The title "Meet Your Voice" sits above; the quiz card is the 3D-tilted child that rotates into place as the user scrolls down to start.

### 3. MessageDock (`components/ui/message-dock.tsx`)
**Original:** Horizontal floating dock with emoji characters; expands to reveal a text input.  
**Awaaz use:** Vertical mood selector on the right side of the pipeline screen. Characters = moods:
- ✨ Auto (sparkle — auto-detect)
- 😊 Happy
- 🤩 Excited  
- 😏 Sarcastic
- 😢 Sad
- 😠 Angry

The dock is rotated/restructured to stack vertically (`flex-col`), fixed to `right-6 top-1/2 -translate-y-1/2`. When a mood is selected, it expands **leftward**, revealing a text input for extra context and a send button that triggers audio processing.

## App Structure

```
frontend/
  src/
    App.tsx                          # Route: onboarding vs main
    main.tsx
    index.css                        # Tailwind directives
    lib/utils.ts                     # cn() helper
    lib/api.ts                       # fetch wrappers for /pipeline/* and /onboarding/*
    components/
      ui/
        hero-highlight.tsx
        container-scroll-animation.tsx
        message-dock.tsx
      Pipeline.tsx                   # Mic button + Generate button
      PipelineStages.tsx             # STT / Speaker / LLM / TTS result cards
      AudioPlayer.tsx                # Custom player for TTS output
      Profile.tsx                    # Edit personality dims
    pages/
      Onboarding.tsx                 # Name → quiz → result, uses ContainerScroll
      Main.tsx                       # HeroHighlight shell + Pipeline + MessageDock
```

## Data Flow

1. `App.tsx` calls `GET /onboarding/profiles` on mount → if profiles exist, show `Main`, else show `Onboarding`
2. `Onboarding.tsx` runs the 10-question quiz, `POST /onboarding` to save → navigate to `Main`
3. `Main.tsx` → mic recording → mood selected via MessageDock → `POST /pipeline/process` → `PipelineStages` renders
4. Approve → `POST /pipeline/approve` → `AudioPlayer` plays TTS audio
5. Deny → `POST /pipeline/deny` → re-renders LLM stage result
6. Save speaker → `POST /pipeline/save-speaker`

## Serving

`main.py` mounts `frontend/dist` at `/ui` via `StaticFiles`. The Vite build writes to `frontend/dist/`. SPA routing handled by serving `index.html` for unknown paths.

## Personality Dimensions (unchanged from current)

energy, filter, style, tone, lang_lean — each binary. Quiz is 10 yes/no questions, majority vote per dimension.

## Latency

**Live latency display:** A persistent counter visible during any active pipeline stage — ticks in real-time (10ms resolution) and freezes on completion showing the final elapsed time per stage. Total end-to-end time shown prominently after TTS completes.

**Minimizing perceived latency:**
- Audio blob is prepared immediately on recording stop (no re-encoding)
- `POST /pipeline/process` fires the instant the user hits send on the dock — no extra UI transitions blocking it
- Stage results render incrementally as they arrive (STT + Speaker done → show, then LLM → show, then TTS → show)
- No full-page re-renders between stages — only the relevant stage card updates
- Framer-motion animations use `spring` physics with short durations (stiffness 400+, no artificial delays)
- Audio player auto-plays TTS output immediately on URL receipt

## Out of Scope

- No SSR, no Next.js
- No auth
- Multi-account switcher kept (same as current)
