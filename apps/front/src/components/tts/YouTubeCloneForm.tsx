import { useState } from "react"
import { Link, Clock, RefreshCw, Check, AlertCircle } from "lucide-react"
import { AudioPlayer } from "../AudioPlayer"

interface YouTubeCloneFormProps {
  onExtracted: (audioBase64: string, refText: string, duration: number) => void
  onCancel?: () => void
}

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8002"

export function YouTubeCloneForm({ onExtracted, onCancel }: YouTubeCloneFormProps) {
  const [url, setUrl] = useState("")
  const [startTime, setStartTime] = useState("")
  const [endTime, setEndTime] = useState("")
  
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const [extractedAudio, setExtractedAudio] = useState<string | null>(null)
  const [extractedRefText, setExtractedRefText] = useState("")
  const [extractedDuration, setExtractedDuration] = useState(0)
  const [qualityScore, setQualityScore] = useState(0)

  const isValidUrl = (urlStr: string) => {
    return urlStr.includes("youtube.com") || urlStr.includes("youtu.be")
  }

  const isValidTime = (time: string) => {
    // Allow formats: "30", "1:30", "01:30", "1:30:00"
    return /^(\d{1,2}:)?\d{1,2}(:\d{2})?$/.test(time) || /^\d+$/.test(time)
  }

  const handleExtract = async () => {
    if (!isValidUrl(url)) {
      setError("올바른 YouTube URL을 입력해주세요")
      return
    }
    if (!isValidTime(startTime) || !isValidTime(endTime)) {
      setError("시간 형식을 확인해주세요 (예: 0:30, 1:45)")
      return
    }

    setIsLoading(true)
    setError(null)
    setExtractedAudio(null)

    try {
      const res = await fetch(`${API_BASE}/api/tts/extract-youtube`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url,
          start_time: startTime,
          end_time: endTime
        })
      })

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.detail || "오디오 추출에 실패했습니다")
      }

      const data = await res.json()
      setExtractedAudio(data.audio_base64)
      setExtractedRefText(data.ref_text || "")
      setExtractedDuration(data.duration)
      setQualityScore(data.quality_score)
    } catch (err) {
      setError(err instanceof Error ? err.message : "오류가 발생했습니다")
    } finally {
      setIsLoading(false)
    }
  }

  const handleConfirm = () => {
    if (extractedAudio) {
      onExtracted(extractedAudio, extractedRefText, extractedDuration)
    }
  }

  const handleReset = () => {
    setExtractedAudio(null)
    setExtractedRefText("")
    setExtractedDuration(0)
    setQualityScore(0)
    setError(null)
  }

  return (
    <div className="bg-zinc-800 rounded-lg p-4 space-y-4">
      <div className="flex items-center gap-2 text-zinc-100 font-medium">
        <Link className="w-5 h-5 text-red-400" />
        <span>YouTube 보이스 클로닝</span>
      </div>

      {/* URL Input */}
      <div className="space-y-2">
        <label className="text-sm text-zinc-300">YouTube URL</label>
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://youtube.com/watch?v=..."
          disabled={!!extractedAudio}
          className="w-full px-3 py-2 bg-zinc-700 border border-zinc-600 rounded-lg text-zinc-100 placeholder-zinc-500 focus:border-emerald-500 focus:outline-none disabled:opacity-50"
        />
      </div>

      {/* Time Inputs */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-2">
          <label className="text-sm text-zinc-300 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            시작 시간
          </label>
          <input
            type="text"
            value={startTime}
            onChange={(e) => setStartTime(e.target.value)}
            placeholder="0:30"
            disabled={!!extractedAudio}
            className="w-full px-3 py-2 bg-zinc-700 border border-zinc-600 rounded-lg text-zinc-100 placeholder-zinc-500 focus:border-emerald-500 focus:outline-none disabled:opacity-50"
          />
        </div>
        <div className="space-y-2">
          <label className="text-sm text-zinc-300 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            종료 시간
          </label>
          <input
            type="text"
            value={endTime}
            onChange={(e) => setEndTime(e.target.value)}
            placeholder="0:45"
            disabled={!!extractedAudio}
            className="w-full px-3 py-2 bg-zinc-700 border border-zinc-600 rounded-lg text-zinc-100 placeholder-zinc-500 focus:border-emerald-500 focus:outline-none disabled:opacity-50"
          />
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="flex items-center gap-2 text-sm text-red-400 bg-red-400/10 rounded-lg p-3">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Extracted Audio Preview */}
      {extractedAudio && (
        <div className="space-y-3 pt-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-emerald-400">추출 완료!</span>
            <span className="text-zinc-400">
              {extractedDuration.toFixed(1)}초 / 품질 {(qualityScore * 100).toFixed(0)}%
            </span>
          </div>
          
          <AudioPlayer audioBase64={extractedAudio} voiceName="추출된 음성" />
          
          {extractedRefText && (
            <div className="space-y-1">
              <span className="text-xs text-zinc-500">감지된 텍스트:</span>
              <p className="text-sm text-zinc-400 bg-zinc-700/50 rounded-lg p-2 italic">
                "{extractedRefText.slice(0, 100)}{extractedRefText.length > 100 ? "..." : ""}"
              </p>
            </div>
          )}
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3 pt-2">
        {!extractedAudio ? (
          <button
            onClick={handleExtract}
            disabled={isLoading || !url || !startTime || !endTime}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-red-500 hover:bg-red-400 disabled:bg-red-500/50 disabled:cursor-not-allowed rounded-lg text-white transition-colors"
          >
            {isLoading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>추출 중...</span>
              </>
            ) : (
              <>
                <Link className="w-4 h-4" />
                <span>추출하기</span>
              </>
            )}
          </button>
        ) : (
          <>
            <button
              onClick={handleReset}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-zinc-700 hover:bg-zinc-600 rounded-lg text-zinc-100 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              <span>다시 추출</span>
            </button>
            <button
              onClick={handleConfirm}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-500 hover:bg-emerald-400 rounded-lg text-white transition-colors"
            >
              <Check className="w-4 h-4" />
              <span>확정</span>
            </button>
          </>
        )}
      </div>

      {/* Cancel Button */}
      {onCancel && (
        <button
          onClick={onCancel}
          className="w-full text-sm text-zinc-400 hover:text-zinc-300 transition-colors"
        >
          취소
        </button>
      )}
    </div>
  )
}
