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

  const formatSeconds = (s: number) =>
    `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`

  return { state, blob, seconds, formattedTime: formatSeconds(seconds), start, stop, reset, toggle }
}
