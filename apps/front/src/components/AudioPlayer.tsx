import { useState, useRef, useEffect } from "react"
import { Play, Pause, Volume2 } from "lucide-react"

interface AudioPlayerProps {
  audioBase64: string
  voiceName?: string
  duration?: number
  className?: string
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, "0")}`
}

export function AudioPlayer({ audioBase64, voiceName = "Audio", duration: propDuration, className = "" }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(propDuration || 0)
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Convert base64 to blob URL
  useEffect(() => {
    if (!audioBase64) {
      setError("No audio data")
      setIsLoading(false)
      return
    }

    try {
      // Handle data URL or raw base64
      const base64Data = audioBase64.includes(",") 
        ? audioBase64.split(",")[1] 
        : audioBase64

      const binaryString = atob(base64Data)
      const bytes = new Uint8Array(binaryString.length)
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i)
      }

      // Detect MIME type from magic bytes
      let mimeType = "audio/mpeg" // default to mp3
      if (bytes[0] === 0x52 && bytes[1] === 0x49 && bytes[2] === 0x46 && bytes[3] === 0x46) {
        mimeType = "audio/wav"
      } else if (bytes[0] === 0x4F && bytes[1] === 0x67 && bytes[2] === 0x67 && bytes[3] === 0x53) {
        mimeType = "audio/ogg"
      }

      const blob = new Blob([bytes], { type: mimeType })
      const url = URL.createObjectURL(blob)
      setBlobUrl(url)
      setIsLoading(false)
      setError(null)

      return () => {
        URL.revokeObjectURL(url)
      }
    } catch (e) {
      setError("Failed to decode audio")
      setIsLoading(false)
    }
  }, [audioBase64])

  // Audio event handlers
  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const handleTimeUpdate = () => setCurrentTime(audio.currentTime)
    const handleLoadedMetadata = () => setDuration(audio.duration)
    const handleEnded = () => setIsPlaying(false)
    const handleError = () => setError("Playback error")

    audio.addEventListener("timeupdate", handleTimeUpdate)
    audio.addEventListener("loadedmetadata", handleLoadedMetadata)
    audio.addEventListener("ended", handleEnded)
    audio.addEventListener("error", handleError)

    return () => {
      audio.removeEventListener("timeupdate", handleTimeUpdate)
      audio.removeEventListener("loadedmetadata", handleLoadedMetadata)
      audio.removeEventListener("ended", handleEnded)
      audio.removeEventListener("error", handleError)
    }
  }, [blobUrl])

  const togglePlay = () => {
    const audio = audioRef.current
    if (!audio) return

    if (isPlaying) {
      audio.pause()
    } else {
      audio.play()
    }
    setIsPlaying(!isPlaying)
  }

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const audio = audioRef.current
    if (!audio) return

    const newTime = parseFloat(e.target.value)
    audio.currentTime = newTime
    setCurrentTime(newTime)
  }

  if (error) {
    return (
      <div className={`flex items-center gap-2 px-3 py-2 bg-zinc-800 rounded-lg text-red-400 text-sm ${className}`}>
        <Volume2 className="h-4 w-4" />
        <span>{error}</span>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className={`flex items-center gap-2 px-3 py-2 bg-zinc-800 rounded-lg text-zinc-400 text-sm ${className}`}>
        <div className="h-4 w-4 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
        <span>Loading audio...</span>
      </div>
    )
  }

  return (
    <div className={`flex items-center gap-3 px-3 py-2 bg-zinc-700 rounded-lg ${className}`}>
      {blobUrl && <audio ref={audioRef} src={blobUrl} preload="metadata" />}
      
      {/* Voice name */}
      <div className="flex items-center gap-1.5 min-w-[80px]">
        <Volume2 className="h-4 w-4 text-emerald-400 flex-shrink-0" />
        <span className="text-sm text-zinc-200 truncate">{voiceName}</span>
      </div>

      {/* Play/Pause button */}
      <button
        onClick={togglePlay}
        className="w-8 h-8 flex items-center justify-center bg-emerald-500 hover:bg-emerald-400 rounded-full transition-colors flex-shrink-0"
      >
        {isPlaying ? (
          <Pause className="h-4 w-4 text-white" fill="white" />
        ) : (
          <Play className="h-4 w-4 text-white ml-0.5" fill="white" />
        )}
      </button>

      {/* Progress bar */}
      <div className="flex-1 flex items-center gap-2">
        <input
          type="range"
          min={0}
          max={duration || 100}
          value={currentTime}
          onChange={handleSeek}
          className="flex-1 h-1.5 bg-zinc-600 rounded-full appearance-none cursor-pointer
            [&::-webkit-slider-thumb]:appearance-none
            [&::-webkit-slider-thumb]:w-3
            [&::-webkit-slider-thumb]:h-3
            [&::-webkit-slider-thumb]:bg-emerald-400
            [&::-webkit-slider-thumb]:rounded-full
            [&::-webkit-slider-thumb]:cursor-pointer
            [&::-webkit-slider-thumb]:hover:bg-emerald-300"
        />
      </div>

      {/* Time display */}
      <span className="text-xs text-zinc-400 min-w-[70px] text-right">
        {formatTime(currentTime)} / {formatTime(duration)}
      </span>
    </div>
  )
}
