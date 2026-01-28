import { useState, useEffect } from "react"
import { Volume2, Check, RefreshCw } from "lucide-react"
import { AudioPlayer } from "../AudioPlayer"

interface InstructExample {
  label: string
  value: string
  description: string
}

interface InstructExamples {
  emotions: InstructExample[]
  speed_range: { min: number; max: number; default: number; step: number }
  pitch_range: { min: number; max: number; default: number; step: number }
}

interface TTSSettings {
  speed: number
  pitch: number
  instruct: string
}

interface TTSSettingsProps {
  channelName: string
  defaultText?: string
  onConfirm: (settings: TTSSettings) => void
  onCancel?: () => void
}

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8002"

export function TTSSettingsPanel({ channelName, defaultText, onConfirm, onCancel }: TTSSettingsProps) {
  const [speed, setSpeed] = useState(1.0)
  const [pitch, setPitch] = useState(0)
  const [instruct, setInstruct] = useState("")
  const [emotions, setEmotions] = useState<InstructExample[]>([])
  const [speedRange, setSpeedRange] = useState({ min: 0.5, max: 2.0, step: 0.1 })
  const [pitchRange, setPitchRange] = useState({ min: -20, max: 20, step: 1 })
  
  const [previewAudio, setPreviewAudio] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const testText = defaultText || `안녕하세요 ${channelName} 입니다. 루틴 스튜디오로 함께 만들어보는 유튜브 영상 제작 프로세스 입니다.`

  // Load emotion options on mount
  useEffect(() => {
    fetch(`${API_BASE}/api/tts/instruct-examples`)
      .then(res => res.json())
      .then((data: InstructExamples) => {
        setEmotions(data.emotions || [])
        if (data.speed_range) setSpeedRange(data.speed_range)
        if (data.pitch_range) setPitchRange(data.pitch_range)
      })
      .catch(err => console.error("Failed to load instruct examples:", err))
  }, [])

  const handlePreview = async () => {
    setIsLoading(true)
    setError(null)
    setPreviewAudio(null)

    try {
      const response = await fetch(`${API_BASE}/api/tts/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: testText,
          speaker: "Sohee",
          speed,
          pitch,
          instruct
        })
      })

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}))
        throw new Error(errData.detail || "미리듣기 생성 실패")
      }

      const data = await response.json()
      setPreviewAudio(data.audio_base64)
    } catch (err) {
      setError(err instanceof Error ? err.message : "오류가 발생했습니다")
    } finally {
      setIsLoading(false)
    }
  }

  const handleConfirm = () => {
    onConfirm({ speed, pitch, instruct })
  }

  return (
    <div className="bg-zinc-800 rounded-lg p-4 space-y-4">
      <div className="flex items-center gap-2 text-zinc-100 font-medium">
        <Volume2 className="w-5 h-5 text-emerald-400" />
        <span>음성 설정</span>
      </div>

      {/* Speed Slider */}
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-zinc-300">속도</span>
          <span className="text-emerald-400">{speed.toFixed(1)}x</span>
        </div>
        <input
          type="range"
          min={speedRange.min}
          max={speedRange.max}
          step={speedRange.step}
          value={speed}
          onChange={(e) => setSpeed(parseFloat(e.target.value))}
          className="w-full h-2 bg-zinc-700 rounded-full appearance-none cursor-pointer
            [&::-webkit-slider-thumb]:appearance-none
            [&::-webkit-slider-thumb]:w-4
            [&::-webkit-slider-thumb]:h-4
            [&::-webkit-slider-thumb]:bg-emerald-500
            [&::-webkit-slider-thumb]:rounded-full
            [&::-webkit-slider-thumb]:cursor-pointer
            [&::-webkit-slider-thumb]:hover:bg-emerald-400"
        />
        <div className="flex justify-between text-xs text-zinc-500">
          <span>{speedRange.min}x</span>
          <span>{speedRange.max}x</span>
        </div>
      </div>

      {/* Pitch Slider */}
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-zinc-300">피치</span>
          <span className="text-emerald-400">{pitch > 0 ? `+${pitch}` : pitch}</span>
        </div>
        <input
          type="range"
          min={pitchRange.min}
          max={pitchRange.max}
          step={pitchRange.step}
          value={pitch}
          onChange={(e) => setPitch(parseInt(e.target.value))}
          className="w-full h-2 bg-zinc-700 rounded-full appearance-none cursor-pointer
            [&::-webkit-slider-thumb]:appearance-none
            [&::-webkit-slider-thumb]:w-4
            [&::-webkit-slider-thumb]:h-4
            [&::-webkit-slider-thumb]:bg-emerald-500
            [&::-webkit-slider-thumb]:rounded-full
            [&::-webkit-slider-thumb]:cursor-pointer
            [&::-webkit-slider-thumb]:hover:bg-emerald-400"
        />
        <div className="flex justify-between text-xs text-zinc-500">
          <span>{pitchRange.min}</span>
          <span>+{pitchRange.max}</span>
        </div>
      </div>

      {/* Emotion Buttons */}
      {emotions.length > 0 && (
        <div className="space-y-2">
          <span className="text-sm text-zinc-300">감정/스타일</span>
          <div className="flex flex-wrap gap-2">
            {emotions.map((emotion) => (
              <button
                key={emotion.value}
                onClick={() => setInstruct(instruct === emotion.value ? "" : emotion.value)}
                className={`px-3 py-1.5 text-sm rounded-lg border transition-colors
                  ${instruct === emotion.value
                    ? "border-emerald-500 bg-emerald-500/20 text-emerald-400"
                    : "border-zinc-600 text-zinc-300 hover:border-zinc-500"
                  }`}
                title={emotion.description}
              >
                {emotion.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Test Text */}
      <div className="space-y-2">
        <span className="text-sm text-zinc-300">테스트 문장</span>
        <p className="text-sm text-zinc-400 bg-zinc-700/50 rounded-lg p-3 italic">
          "{testText}"
        </p>
      </div>

      {/* Preview Audio */}
      {previewAudio && (
        <div className="pt-2">
          <AudioPlayer audioBase64={previewAudio} voiceName="미리듣기" />
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="text-sm text-red-400 bg-red-400/10 rounded-lg p-3">
          {error}
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3 pt-2">
        <button
          onClick={handlePreview}
          disabled={isLoading}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-zinc-700 hover:bg-zinc-600 disabled:bg-zinc-700 disabled:opacity-50 rounded-lg text-zinc-100 transition-colors"
        >
          {isLoading ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span>생성 중...</span>
            </>
          ) : (
            <>
              <Volume2 className="w-4 h-4" />
              <span>미리듣기</span>
            </>
          )}
        </button>
        <button
          onClick={handleConfirm}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-500 hover:bg-emerald-400 rounded-lg text-white transition-colors"
        >
          <Check className="w-4 h-4" />
          <span>확정</span>
        </button>
      </div>

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
