import { useRef, useState, useCallback, useEffect } from 'react'
import { GestureRecognizer, FilesetResolver } from '@mediapipe/tasks-vision'

export type SignRecognizerState = 'idle' | 'initializing' | 'ready' | 'recording' | 'done'

// Google's trained gesture model — confirmed URL from MediaPipe models CDN
const MODEL_URL =
  'https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task'

const HAND_CONNECTIONS: [number, number][] = [
  [0,1],[1,2],[2,3],[3,4],
  [0,5],[5,6],[6,7],[7,8],
  [0,9],[9,10],[10,11],[11,12],
  [0,13],[13,14],[14,15],[15,16],
  [0,17],[17,18],[18,19],[19,20],
  [5,9],[9,13],[13,17],
]

// Map MediaPipe category names to display text
const GESTURE_LABEL: Record<string, string> = {
  Closed_Fist: 'fist',
  Open_Palm: 'open hand',
  Pointing_Up: 'pointing up',
  Thumb_Down: 'thumbs down',
  Thumb_Up: 'thumbs up',
  Victory: 'peace',
  ILoveYou: 'I love you',
}

function majorityVote(gestures: string[]): string {
  if (gestures.length === 0) return ''
  const counts: Record<string, number> = {}
  for (const g of gestures) counts[g] = (counts[g] ?? 0) + 1
  const top = Object.entries(counts).sort((a, b) => b[1] - a[1])[0][0]
  return GESTURE_LABEL[top] ?? top.toLowerCase().replace('_', ' ')
}

export function useSignRecognizer() {
  const [state, setState] = useState<SignRecognizerState>('idle')
  const [liveGesture, setLiveGesture] = useState<string>('')

  const recognizerRef = useRef<GestureRecognizer | null>(null)
  const rafIdRef = useRef<number | null>(null)
  const lastSnapRef = useRef<number>(0)
  const gestureBufferRef = useRef<string[]>([])
  const isRecordingRef = useRef(false)
  const streamRef = useRef<MediaStream | null>(null)

  const drawSkeleton = useCallback((
    canvas: HTMLCanvasElement,
    landmarks: { x: number; y: number; z: number }[]
  ) => {
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    const W = canvas.width, H = canvas.height

    ctx.strokeStyle = 'rgba(99,102,241,0.85)'
    ctx.lineWidth = 2
    for (const [a, b] of HAND_CONNECTIONS) {
      ctx.beginPath()
      ctx.moveTo(landmarks[a].x * W, landmarks[a].y * H)
      ctx.lineTo(landmarks[b].x * W, landmarks[b].y * H)
      ctx.stroke()
    }
    for (const lm of landmarks) {
      ctx.beginPath()
      ctx.arc(lm.x * W, lm.y * H, 3.5, 0, 2 * Math.PI)
      ctx.fillStyle = 'rgba(255,255,255,0.9)'
      ctx.fill()
    }
  }, [])

  const detect = useCallback((
    recognizer: GestureRecognizer,
    video: HTMLVideoElement,
    canvas: HTMLCanvasElement
  ) => {
    const loop = () => {
      if (video.readyState >= 2) {
        const now = performance.now()
        const results = recognizer.recognizeForVideo(video, now)
        const ctx = canvas.getContext('2d')

        if (results.landmarks.length === 0) {
          ctx?.clearRect(0, 0, canvas.width, canvas.height)
          setLiveGesture('')
        } else {
          drawSkeleton(canvas, results.landmarks[0])

          const topGesture = results.gestures[0]?.[0]
          if (topGesture && topGesture.categoryName !== 'None' && topGesture.score > 0.5) {
            const label = GESTURE_LABEL[topGesture.categoryName] ?? topGesture.categoryName
            setLiveGesture(label)

            // Collect gesture samples at ~5fps during recording
            if (isRecordingRef.current && now - lastSnapRef.current > 200) {
              lastSnapRef.current = now
              gestureBufferRef.current.push(topGesture.categoryName)
            }
          } else {
            setLiveGesture('')
          }
        }
      }
      rafIdRef.current = requestAnimationFrame(loop)
    }
    rafIdRef.current = requestAnimationFrame(loop)
  }, [drawSkeleton])

  useEffect(() => {
    let cancelled = false
    const init = async () => {
      setState('initializing')
      const vision = await FilesetResolver.forVisionTasks(
        'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.15/wasm'
      )
      const recognizer = await GestureRecognizer.createFromOptions(vision, {
        baseOptions: { modelAssetPath: MODEL_URL, delegate: 'GPU' },
        runningMode: 'VIDEO',
        numHands: 1,
      })
      if (!cancelled) {
        recognizerRef.current = recognizer
        setState('ready')
      }
    }
    init().catch(console.error)
    return () => {
      cancelled = true
      if (rafIdRef.current) cancelAnimationFrame(rafIdRef.current)
      recognizerRef.current?.close()
    }
  }, [])

  const start = useCallback(async (
    videoEl: HTMLVideoElement,
    canvasEl: HTMLCanvasElement
  ) => {
    if (!recognizerRef.current) return
    gestureBufferRef.current = []
    isRecordingRef.current = true
    lastSnapRef.current = 0

    const stream = await navigator.mediaDevices.getUserMedia({ video: true })
    streamRef.current = stream
    videoEl.srcObject = stream
    await videoEl.play()

    setState('recording')
    detect(recognizerRef.current, videoEl, canvasEl)
  }, [detect])

  // Returns the majority-voted gesture as display text
  const stop = useCallback((): string => {
    isRecordingRef.current = false
    if (rafIdRef.current) {
      cancelAnimationFrame(rafIdRef.current)
      rafIdRef.current = null
    }
    streamRef.current?.getTracks().forEach(t => t.stop())
    const result = majorityVote(gestureBufferRef.current)
    setLiveGesture('')
    setState('done')
    return result
  }, [])

  const reset = useCallback(() => {
    gestureBufferRef.current = []
    setLiveGesture('')
    setState('ready')
  }, [])

  return { state, liveGesture, start, stop, reset }
}
