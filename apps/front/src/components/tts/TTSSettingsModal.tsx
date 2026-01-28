import { useState, useEffect, useRef } from "react"
import { X, Volume2, Check, RefreshCw, Music, Youtube, Mic2, Play, Pause, ChevronLeft, ChevronRight, Clock } from "lucide-react"
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

interface VoiceSample {
  voice_id: string
  filename: string
  prompt_text: string
  index: number
}

interface TTSSettings {
  type: "default" | "clone_sample" | "clone_youtube"
  speed?: number
  pitch?: number
  instruct?: string
  text: string
  sampleId?: string
  sampleRefText?: string
  youtubeUrl?: string
  timeRange?: string
}

interface TTSSettingsModalProps {
  isOpen: boolean
  channelName: string
  defaultText?: string
  onConfirm: (settings: TTSSettings) => void
  onClose: () => void
}

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8002"

type TabType = "default" | "cloning"
type CloningMethod = "sample" | "youtube"

// Time parsing utilities
const parseTimeToSeconds = (time: string): number => {
  if (!time) return 0
  const trimmed = time.trim()
  
  // Already seconds (number only)
  if (/^\d+$/.test(trimmed)) {
    return parseInt(trimmed, 10)
  }
  
  // MM:SS or HH:MM:SS format
  const parts = trimmed.split(':').map(p => parseInt(p, 10) || 0)
  if (parts.length === 2) {
    // MM:SS
    return parts[0] * 60 + parts[1]
  } else if (parts.length === 3) {
    // HH:MM:SS
    return parts[0] * 3600 + parts[1] * 60 + parts[2]
  }
  return 0
}

const formatSecondsToTime = (seconds: number): string => {
  if (seconds < 0) seconds = 0
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  
  if (h > 0) {
    return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }
  return `${m}:${s.toString().padStart(2, '0')}`
}

export function TTSSettingsModal({ isOpen, channelName, defaultText, onConfirm, onClose }: TTSSettingsModalProps) {
  // Tab state
  const [activeTab, setActiveTab] = useState<TabType>("default")
  
  // Default voice settings
  const [speed, setSpeed] = useState(1.0)
  const [pitch, setPitch] = useState(0)
  const [instruct, setInstruct] = useState("")
  const [emotions, setEmotions] = useState<InstructExample[]>([])
  const [speedRange, setSpeedRange] = useState({ min: 0.5, max: 2.0, step: 0.1 })
  const [pitchRange, setPitchRange] = useState({ min: -20, max: 20, step: 1 })
  
  // Editable text
  const [testText, setTestText] = useState("")
  
  // Voice cloning settings
  const [cloningMethod, setCloningMethod] = useState<CloningMethod>("sample")
  const [voiceSamples, setVoiceSamples] = useState<VoiceSample[]>([])
  const [selectedSample, setSelectedSample] = useState<VoiceSample | null>(null)
  const [youtubeUrl, setYoutubeUrl] = useState("")
  
  // Separate time inputs
  const [startTime, setStartTime] = useState("")
  const [endTime, setEndTime] = useState("")
  const [duration, setDuration] = useState(15) // default 15 seconds
  
  // Pagination
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalSamples, setTotalSamples] = useState(0)
  const perPage = 5
  
  // Sample preview state
  const [playingSampleId, setPlayingSampleId] = useState<string | null>(null)
  const [sampleAudioLoading, setSampleAudioLoading] = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  
  // Preview state
  const [previewAudio, setPreviewAudio] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Auto-calculate end time when start time changes
  useEffect(() => {
    if (startTime && !endTime) {
      const startSeconds = parseTimeToSeconds(startTime)
      const endSeconds = startSeconds + duration
      setEndTime(formatSecondsToTime(endSeconds))
    }
  }, [startTime, duration])

  // Initialize text
  useEffect(() => {
    if (isOpen) {
      setTestText(defaultText || `안녕하세요 ${channelName} 입니다. 루틴 스튜디오로 함께 만들어보는 유튜브 영상 제작 프로세스 입니다.`)
    }
  }, [isOpen, defaultText, channelName])

  // Load emotion options on mount
  useEffect(() => {
    if (!isOpen) return
    
    fetch(`${API_BASE}/api/tts/instruct-examples`)
      .then(res => res.json())
      .then((data: InstructExamples) => {
        setEmotions(data.emotions || [])
        if (data.speed_range) setSpeedRange(data.speed_range)
        if (data.pitch_range) setPitchRange(data.pitch_range)
      })
      .catch(err => console.error("Failed to load instruct examples:", err))
  }, [isOpen])

  // Load voice samples when cloning tab is active
  useEffect(() => {
    if (!isOpen || activeTab !== "cloning") return
    
    fetch(`${API_BASE}/api/tts/samples?page=${currentPage}&per_page=${perPage}`)
      .then(res => res.json())
      .then((data) => {
        setVoiceSamples(data.samples || [])
        setTotalPages(data.total_pages || 1)
        setTotalSamples(data.total || 0)
      })
      .catch(err => {
        console.error("Failed to load voice samples:", err)
        setVoiceSamples([])
      })
  }, [isOpen, activeTab, currentPage])

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setActiveTab("default")
      setSpeed(1.0)
      setPitch(0)
      setInstruct("")
      setPreviewAudio(null)
      setError(null)
      setSelectedSample(null)
      setYoutubeUrl("")
      setStartTime("")
      setEndTime("")
      setDuration(15)
      setCloningMethod("sample")
      setCurrentPage(1)
      stopSamplePlayback()
    }
  }, [isOpen])

  // Handle ESC key
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) onClose()
    }
    window.addEventListener("keydown", handleEsc)
    return () => window.removeEventListener("keydown", handleEsc)
  }, [isOpen, onClose])

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current = null
      }
    }
  }, [])

  const stopSamplePlayback = () => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current = null
    }
    setPlayingSampleId(null)
  }

  const handlePlaySample = async (sample: VoiceSample) => {
    // If same sample is playing, stop it
    if (playingSampleId === sample.voice_id) {
      stopSamplePlayback()
      return
    }

    // Stop any current playback
    stopSamplePlayback()

    try {
      setSampleAudioLoading(sample.voice_id)
      
      const response = await fetch(`${API_BASE}/api/tts/sample/${sample.voice_id}`)
      if (!response.ok) throw new Error("Failed to load sample audio")
      
      const data = await response.json()
      
      // Create and play audio
      const audioBlob = base64ToBlob(data.audio_base64, "audio/mpeg")
      const audioUrl = URL.createObjectURL(audioBlob)
      
      const audio = new Audio(audioUrl)
      audioRef.current = audio
      
      audio.onended = () => {
        setPlayingSampleId(null)
        URL.revokeObjectURL(audioUrl)
      }
      
      audio.onerror = () => {
        setPlayingSampleId(null)
        URL.revokeObjectURL(audioUrl)
      }
      
      await audio.play()
      setPlayingSampleId(sample.voice_id)
    } catch (err) {
      console.error("Failed to play sample:", err)
      setError("샘플 재생에 실패했습니다")
    } finally {
      setSampleAudioLoading(null)
    }
  }

  const base64ToBlob = (base64: string, mimeType: string): Blob => {
    const byteCharacters = atob(base64)
    const byteNumbers = new Array(byteCharacters.length)
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i)
    }
    const byteArray = new Uint8Array(byteNumbers)
    return new Blob([byteArray], { type: mimeType })
  }

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

  // 샘플 클로닝 미리듣기
  const handleSampleClonePreview = async () => {
    if (!selectedSample) {
      setError("샘플을 먼저 선택해주세요")
      return
    }

    setIsLoading(true)
    setError(null)
    setPreviewAudio(null)

    try {
      // 1. 선택된 샘플의 오디오 가져오기
      const sampleRes = await fetch(`${API_BASE}/api/tts/sample/${selectedSample.voice_id}`)
      if (!sampleRes.ok) throw new Error("샘플 오디오 로드 실패")
      const sampleData = await sampleRes.json()

      // 2. 클로닝 미리듣기 요청
      const response = await fetch(`${API_BASE}/api/tts/clone-preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: testText,
          ref_audio_base64: sampleData.audio_base64,
          ref_text: selectedSample.prompt_text
        })
      })

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}))
        throw new Error(errData.detail || "클로닝 미리듣기 실패")
      }

      const data = await response.json()
      setPreviewAudio(data.audio_base64)
    } catch (err) {
      setError(err instanceof Error ? err.message : "오류가 발생했습니다")
    } finally {
      setIsLoading(false)
    }
  }

  // YouTube 클로닝 미리듣기
  const handleYoutubeClonePreview = async () => {
    if (!youtubeUrl || !startTime || !endTime) {
      setError("YouTube URL과 시간 범위를 입력해주세요")
      return
    }

    setIsLoading(true)
    setError(null)
    setPreviewAudio(null)

    try {
      // 1. YouTube에서 오디오 추출
      const extractRes = await fetch(`${API_BASE}/api/tts/extract-youtube`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: youtubeUrl,
          start_time: startTime,
          end_time: endTime
        })
      })

      if (!extractRes.ok) {
        const errData = await extractRes.json().catch(() => ({}))
        throw new Error(errData.detail || "YouTube 오디오 추출 실패")
      }

      const extractData = await extractRes.json()

      // 2. 클로닝 미리듣기 요청
      const response = await fetch(`${API_BASE}/api/tts/clone-preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: testText,
          ref_audio_base64: extractData.audio_base64,
          ref_text: extractData.ref_text || ""
        })
      })

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}))
        throw new Error(errData.detail || "클로닝 미리듣기 실패")
      }

      const data = await response.json()
      setPreviewAudio(data.audio_base64)
    } catch (err) {
      setError(err instanceof Error ? err.message : "오류가 발생했습니다")
    } finally {
      setIsLoading(false)
    }
  }

  // 클로닝 미리듣기 핸들러
  const handleClonePreview = () => {
    if (cloningMethod === "sample") {
      handleSampleClonePreview()
    } else {
      handleYoutubeClonePreview()
    }
  }

  // 클로닝 미리듣기 가능 여부
  const canClonePreview = () => {
    if (cloningMethod === "sample") return !!selectedSample && testText.trim().length > 0
    if (cloningMethod === "youtube") return !!youtubeUrl && !!startTime && !!endTime && testText.trim().length > 0
    return false
  }

  const handleStartTimeChange = (value: string) => {
    setStartTime(value)
    // Auto-calculate end time
    if (value) {
      const startSeconds = parseTimeToSeconds(value)
      const endSeconds = startSeconds + duration
      setEndTime(formatSecondsToTime(endSeconds))
    }
  }

  const getTimeRange = (): string => {
    if (startTime && endTime) {
      return `${startTime}-${endTime}`
    }
    return ""
  }

  const handleConfirm = () => {
    if (activeTab === "default") {
      onConfirm({ 
        type: "default",
        speed, 
        pitch, 
        instruct,
        text: testText
      })
    } else if (cloningMethod === "sample" && selectedSample) {
      onConfirm({
        type: "clone_sample",
        sampleId: selectedSample.voice_id,
        sampleRefText: selectedSample.prompt_text,
        text: testText
      })
    } else if (cloningMethod === "youtube" && youtubeUrl && startTime) {
      onConfirm({
        type: "clone_youtube",
        youtubeUrl,
        timeRange: getTimeRange(),
        text: testText
      })
    }
  }

  const canConfirm = () => {
    if (activeTab === "default") return true
    if (cloningMethod === "sample") return !!selectedSample
    if (cloningMethod === "youtube") return !!youtubeUrl && !!startTime
    return false
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative bg-zinc-900 rounded-2xl shadow-2xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto border border-zinc-700">
        {/* Header */}
        <div className="sticky top-0 bg-zinc-900 border-b border-zinc-700 px-6 py-4 flex items-center justify-between z-10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-emerald-500/20 rounded-xl flex items-center justify-center">
              <Volume2 className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">음성 설정</h2>
              <p className="text-sm text-zinc-400">{channelName}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-zinc-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-zinc-400" />
          </button>
        </div>

        {/* Tabs */}
        <div className="px-6 pt-4">
          <div className="flex gap-2 p-1 bg-zinc-800 rounded-xl">
            <button
              onClick={() => setActiveTab("default")}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === "default"
                  ? "bg-emerald-500 text-white shadow-lg"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700"
              }`}
            >
              <Mic2 className="w-4 h-4" />
              기본 음성
            </button>
            <button
              onClick={() => setActiveTab("cloning")}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === "cloning"
                  ? "bg-emerald-500 text-white shadow-lg"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700"
              }`}
            >
              <Music className="w-4 h-4" />
              보이스 클로닝
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Default Voice Tab */}
          {activeTab === "default" && (
            <>
              {/* Speed Slider */}
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-300 font-medium">속도</span>
                  <span className="text-emerald-400 font-mono">{speed.toFixed(1)}x</span>
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
                    [&::-webkit-slider-thumb]:w-5
                    [&::-webkit-slider-thumb]:h-5
                    [&::-webkit-slider-thumb]:bg-emerald-500
                    [&::-webkit-slider-thumb]:rounded-full
                    [&::-webkit-slider-thumb]:cursor-pointer
                    [&::-webkit-slider-thumb]:hover:bg-emerald-400
                    [&::-webkit-slider-thumb]:shadow-lg"
                />
                <div className="flex justify-between text-xs text-zinc-500">
                  <span>느리게 {speedRange.min}x</span>
                  <span>빠르게 {speedRange.max}x</span>
                </div>
              </div>

              {/* Pitch Slider */}
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-300 font-medium">피치</span>
                  <span className="text-emerald-400 font-mono">{pitch > 0 ? `+${pitch}` : pitch}</span>
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
                    [&::-webkit-slider-thumb]:w-5
                    [&::-webkit-slider-thumb]:h-5
                    [&::-webkit-slider-thumb]:bg-emerald-500
                    [&::-webkit-slider-thumb]:rounded-full
                    [&::-webkit-slider-thumb]:cursor-pointer
                    [&::-webkit-slider-thumb]:hover:bg-emerald-400
                    [&::-webkit-slider-thumb]:shadow-lg"
                />
                <div className="flex justify-between text-xs text-zinc-500">
                  <span>낮게 {pitchRange.min}</span>
                  <span>높게 +{pitchRange.max}</span>
                </div>
              </div>

              {/* Emotion Buttons */}
              {emotions.length > 0 && (
                <div className="space-y-3">
                  <span className="text-sm text-zinc-300 font-medium">감정/스타일</span>
                  <div className="flex flex-wrap gap-2">
                    {emotions.map((emotion) => (
                      <button
                        key={emotion.value}
                        onClick={() => setInstruct(instruct === emotion.value ? "" : emotion.value)}
                        className={`px-4 py-2 text-sm rounded-xl border-2 transition-all
                          ${instruct === emotion.value
                            ? "border-emerald-500 bg-emerald-500/20 text-emerald-400 shadow-lg shadow-emerald-500/20"
                            : "border-zinc-700 text-zinc-300 hover:border-zinc-500 hover:bg-zinc-800"
                          }`}
                        title={emotion.description}
                      >
                        {emotion.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          {/* Voice Cloning Tab */}
          {activeTab === "cloning" && (
            <>
              {/* Cloning Method Selection */}
              <div className="space-y-3">
                <span className="text-sm text-zinc-300 font-medium">클로닝 방식 선택</span>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={() => setCloningMethod("sample")}
                    className={`p-4 rounded-xl border-2 transition-all text-left ${
                      cloningMethod === "sample"
                        ? "border-emerald-500 bg-emerald-500/10"
                        : "border-zinc-700 hover:border-zinc-500"
                    }`}
                  >
                    <Mic2 className={`w-5 h-5 mb-2 ${cloningMethod === "sample" ? "text-emerald-400" : "text-zinc-400"}`} />
                    <div className={`font-medium ${cloningMethod === "sample" ? "text-emerald-400" : "text-zinc-200"}`}>샘플 선택</div>
                    <div className="text-xs text-zinc-500 mt-1">준비된 음성 샘플 사용</div>
                  </button>
                  <button
                    onClick={() => setCloningMethod("youtube")}
                    className={`p-4 rounded-xl border-2 transition-all text-left ${
                      cloningMethod === "youtube"
                        ? "border-emerald-500 bg-emerald-500/10"
                        : "border-zinc-700 hover:border-zinc-500"
                    }`}
                  >
                    <Youtube className={`w-5 h-5 mb-2 ${cloningMethod === "youtube" ? "text-emerald-400" : "text-zinc-400"}`} />
                    <div className={`font-medium ${cloningMethod === "youtube" ? "text-emerald-400" : "text-zinc-200"}`}>YouTube 추출</div>
                    <div className="text-xs text-zinc-500 mt-1">영상에서 음성 복제</div>
                  </button>
                </div>
              </div>

              {/* Sample Selection */}
              {cloningMethod === "sample" && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-zinc-300 font-medium">음성 샘플 선택</span>
                    <span className="text-xs text-zinc-500">{totalSamples}개 샘플</span>
                  </div>
                  
                  <div className="space-y-2">
                    {voiceSamples.length === 0 ? (
                      <div className="text-center py-8 text-zinc-500">
                        <RefreshCw className="w-6 h-6 mx-auto mb-2 animate-spin" />
                        <p className="text-sm">샘플 로딩 중...</p>
                      </div>
                    ) : (
                      voiceSamples.map((sample) => (
                        <div
                          key={sample.voice_id}
                          className={`p-4 rounded-xl border-2 transition-all ${
                            selectedSample?.voice_id === sample.voice_id
                              ? "border-emerald-500 bg-emerald-500/10"
                              : "border-zinc-700 hover:border-zinc-500"
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            {/* Play Button */}
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                handlePlaySample(sample)
                              }}
                              disabled={sampleAudioLoading === sample.voice_id}
                              className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 transition-all ${
                                playingSampleId === sample.voice_id
                                  ? "bg-emerald-500 text-white"
                                  : "bg-zinc-700 text-zinc-300 hover:bg-zinc-600"
                              }`}
                            >
                              {sampleAudioLoading === sample.voice_id ? (
                                <RefreshCw className="w-4 h-4 animate-spin" />
                              ) : playingSampleId === sample.voice_id ? (
                                <Pause className="w-4 h-4" />
                              ) : (
                                <Play className="w-4 h-4 ml-0.5" />
                              )}
                            </button>
                            
                            {/* Sample Info */}
                            <button
                              onClick={() => setSelectedSample(sample)}
                              className="flex-1 text-left"
                            >
                              <div className={`font-medium text-sm ${
                                selectedSample?.voice_id === sample.voice_id ? "text-emerald-400" : "text-zinc-200"
                              }`}>
                                #{sample.index + 1}
                              </div>
                              <div className="text-xs text-zinc-400 line-clamp-2 mt-1">
                                {sample.prompt_text}
                              </div>
                            </button>
                            
                            {/* Selection Indicator */}
                            {selectedSample?.voice_id === sample.voice_id && (
                              <Check className="w-5 h-5 text-emerald-400 flex-shrink-0" />
                            )}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                  
                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="flex items-center justify-center gap-2 pt-2">
                      <button
                        onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                        disabled={currentPage === 1}
                        className="p-2 rounded-lg bg-zinc-800 text-zinc-300 hover:bg-zinc-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <ChevronLeft className="w-4 h-4" />
                      </button>
                      <span className="text-sm text-zinc-400 px-2">
                        {currentPage} / {totalPages}
                      </span>
                      <button
                        onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                        disabled={currentPage === totalPages}
                        className="p-2 rounded-lg bg-zinc-800 text-zinc-300 hover:bg-zinc-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <ChevronRight className="w-4 h-4" />
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* YouTube Input - IMPROVED */}
              {cloningMethod === "youtube" && (
                <div className="space-y-4">
                  {/* Guide */}
                  <div className="bg-zinc-800/50 rounded-xl p-4 border border-zinc-700">
                    <h4 className="text-sm font-medium text-zinc-200 mb-2">YouTube 음성 복제 가이드</h4>
                    <ul className="text-xs text-zinc-400 space-y-1">
                      <li>- YouTube 영상 또는 Shorts에서 음성을 복제합니다</li>
                      <li>- 10~30초 분량의 깨끗한 음성 구간을 선택해주세요</li>
                      <li>- 배경음악이 없는 구간이 좋습니다</li>
                    </ul>
                  </div>

                  {/* YouTube URL Input */}
                  <div className="space-y-2">
                    <label className="text-sm text-zinc-300 font-medium">YouTube URL</label>
                    <input
                      type="text"
                      value={youtubeUrl}
                      onChange={(e) => setYoutubeUrl(e.target.value)}
                      placeholder="https://youtube.com/watch?v=... 또는 /shorts/..."
                      className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-xl text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-emerald-500 transition-colors"
                    />
                  </div>

                  {/* Time Input - IMPROVED */}
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4 text-zinc-400" />
                      <label className="text-sm text-zinc-300 font-medium">시간 설정</label>
                    </div>
                    
                    {/* Start Time */}
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <label className="text-xs text-zinc-500">시작 시간</label>
                        <input
                          type="text"
                          value={startTime}
                          onChange={(e) => handleStartTimeChange(e.target.value)}
                          placeholder="40:51"
                          className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-xl text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-emerald-500 transition-colors text-center font-mono"
                        />
                      </div>
                      <div className="space-y-1">
                        <label className="text-xs text-zinc-500">끝 시간</label>
                        <input
                          type="text"
                          value={endTime}
                          onChange={(e) => setEndTime(e.target.value)}
                          placeholder="41:06"
                          className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-xl text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-emerald-500 transition-colors text-center font-mono"
                        />
                      </div>
                    </div>
                    
                    {/* Time Format Help */}
                    <p className="text-xs text-zinc-500">
                      형식: MM:SS (예: 40:51) 또는 HH:MM:SS (예: 1:40:51)
                    </p>
                    
                    {/* Preview of time range */}
                    {startTime && endTime && (
                      <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg px-4 py-2 text-sm text-emerald-400">
                        추출 구간: {startTime} ~ {endTime}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}

          {/* Editable Test Text (Always visible) */}
          <div className="space-y-2">
            <span className="text-sm text-zinc-300 font-medium">테스트 문장</span>
            <textarea
              value={testText}
              onChange={(e) => setTestText(e.target.value)}
              rows={3}
              className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-xl text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-emerald-500 transition-colors resize-none"
              placeholder="테스트할 문장을 입력하세요..."
            />
          </div>

          {/* Preview Audio */}
          {previewAudio && (
            <div className="bg-zinc-800/50 rounded-xl p-4 border border-zinc-700">
              <AudioPlayer audioBase64={previewAudio} voiceName="미리듣기" />
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="text-sm text-red-400 bg-red-400/10 rounded-xl p-4 border border-red-400/20">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-zinc-900 border-t border-zinc-700 px-6 py-4">
          <div className="flex gap-3">
            {activeTab === "default" && (
              <button
                onClick={handlePreview}
                disabled={isLoading}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-zinc-800 hover:bg-zinc-700 disabled:bg-zinc-800 disabled:opacity-50 rounded-xl text-zinc-100 transition-colors font-medium"
              >
                {isLoading ? (
                  <>
                    <RefreshCw className="w-5 h-5 animate-spin" />
                    <span>생성 중...</span>
                  </>
                ) : (
                  <>
                    <Volume2 className="w-5 h-5" />
                    <span>미리듣기</span>
                  </>
                )}
              </button>
            )}
            {activeTab === "cloning" && (
              <button
                onClick={handleClonePreview}
                disabled={isLoading || !canClonePreview()}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-zinc-800 hover:bg-zinc-700 disabled:bg-zinc-800 disabled:opacity-50 rounded-xl text-zinc-100 transition-colors font-medium"
              >
                {isLoading ? (
                  <>
                    <RefreshCw className="w-5 h-5 animate-spin" />
                    <span>생성 중...</span>
                  </>
                ) : (
                  <>
                    <Volume2 className="w-5 h-5" />
                    <span>미리듣기</span>
                  </>
                )}
              </button>
            )}
            <button
              onClick={handleConfirm}
              disabled={!canConfirm()}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-emerald-500 hover:bg-emerald-400 disabled:bg-zinc-700 disabled:text-zinc-500 rounded-xl text-white transition-colors font-medium shadow-lg shadow-emerald-500/20 disabled:shadow-none"
            >
              <Check className="w-5 h-5" />
              <span>확정</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
