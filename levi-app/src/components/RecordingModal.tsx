import { useState, useEffect, useRef } from 'react'
import { X, Pause, Play } from 'lucide-react'
import styles from './RecordingModal.module.css'

interface RecordingModalProps {
  isOpen: boolean
  onClose: () => void
  onStop: (audioBlob: Blob, duration: number) => void
}

export default function RecordingModal({ isOpen, onClose, onStop }: RecordingModalProps) {
  const [isPaused, setIsPaused] = useState(false)
  const [elapsedTime, setElapsedTime] = useState(0)
  const [waveformBars, setWaveformBars] = useState<number[]>(Array(50).fill(2))
  const [isRecording, setIsRecording] = useState(false)
  
  const timerRef = useRef<NodeJS.Timeout | null>(null)
  const animationRef = useRef<NodeJS.Timeout | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const elapsedTimeRef = useRef(0)

  const maxDuration = 120 // 2 minutes in seconds

  // Start recording when modal opens
  useEffect(() => {
    if (isOpen && !isRecording) {
      startRecording()
    }
    
    return () => {
      if (!isOpen) {
        cleanup()
      }
    }
  }, [isOpen])

  // Timer and waveform animation
  useEffect(() => {
    if (isOpen && isRecording && !isPaused) {
      // Start timer
      timerRef.current = setInterval(() => {
        setElapsedTime(prev => {
          const newTime = prev + 1
          elapsedTimeRef.current = newTime
          if (newTime >= maxDuration) {
            handleStop()
            return prev
          }
          return newTime
        })
      }, 1000)

      // Animate waveform based on audio levels
      if (analyserRef.current) {
        animationRef.current = setInterval(() => {
          if (analyserRef.current) {
            const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount)
            analyserRef.current.getByteFrequencyData(dataArray)
            
            // Create waveform from frequency data
            const bars = []
            const step = Math.floor(dataArray.length / 50)
            for (let i = 0; i < 50; i++) {
              const value = dataArray[i * step] || 0
              bars.push(Math.max(2, (value / 255) * 30))
            }
            setWaveformBars(bars)
          }
        }, 50)
      } else {
        // Fallback random animation if no analyser
        animationRef.current = setInterval(() => {
          setWaveformBars(prev => 
            prev.map(() => Math.random() * 28 + 2)
          )
        }, 100)
      }
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
      if (animationRef.current) clearInterval(animationRef.current)
    }
  }, [isOpen, isRecording, isPaused])

  const startRecording = async () => {
    try {
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 44100
        } 
      })
      streamRef.current = stream

      // Set up audio analyser for waveform visualization
      try {
        audioContextRef.current = new AudioContext()
        const source = audioContextRef.current.createMediaStreamSource(stream)
        analyserRef.current = audioContextRef.current.createAnalyser()
        analyserRef.current.fftSize = 256
        source.connect(analyserRef.current)
      } catch (e) {
        console.log('Audio analyser not available:', e)
      }

      // Create MediaRecorder
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') 
        ? 'audio/webm;codecs=opus' 
        : MediaRecorder.isTypeSupported('audio/webm')
          ? 'audio/webm'
          : 'audio/mp4'
      
      const mediaRecorder = new MediaRecorder(stream, { mimeType })
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType })
        const finalDuration = elapsedTimeRef.current
        onStop(audioBlob, finalDuration)
        cleanup()
      }

      mediaRecorder.start(100) // Collect data every 100ms
      setIsRecording(true)
      
    } catch (error) {
      console.error('Failed to start recording:', error)
      alert('Mikrofonni ishlatish imkoni bo\'lmadi. Iltimos, ruxsat bering.')
      onClose()
    }
  }

  const cleanup = () => {
    // Stop all tracks
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }
    
    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }
    
    // Clear refs
    mediaRecorderRef.current = null
    analyserRef.current = null
    audioChunksRef.current = []
    
    // Reset state
    setIsRecording(false)
    setElapsedTime(0)
    setIsPaused(false)
    setWaveformBars(Array(50).fill(2))
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const handlePauseResume = () => {
    if (!mediaRecorderRef.current) return

    if (isPaused) {
      mediaRecorderRef.current.resume()
      setIsPaused(false)
    } else {
      mediaRecorderRef.current.pause()
      setIsPaused(true)
      if (animationRef.current) clearInterval(animationRef.current)
    }
  }

  const handleStop = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop()
    }
  }

  const handleCancel = () => {
    cleanup()
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className={styles.overlay}>
      <div className={styles.modal}>
        {/* Handle bar */}
        <div className={styles.handleBar} />

        {/* Header */}
        <div className={styles.header}>
          <div className={styles.headerLeft}>
            <h2 className={styles.title}>Yangi yozuv</h2>
            <p className={styles.subtitle}>
              {isPaused ? 'To\'xtatildi' : 'Yozilmoqda...'}
            </p>
          </div>
          <div className={styles.timer}>
            {formatTime(elapsedTime)} / {formatTime(maxDuration)}
          </div>
        </div>

        {/* Waveform */}
        <div className={styles.waveformContainer}>
          <div className={styles.waveform}>
            {waveformBars.map((height, index) => (
              <div
                key={index}
                className={styles.waveformBar}
                style={{ height: isPaused ? '2px' : `${height}px` }}
              />
            ))}
          </div>
        </div>

        {/* Controls */}
        <div className={styles.controls}>
          <button className={styles.cancelButton} onClick={handleCancel}>
            <X size={28} strokeWidth={2.5} />
          </button>

          <button className={styles.stopButton} onClick={handleStop}>
            <div className={styles.stopIcon} />
          </button>

          <button className={styles.pauseButton} onClick={handlePauseResume}>
            {isPaused ? (
              <Play size={28} fill="currentColor" />
            ) : (
              <Pause size={28} strokeWidth={3} />
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
