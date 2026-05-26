import { useRef, useState, useCallback, useEffect } from 'react'
import { HandLandmarker, FilesetResolver } from '@mediapipe/tasks-vision'

export type SignRecognizerState = 'idle' | 'initializing' | 'ready' | 'recording' | 'done'

const HAND_CONNECTIONS: [number, number][] = [
  [0,1],[1,2],[2,3],[3,4],
  [0,5],[5,6],[6,7],[7,8],
  [0,9],[9,10],[10,11],[11,12],
  [0,13],[13,14],[14,15],[15,16],
  [0,17],[17,18],[18,19],[19,20],
  [5,9],[9,13],[13,17],
]

export type LandmarkFrame = [number, number, number][]

export function useSignRecognizer() {
  const [state, setState] = useState<SignRecognizerState>('idle')
  const landmarkerRef = useRef<HandLandmarker | null>(null)
  const rafIdRef = useRef<number | null>(null)
  const lastSnapRef = useRef<number>(0)
  const landmarkBufferRef = useRef<LandmarkFrame[]>([])
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
    landmarker: HandLandmarker,
    video: HTMLVideoElement,
    canvas: HTMLCanvasElement
  ) => {
    const loop = () => {
      if (video.readyState >= 2) {
        const now = performance.now()
        const results = landmarker.detectForVideo(video, now)
        const ctx = canvas.getContext('2d')

        if (results.landmarks.length === 0) {
          ctx?.clearRect(0, 0, canvas.width, canvas.height)
        } else {
          drawSkeleton(canvas, results.landmarks[0])
          // Snap at ~15fps during recording
          if (isRecordingRef.current && now - lastSnapRef.current > 66) {
            lastSnapRef.current = now
            const frame: LandmarkFrame = results.landmarks[0].map(
              lm => [lm.x, lm.y, lm.z] as [number, number, number]
            )
            landmarkBufferRef.current.push(frame)
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
      const landmarker = await HandLandmarker.createFromOptions(vision, {
        baseOptions: {
          modelAssetPath:
            'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',
          delegate: 'GPU',
        },
        runningMode: 'VIDEO',
        numHands: 1,
      })
      if (!cancelled) {
        landmarkerRef.current = landmarker
        setState('ready')
      }
    }
    init().catch(console.error)
    return () => {
      cancelled = true
      if (rafIdRef.current) cancelAnimationFrame(rafIdRef.current)
      landmarkerRef.current?.close()
    }
  }, [])

  const start = useCallback(async (
    videoEl: HTMLVideoElement,
    canvasEl: HTMLCanvasElement
  ) => {
    if (!landmarkerRef.current) return
    landmarkBufferRef.current = []
    isRecordingRef.current = true
    lastSnapRef.current = 0

    const stream = await navigator.mediaDevices.getUserMedia({ video: true })
    streamRef.current = stream
    videoEl.srcObject = stream
    await videoEl.play()

    setState('recording')
    detect(landmarkerRef.current, videoEl, canvasEl)
  }, [detect])

  const stop = useCallback((): LandmarkFrame[] => {
    isRecordingRef.current = false
    if (rafIdRef.current) {
      cancelAnimationFrame(rafIdRef.current)
      rafIdRef.current = null
    }
    streamRef.current?.getTracks().forEach(t => t.stop())
    const captured = [...landmarkBufferRef.current]
    setState('done')
    return captured
  }, [])

  const reset = useCallback(() => {
    landmarkBufferRef.current = []
    setState('ready')
  }, [])

  return { state, start, stop, reset }
}
