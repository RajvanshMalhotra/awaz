import { useCallback, useEffect, useRef, useState } from 'react'

export interface VoiceWSState {
  transcript: string | null
  expressiveText: string | null
  detectedMood: string | null
  reasoning: string | null
  isProcessing: boolean
  isPlayingAudio: boolean
  error: string | null
}

const INITIAL_STATE: VoiceWSState = {
  transcript: null,
  expressiveText: null,
  detectedMood: null,
  reasoning: null,
  isProcessing: false,
  isPlayingAudio: false,
  error: null,
}

export function useVoiceWS() {
  const [state, setState] = useState<VoiceWSState>(INITIAL_STATE)
  const audioCtxRef = useRef<AudioContext | null>(null)
  const nextStartTimeRef = useRef(0)
  const audioEndedRef = useRef(false)
  const wsRef = useRef<WebSocket | null>(null)

  const submit = useCallback((blob: Blob, mood: string) => {
    // Close any previous connection
    wsRef.current?.close()
    if (audioCtxRef.current) {
      audioCtxRef.current.close()
      audioCtxRef.current = null
    }

    setState({ ...INITIAL_STATE, isProcessing: true })
    nextStartTimeRef.current = 0
    audioEndedRef.current = false

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const moodParam = encodeURIComponent(mood)
    const ws = new WebSocket(
      `${protocol}//${window.location.host}/ws/voice?mood_override=${moodParam}`
    )
    wsRef.current = ws
    ws.binaryType = 'arraybuffer'

    ws.onopen = () => {
      ws.send(blob)
    }

    ws.onmessage = (event) => {
      if (typeof event.data === 'string') {
        let msg: { type: string; [key: string]: string }
        try {
          msg = JSON.parse(event.data)
        } catch {
          return
        }

        if (msg.type === 'transcript') {
          setState(s => ({ ...s, transcript: msg.text }))

        } else if (msg.type === 'llm') {
          setState(s => ({
            ...s,
            expressiveText: msg.expressive_text,
            detectedMood: msg.detected_mood,
            reasoning: msg.reasoning,
          }))

        } else if (msg.type === 'audio_start') {
          const ctx = new AudioContext({ sampleRate: 24000 })
          ctx.resume()
          audioCtxRef.current = ctx
          nextStartTimeRef.current = ctx.currentTime + 0.1
          audioEndedRef.current = false
          setState(s => ({ ...s, isPlayingAudio: true }))

        } else if (msg.type === 'audio_end') {
          audioEndedRef.current = true
          setState(s => ({ ...s, isProcessing: false }))
          ws.close(1000)

        } else if (msg.type === 'error') {
          setState(s => ({ ...s, isProcessing: false, isPlayingAudio: false, error: msg.message }))
          ws.close()
        }

      } else {
        // Binary: Int16 PCM chunk at 24kHz mono
        const ctx = audioCtxRef.current
        if (!ctx) return

        const int16 = new Int16Array(event.data as ArrayBuffer)
        if (int16.length === 0) return

        const float32 = new Float32Array(int16.length)
        for (let i = 0; i < int16.length; i++) {
          float32[i] = int16[i] / 32768.0
        }

        const buffer = ctx.createBuffer(1, float32.length, 24000)
        buffer.copyToChannel(float32, 0)

        const source = ctx.createBufferSource()
        source.buffer = buffer
        source.connect(ctx.destination)

        const startTime = Math.max(nextStartTimeRef.current, ctx.currentTime)
        source.start(startTime)
        nextStartTimeRef.current = startTime + buffer.duration
        source.onended = () => {
          if (audioEndedRef.current) {
            setState(s => ({ ...s, isPlayingAudio: false }))
          }
        }
      }
    }

    ws.onerror = () => {
      setState(s => ({ ...s, isProcessing: false, isPlayingAudio: false, error: 'Connection failed' }))
    }

    ws.onclose = (event) => {
      wsRef.current = null
      // Abnormal close codes (not 1000 = normal, not 1001 = going away)
      if (event.code !== 1000 && event.code !== 1001) {
        setState(s => ({ ...s, isProcessing: false, isPlayingAudio: false }))
      }
    }
  }, [])

  const reset = useCallback(() => {
    wsRef.current?.close()
    wsRef.current = null
    if (audioCtxRef.current) {
      audioCtxRef.current.close()
      audioCtxRef.current = null
    }
    setState(INITIAL_STATE)
  }, [])

  useEffect(() => {
    return () => {
      wsRef.current?.close()
      audioCtxRef.current?.close()
    }
  }, [])

  return { state, submit, reset }
}
