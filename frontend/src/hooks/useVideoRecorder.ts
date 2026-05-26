import { useState, useRef, useCallback, useEffect } from 'react'

export type VideoRecorderState = 'idle' | 'recording' | 'ready'

export function useVideoRecorder() {
  const [state, setState] = useState<VideoRecorderState>('idle')
  const [blob, setBlob] = useState<Blob | null>(null)
  const [seconds, setSeconds] = useState(0)
  const [stream, setStream] = useState<MediaStream | null>(null)

  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const start = useCallback(async (videoEl?: HTMLVideoElement | null) => {
    let mediaStream: MediaStream
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true })
    } catch {
      return false
    }

    chunksRef.current = []
    setBlob(null)
    setSeconds(0)
    setStream(mediaStream)

    if (videoEl) {
      videoEl.srcObject = mediaStream
      videoEl.play().catch(() => {})
    }

    const mime = ['video/webm;codecs=vp9,opus', 'video/webm', 'video/mp4'].find(m =>
      MediaRecorder.isTypeSupported(m),
    ) ?? ''

    const recorder = new MediaRecorder(mediaStream, mime ? { mimeType: mime } : {})
    recorderRef.current = recorder

    recorder.ondataavailable = e => {
      if (e.data.size > 0) chunksRef.current.push(e.data)
    }
    recorder.onstop = () => {
      const b = new Blob(chunksRef.current, { type: recorder.mimeType || 'video/webm' })
      setBlob(b)
      setState('ready')
      mediaStream.getTracks().forEach(t => t.stop())
      setStream(null)
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
    stream?.getTracks().forEach(t => t.stop())
    setStream(null)
    setBlob(null)
    setSeconds(0)
    setState('idle')
  }, [stop, stream])

  useEffect(() => {
    return () => {
      if (recorderRef.current && recorderRef.current.state !== 'inactive') {
        recorderRef.current.stop()
      }
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [])

  const formatSeconds = (s: number) =>
    `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`

  return { state, blob, seconds, formattedTime: formatSeconds(seconds), stream, start, stop, reset }
}
