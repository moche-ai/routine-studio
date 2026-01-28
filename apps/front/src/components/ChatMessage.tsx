import type { ChatMessage as Message } from "../types/chat"
import { useChatStore } from "../stores/chatStore"
import { useState, useEffect } from "react"
import ReactMarkdown from "react-markdown"
import rehypeRaw from "rehype-raw"
import { Download, X, Volume2, Headphones, RefreshCw, Check, Settings } from "lucide-react"
import { AudioPlayer } from "./AudioPlayer"
import { TTSSettingsModal } from "./tts/TTSSettingsModal"
import { VoiceSampleList } from "./tts/VoiceSampleList"
import { YouTubeCloneForm } from "./tts/YouTubeCloneForm"

interface Props {
  message: Message
  isLast?: boolean
}

interface SelectionOption {
  id: number
  label: string
  description?: string
}

interface QuickAction {
  label: string
  value: string
  icon?: "volume" | "headphones" | "refresh" | "check"
  variant?: "primary" | "secondary"
}

interface AudioData {
  audio_base64: string
  voice_name?: string
  duration?: number
  text?: string
}

// 메시지에서 퀵 액션 추출
function extractQuickActions(content: string, step?: string): QuickAction[] {
  const actions: QuickAction[] = []

  // ========== 채널명 설문/선택 관련 ==========
  if (content.includes("더 추천해줘") || content.includes("새로운 10개")) {
    actions.push({ label: "더 추천해줘", value: "더 추천해줘" })
  }
  if (content.includes("좀 더 짧게") || content.includes("짧은 이름")) {
    actions.push({ label: "짧게", value: "좀 더 짧게" })
  }
  if (content.includes("언어 변경")) {
    actions.push({ label: "영어로", value: "영어로" })
  }

  if (content.includes("채널명이 확정되었습니다") && content.includes("다음 단계로 진행")) {
    actions.push({ label: "다음 단계", value: "확인" })
  }

  // ========== 벤치마킹 관련 ==========
  if (content.includes("맞으면") && (content.includes("확인") || content.includes("맞아"))) {
    actions.push({ label: "확인", value: "확인" })
  }

  if (content.includes("분석을 시작하려면") || content.includes("분석 시작") ||
      (content.includes("시작") && content.includes("\"시작\""))) {
    actions.push({ label: "분석 시작", value: "시작" })
  }

  if (content.includes("추가하려면") && content.includes("확인")) {
    if (!actions.some(a => a.label === "확인")) {
      actions.push({ label: "확인", value: "확인" })
    }
  }

  if (content.includes("다음 단계로 진행하려면") || content.includes("리포트 확인 완료")) {
    if (!actions.some(a => a.label === "다음 단계")) {
      actions.push({ label: "다음 단계", value: "다음" })
    }
  }

  if (content.includes("스킵") || content.includes("건너뛰")) {
    actions.push({ label: "스킵", value: "스킵" })
  }

  if (content.includes("이미 벤치마킹된") || content.includes("기존 결과를 사용")) {
    actions.push({ label: "기존 결과 사용", value: "확인" })
    actions.push({ label: "다시 분석", value: "다시 분석" })
  }

  if (content.includes("추가로 분석할 채널") || content.includes("더 추가하려면")) {
    if (!actions.some(a => a.label === "분석 시작")) {
      actions.push({ label: "분석 시작", value: "시작" })
    }
  }

  // ========== 캐릭터 관련 ==========
  // 캐릭터 이미지 확정 전 (캐릭터 생성 결과 표시 또는 미리보기)
  if (step === "character" || step === "character_confirmed" || step === "character_preview") {
    if (content.includes("캐릭터를 만났어요") || content.includes("캐릭터가 생성") || content.includes("캐릭터 이미지") || content.includes("캐릭터로 확정할까요")) {
      actions.push({ label: "변경", value: "다른 캐릭터", icon: "refresh", variant: "secondary" })
      actions.push({ label: "확정", value: "확정", icon: "check", variant: "primary" })
    }
  }
  
  // 캐릭터 확정 후 다음 단계
  if (content.includes("다음 단계로 진행하려면 아무 메시지")) {
    if (!actions.some(a => a.label === "다음 단계")) {
      actions.push({ label: "다음 단계", value: "확인" })
    }
  }

  // ========== 대본 관련 ==========
  if (content.includes("확정을 입력하면 완료") || content.includes("확정\"을 입력하면")) {
    actions.push({ label: "확정", value: "확정" })
  }

  // ========== 보이스오버/TTS 관련 ==========
  if (content.includes("기본 보이스") && content.includes("보이스 클로닝") && content.includes("1.") && content.includes("2.")) {
    actions.push({ label: "기본 보이스", value: "1" })
    actions.push({ label: "보이스 클로닝", value: "2" })
  }

  if (content.includes("YouTube 영상에서 추출") && content.includes("저장된 샘플")) {
    actions.push({ label: "YouTube 클로닝", value: "1" })
    actions.push({ label: "샘플 보이스", value: "2" })
  }

  if (content.includes("생성을 입력하면") || content.includes("생성을 시작합니다")) {
    actions.push({ label: "생성", value: "생성" })
  }

  // ========== 이미지 생성 관련 ==========
  if (content.includes("이미지 생성을 시작") || content.includes("생성하시겠습니까")) {
    if (!actions.some(a => a.value === "생성")) {
      actions.push({ label: "생성 시작", value: "생성" })
    }
  }

  // ========== 컴포저 관련 ==========
  if (content.includes("영상 합성") && content.includes("시작")) {
    if (!actions.some(a => a.value === "시작")) {
      actions.push({ label: "합성 시작", value: "시작" })
    }
  }

  // ========== TTS 미리듣기 관련 ==========
  if (content.includes("미리듣기") || content.includes("들어보세요")) {
    actions.push({ label: "미리듣기", value: "미리듣기", icon: "volume" })
  }

  return actions
}

export function ChatMessage({ message, isLast = false }: Props) {
  const { sendMessage, sendInlineMessage, isLoading } = useChatStore()
  const [enlargedImage, setEnlargedImage] = useState<string | null>(null)
  const [ttsModalOpen, setTtsModalOpen] = useState(false)
  const isAgent = message.role === "assistant" || message.role === "agent"

  const timestamp = message.timestamp instanceof Date
    ? message.timestamp
    : new Date(message.timestamp)

  const options: SelectionOption[] = (message.metadata?.data?.options as SelectionOption[]) || []
  const isSelection = message.metadata?.data?.type === "selection"
  const isTTSSettingsPanel = message.metadata?.data?.show_panel === "tts_settings_panel"
  const isVoiceSampleList = message.metadata?.data?.type === "voice_sample_list"
  const isYouTubeCloneForm = message.metadata?.data?.type === "youtube_clone_form"
  
  // Audio data from message metadata
  const audioData: AudioData | undefined = message.metadata?.data?.audio as AudioData | undefined
  const audioSamples: AudioData[] | undefined = message.metadata?.data?.audio_samples as AudioData[] | undefined
  
  // Step from metadata
  const stepName = message.metadata?.step as string | undefined

  // TTS 설정 패널이면 자동으로 모달 열기
  useEffect(() => {
    if (isTTSSettingsPanel && isLast && !isLoading) {
      setTtsModalOpen(true)
    }
  }, [isTTSSettingsPanel, isLast, isLoading])

  // 퀵 액션 추출 (마지막 에이전트 메시지이고 로딩 중이 아닐 때만)
  const quickActions = isAgent && isLast && !isLoading && message.content
    ? extractQuickActions(message.content, stepName)
    : []

  // TTS 관련 단계인지 확인
  const isTTSStep = stepName === "tts_settings" || stepName?.startsWith("tts_")
  
  const handleOptionClick = (option: SelectionOption) => {
    if (!isLoading) {
      if (isTTSStep) {
        // TTS 단계에서는 인라인 업데이트 (말풍선 교체)
        sendInlineMessage(String(option.id))
      } else {
        // 일반 단계에서는 새 메시지
        sendMessage(String(option.id), [])
      }
    }
  }

  const handleQuickAction = (action: QuickAction) => {
    if (!isLoading) {
      sendMessage(action.value, [])
    }
  }

  const handleImageClick = (imgSrc: string) => {
    if (imgSrc.startsWith("data:") || imgSrc.startsWith("blob:")) {
      setEnlargedImage(imgSrc)
    } else {
      window.open(imgSrc, "_blank")
    }
  }

  const handleDownload = (imgSrc: string, index: number) => {
    const link = document.createElement("a")
    link.href = imgSrc
    link.download = "character_" + Date.now() + "_" + index + ".png"
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const handleTTSConfirm = (settings: { type?: string; speed?: number; pitch?: number; instruct?: string; text?: string; sampleId?: string; youtubeUrl?: string; timeRange?: string }) => {
    setTtsModalOpen(false)
    sendMessage(JSON.stringify(settings), [])
  }

  const handleTTSClose = () => {
    setTtsModalOpen(false)
    sendMessage("취소", [])
  }

  const msgIsAgent = isAgent

  // Render icon for quick action
  const renderActionIcon = (icon?: string) => {
    if (icon === "volume") return <Volume2 className="h-4 w-4 mr-1.5" />
    if (icon === "headphones") return <Headphones className="h-4 w-4 mr-1.5" />
    if (icon === "refresh") return <RefreshCw className="h-4 w-4 mr-1.5" />
    if (icon === "check") return <Check className="h-4 w-4 mr-1.5" />
    return null
  }

  // Get button style based on variant
  const getButtonStyle = (variant?: string) => {
    if (variant === "secondary") {
      return "bg-zinc-700 hover:bg-zinc-600 text-zinc-200"
    }
    return "bg-emerald-600 hover:bg-emerald-500 text-white"
  }

  return (
    <>
      <div className={`flex ${msgIsAgent ? "justify-start" : "justify-end"} mb-4`}>
        <div className="flex flex-col max-w-[85%]">
          <div className={`overflow-hidden ${msgIsAgent ? "bg-zinc-800" : "bg-emerald-600"} rounded-2xl px-4 py-3`}>
            {msgIsAgent && stepName && (
              <div className="mb-2">
                <span className="text-sm font-medium text-white">Routine</span>
                <span className="text-xs text-zinc-500 ml-2">#{stepName} agent</span>
              </div>
            )}

            {message.images && message.images.length > 0 && (
              <div className="space-y-3 mb-3">
                {message.images.map((img, idx) => (
                  <div key={idx} className="relative group">
                    <img
                      src={img}
                      alt={"attachment-" + idx}
                      className="w-full max-w-[500px] rounded-lg cursor-pointer hover:opacity-90 border border-zinc-700 transition-opacity"
                      onClick={() => handleImageClick(img)}
                    />
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDownload(img, idx)
                      }}
                      className="absolute top-2 right-2 p-2 bg-black/60 hover:bg-black/80 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity"
                      title="다운로드"
                    >
                      <Download className="h-5 w-5 text-white" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {message.content && (
              <div className="text-white leading-relaxed break-words [word-break:break-all] prose prose-invert prose-sm max-w-none prose-p:my-2 prose-p:leading-relaxed prose-strong:text-emerald-300 prose-strong:font-semibold prose-ul:my-2 prose-ul:pl-4 prose-ol:my-2 prose-ol:pl-4 prose-li:my-0.5 prose-code:bg-zinc-700 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-emerald-400 prose-a:text-emerald-400 prose-a:underline prose-hr:border-zinc-600 prose-hr:my-3 prose-headings:text-white prose-headings:font-bold prose-table:hidden">
                <ReactMarkdown rehypePlugins={[rehypeRaw]}>{message.content}</ReactMarkdown>
              </div>
            )}

            {/* Single audio player */}
            {audioData && audioData.audio_base64 && (
              <div className="mt-3">
                <AudioPlayer
                  audioBase64={audioData.audio_base64}
                  voiceName={audioData.voice_name || "Audio"}
                  duration={audioData.duration}
                />
                {audioData.text && (
                  <p className="text-xs text-zinc-400 mt-1 italic">"{audioData.text}"</p>
                )}
              </div>
            )}

            {/* Multiple audio samples */}
            {audioSamples && audioSamples.length > 0 && (
              <div className="mt-3 space-y-2">
                <div className="flex items-center gap-1 text-xs text-zinc-400 mb-2">
                  <Headphones className="h-3.5 w-3.5" />
                  <span>음성 샘플:</span>
                </div>
                {audioSamples.map((sample, idx) => (
                  <div key={idx}>
                    <AudioPlayer
                      audioBase64={sample.audio_base64}
                      voiceName={sample.voice_name || `Sample ${idx + 1}`}
                      duration={sample.duration}
                    />
                    {sample.text && (
                      <p className="text-xs text-zinc-500 mt-0.5 ml-2 italic">"{sample.text}"</p>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* TTS Settings - 모달로 이동, 버튼만 표시 */}
            {msgIsAgent && isTTSSettingsPanel && isLast && (
              <div className="mt-3">
                <button
                  onClick={() => setTtsModalOpen(true)}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/50 rounded-xl text-emerald-400 transition-colors"
                >
                  <Settings className="w-5 h-5" />
                  <span className="font-medium">음성 설정 열기</span>
                </button>
              </div>
            )}

            {/* Voice Sample List */}
            {msgIsAgent && isVoiceSampleList && isLast && (
              <div className="mt-3">
                <VoiceSampleList
                  onSelect={(voiceId, audioBase64, promptText) => {
                    // Send selection as JSON to backend
                    sendMessage(JSON.stringify({
                      type: "sample_selected",
                      voice_id: voiceId,
                      audio_base64: audioBase64,
                      prompt_text: promptText
                    }), [])
                  }}
                  onCancel={() => sendMessage("취소", [])}
                />
              </div>
            )}

            {/* YouTube Clone Form */}
            {msgIsAgent && isYouTubeCloneForm && isLast && (
              <div className="mt-3">
                <YouTubeCloneForm
                  onExtracted={(audioBase64, refText, duration) => {
                    // Send extracted audio as JSON to backend
                    sendMessage(JSON.stringify({
                      type: "youtube_extracted",
                      audio_base64: audioBase64,
                      ref_text: refText,
                      duration: duration
                    }), [])
                  }}
                  onCancel={() => sendMessage("취소", [])}
                />
              </div>
            )}
            {msgIsAgent && isSelection && options.length > 0 && (
              <div className="mt-3 space-y-2">
                {options.map((option) => (
                  <button
                    key={option.id}
                    onClick={() => handleOptionClick(option)}
                    disabled={isLoading}
                    className="w-full text-left px-3 py-2 bg-zinc-700 hover:bg-zinc-600 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed group"
                  >
                    <div className="flex items-center gap-2">
                      <span className="w-6 h-6 flex items-center justify-center bg-emerald-500 text-white text-sm font-bold rounded-full group-hover:bg-emerald-400">
                        {option.id}
                      </span>
                      <span className="font-medium">{option.label}</span>
                    </div>
                    {option.description && (
                      <p className="text-xs text-zinc-400 mt-1 ml-8">{option.description}</p>
                    )}
                  </button>
                ))}
              </div>
            )}

            <span className="text-xs text-zinc-500 mt-2 block text-right">
              {timestamp.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })}
            </span>
          </div>

          {/* 퀵 액션 버튼 */}
          {quickActions.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-2 ml-1">
              {quickActions.map((action, idx) => (
                <button
                  key={idx}
                  onClick={() => handleQuickAction(action)}
                  disabled={isLoading}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center ${getButtonStyle(action.variant)}`}
                >
                  {renderActionIcon(action.icon)}
                  {action.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* TTS Settings Modal */}
      <TTSSettingsModal
        isOpen={ttsModalOpen}
        channelName={message.metadata?.data?.channel_name as string || "채널"}
        defaultText={message.metadata?.data?.default_text as string}
        onConfirm={handleTTSConfirm}
        onClose={handleTTSClose}
      />

      {enlargedImage && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4"
          onClick={() => setEnlargedImage(null)}
        >
          <div className="relative max-w-[90vw] max-h-[90vh]">
            <img
              src={enlargedImage}
              alt="enlarged"
              className="max-w-full max-h-[90vh] object-contain rounded-lg"
            />
            <button
              onClick={() => setEnlargedImage(null)}
              className="absolute top-2 right-2 p-2 bg-black/60 hover:bg-black/80 rounded-full"
            >
              <X className="h-6 w-6 text-white" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation()
                handleDownload(enlargedImage, 0)
              }}
              className="absolute bottom-4 right-4 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg flex items-center gap-2 text-white"
            >
              <Download className="h-5 w-5" />
              다운로드
            </button>
          </div>
        </div>
      )}
    </>
  )
}
