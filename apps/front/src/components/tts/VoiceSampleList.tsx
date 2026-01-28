import { useState, useEffect } from "react"
import { Play, Pause, ChevronLeft, ChevronRight, Check, Loader2 } from "lucide-react"

interface VoiceSample {
  voice_id: string
  filename: string
  prompt_text: string
  index: number
}

interface SamplesResponse {
  samples: VoiceSample[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

interface VoiceSampleListProps {
  onSelect: (voiceId: string, audioBase64: string, promptText: string) => void
  onCancel?: () => void
}

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8002"

export function VoiceSampleList({ onSelect, onCancel }: VoiceSampleListProps) {
  const [samples, setSamples] = useState<VoiceSample[]>([])
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  const [playingId, setPlayingId] = useState<string | null>(null)
  const [loadingAudioId, setLoadingAudioId] = useState<string | null>(null)
  const [audioElement, setAudioElement] = useState<HTMLAudioElement | null>(null)

  const perPage = 5

  // Load samples
  useEffect(() => {
    setIsLoading(true)
    setError(null)

    fetch(`${API_BASE}/api/tts/samples?page=${page}&per_page=${perPage}`)
      .then(res => {
        if (!res.ok) throw new Error("샘플 목록을 불러올 수 없습니다")
        return res.json()
      })
      .then((data: SamplesResponse) => {
        setSamples(data.samples)
        setTotalPages(data.total_pages)
        setTotal(data.total)
        setIsLoading(false)
      })
      .catch(err => {
        setError(err.message)
        setIsLoading(false)
      })
  }, [page])

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      if (audioElement) {
        audioElement.pause()
        audioElement.src = ""
      }
    }
  }, [audioElement])

  const handlePlay = async (voiceId: string) => {
    // If already playing this sample, stop it
    if (playingId === voiceId && audioElement) {
      audioElement.pause()
      setPlayingId(null)
      return
    }

    // Stop any currently playing audio
    if (audioElement) {
      audioElement.pause()
    }

    setLoadingAudioId(voiceId)

    try {
      const res = await fetch(`${API_BASE}/api/tts/sample/${voiceId}`)
      if (!res.ok) throw new Error("오디오를 불러올 수 없습니다")
      
      const data = await res.json()
      const audioBase64 = data.audio_base64

      // Create audio from base64
      const base64Data = audioBase64.includes(",") ? audioBase64.split(",")[1] : audioBase64
      const binaryString = atob(base64Data)
      const bytes = new Uint8Array(binaryString.length)
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i)
      }
      
      const blob = new Blob([bytes], { type: "audio/wav" })
      const url = URL.createObjectURL(blob)

      const audio = new Audio(url)
      audio.onended = () => {
        setPlayingId(null)
        URL.revokeObjectURL(url)
      }
      audio.onerror = () => {
        setPlayingId(null)
        URL.revokeObjectURL(url)
      }

      await audio.play()
      setAudioElement(audio)
      setPlayingId(voiceId)
    } catch (err) {
      console.error("Audio play error:", err)
    } finally {
      setLoadingAudioId(null)
    }
  }

  const handleSelect = async (sample: VoiceSample) => {
    setLoadingAudioId(sample.voice_id)

    try {
      const res = await fetch(`${API_BASE}/api/tts/sample/${sample.voice_id}`)
      if (!res.ok) throw new Error("오디오를 불러올 수 없습니다")
      
      const data = await res.json()
      onSelect(sample.voice_id, data.audio_base64, sample.prompt_text)
    } catch (err) {
      setError(err instanceof Error ? err.message : "오류가 발생했습니다")
    } finally {
      setLoadingAudioId(null)
    }
  }

  if (isLoading) {
    return (
      <div className="bg-zinc-800 rounded-lg p-6 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-emerald-400" />
        <span className="ml-2 text-zinc-300">샘플 로딩 중...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-zinc-800 rounded-lg p-6">
        <p className="text-red-400 text-center">{error}</p>
        {onCancel && (
          <button
            onClick={onCancel}
            className="mt-4 w-full text-sm text-zinc-400 hover:text-zinc-300"
          >
            돌아가기
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="bg-zinc-800 rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-zinc-100 font-medium">샘플 보이스 선택</span>
        <span className="text-xs text-zinc-500">총 {total}개</span>
      </div>

      {/* Sample List */}
      <div className="space-y-2">
        {samples.map((sample) => (
          <div
            key={sample.voice_id}
            className="flex items-center gap-3 p-3 bg-zinc-700/50 rounded-lg hover:bg-zinc-700 transition-colors"
          >
            {/* Play Button */}
            <button
              onClick={() => handlePlay(sample.voice_id)}
              disabled={loadingAudioId === sample.voice_id}
              className="w-10 h-10 flex items-center justify-center bg-zinc-600 hover:bg-zinc-500 disabled:bg-zinc-600 rounded-full transition-colors flex-shrink-0"
            >
              {loadingAudioId === sample.voice_id ? (
                <Loader2 className="w-4 h-4 animate-spin text-zinc-300" />
              ) : playingId === sample.voice_id ? (
                <Pause className="w-4 h-4 text-emerald-400" fill="currentColor" />
              ) : (
                <Play className="w-4 h-4 text-zinc-300 ml-0.5" fill="currentColor" />
              )}
            </button>

            {/* Sample Info */}
            <div className="flex-1 min-w-0">
              <p className="text-sm text-zinc-200 font-medium truncate">
                Sample {sample.index + 1}
              </p>
              <p className="text-xs text-zinc-400 truncate" title={sample.prompt_text}>
                {sample.prompt_text || "텍스트 없음"}
              </p>
            </div>

            {/* Select Button */}
            <button
              onClick={() => handleSelect(sample)}
              disabled={loadingAudioId === sample.voice_id}
              className="px-3 py-1.5 bg-emerald-500 hover:bg-emerald-400 disabled:bg-emerald-500/50 rounded-lg text-white text-sm transition-colors flex items-center gap-1"
            >
              <Check className="w-3 h-3" />
              <span>선택</span>
            </button>
          </div>
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 pt-2">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="p-2 bg-zinc-700 hover:bg-zinc-600 disabled:bg-zinc-700 disabled:opacity-50 rounded-lg transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-sm text-zinc-400">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="p-2 bg-zinc-700 hover:bg-zinc-600 disabled:bg-zinc-700 disabled:opacity-50 rounded-lg transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Cancel Button */}
      {onCancel && (
        <button
          onClick={onCancel}
          className="w-full text-sm text-zinc-400 hover:text-zinc-300 transition-colors pt-2"
        >
          취소
        </button>
      )}
    </div>
  )
}
