import { useEffect, useRef, useState } from 'react'
import { Bot, MessageSquare, Wallet, Rocket, Code, Leaf, ChevronDown, ChevronUp, Check } from 'lucide-react'
import { ChatInput } from '../components/ChatInput'
import { ChatMessage } from '../components/ChatMessage'
import { useChatStore } from '../stores/chatStore'

// 워크플로우 단계 정의
const WORKFLOW_STEPS = [
  { key: "channel_name", label: "채널명", short: "1" },
  { key: "benchmarking", label: "벤치마킹", short: "2" },
  { key: "character", label: "캐릭터", short: "3" },
  { key: "tts_settings", label: "음성", short: "4" },
  { key: "logo", label: "브랜딩", short: "5" },
]

const STEP_LABELS: Record<string, string> = {
  idle: '대기중',
  channel_name: '채널명 생성',
  benchmarking: '채널 벤치마킹',
  character: '캐릭터 생성',
  character_confirmed: '캐릭터 확정',
  tts_settings: '음성 설정',
  logo: '브랜딩 생성',
  logo_review: '브랜딩 선택',
  video_ideas: '영상 아이디어',
  script: '대본 작성',
  image_prompt: '이미지 프롬프트',
  image_generate: '이미지 생성',
  voiceover: '보이스오버',
  compose: '영상 합성',
  completed: '완료',
  channel_saved: '채널 저장 완료',
  channel_save_error: '저장 실패'
}

// 단계 상태 계산
function getStepStatus(stepKey: string, currentStep: string): "completed" | "current" | "pending" {
  const stepIndex = WORKFLOW_STEPS.findIndex(s => s.key === currentStep || currentStep.startsWith(s.key))
  const thisIndex = WORKFLOW_STEPS.findIndex(s => s.key === stepKey)

  if (thisIndex < stepIndex) return "completed"
  if (thisIndex === stepIndex) return "current"
  return "pending"
}

// 프로그레스 바 컴포넌트
function WorkflowProgress({ currentStep }: { currentStep: string }) {
  if (currentStep === "idle" || currentStep === "completed") return null

  return (
    <div className="flex items-center gap-1">
      {WORKFLOW_STEPS.map((step, idx) => {
        const status = getStepStatus(step.key, currentStep)
        const isLast = idx === WORKFLOW_STEPS.length - 1

        return (
          <div key={step.key} className="flex items-center">
            {/* 단계 아이콘 */}
            <div className="relative group">
              {status === "completed" ? (
                <div className="w-6 h-6 rounded-full bg-emerald-500 flex items-center justify-center">
                  <Check className="w-3.5 h-3.5 text-white" />
                </div>
              ) : status === "current" ? (
                <div className="w-6 h-6 rounded-full bg-emerald-500 flex items-center justify-center animate-pulse">
                  <span className="text-[10px] font-bold text-white">{step.short}</span>
                </div>
              ) : (
                <div className="w-6 h-6 rounded-full bg-zinc-700 flex items-center justify-center">
                  <span className="text-[10px] text-zinc-400">{step.short}</span>
                </div>
              )}

              {/* 툴팁 */}
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-zinc-800 text-xs text-white rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
                {step.label}
                {status === "current" && " (진행중)"}
                {status === "completed" && " ✓"}
              </div>
            </div>

            {/* 연결선 */}
            {!isLast && (
              <div className={`w-3 h-0.5 ${
                status === "completed" ? "bg-emerald-500" : "bg-zinc-700"
              }`} />
            )}
          </div>
        )
      })}
    </div>
  )
}

export function ChannelChatPage() {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const progressEndRef = useRef<HTMLDivElement>(null)
  const [progressExpanded, setProgressExpanded] = useState(false)

  const {
    isLoading,
    progressLog,
    currentConversationId,
    getMessages,
    getCurrentStep,
    sendMessage,
    createConversation
  } = useChatStore()

  const messages = getMessages()
  const currentStep = getCurrentStep()

  // 대화가 없으면 새로 생성
  useEffect(() => {
    if (!currentConversationId) {
      createConversation()
    }
  }, [currentConversationId, createConversation])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isLoading, progressLog])

  useEffect(() => {
    progressEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [progressLog])

  const handleSend = async (content: string, images: string[]) => {
    await sendMessage(content, images)
  }

  const handleQuickStart = (topic: string) => {
    handleSend(topic, [])
  }

  const noMessages = messages.length === 0
  const stepLabel = STEP_LABELS[currentStep] || currentStep
  const showProgress = currentStep !== 'idle' && currentStep !== 'completed'
  const latestProgress = progressLog.length > 0 ? progressLog[progressLog.length - 1] : null
  const hasMultipleProgress = progressLog.length > 1

  return (
    <div className="h-full flex flex-col bg-zinc-900">
      {/* Header - Responsive */}
      <header className="flex items-center justify-between p-3 sm:p-4 border-b border-zinc-800">
        <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1">
          <div className="w-8 h-8 sm:w-10 sm:h-10 bg-gradient-to-br from-emerald-500 to-emerald-700 rounded-full flex items-center justify-center flex-shrink-0">
            <Bot className="w-4 h-4 sm:w-6 sm:h-6 text-white" />
          </div>
          <div className="min-w-0 flex-1">
            <h1 className="font-semibold text-white text-sm sm:text-base truncate">채널 기획 어시스턴트</h1>
            {showProgress ? (
              <div className="flex items-center gap-2 mt-0.5 sm:mt-1">
                <div className="hidden sm:flex">
                  <WorkflowProgress currentStep={currentStep} />
                </div>
                <span className="text-xs text-emerald-400 truncate">{stepLabel}</span>
              </div>
            ) : (
              <p className="text-xs sm:text-sm text-zinc-400 truncate">{stepLabel}</p>
            )}
          </div>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4">
        {noMessages ? (
          <div className="flex flex-col items-center justify-center h-full text-zinc-500">
            <MessageSquare className="w-16 h-16 mb-4 text-zinc-600" />
            <p className="text-lg mb-2 text-white">유튜브 채널 기획을 시작해보세요</p>
            <p className="text-sm text-center max-w-md text-zinc-500">
              어떤 주제의 채널을 만들고 싶은지 알려주세요.
            </p>
            <div className="mt-6 grid grid-cols-2 gap-2">
              <button
                onClick={() => handleQuickStart('경제/투자 교육 채널을 만들고 싶어요')}
                className="px-4 py-2 text-sm bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors flex items-center gap-2"
              >
                <Wallet className="w-4 h-4 text-emerald-400" />
                경제/투자 채널
              </button>
              <button
                onClick={() => handleQuickStart('자기계발/동기부여 채널을 만들고 싶어요')}
                className="px-4 py-2 text-sm bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors flex items-center gap-2"
              >
                <Rocket className="w-4 h-4 text-emerald-400" />
                자기계발 채널
              </button>
              <button
                onClick={() => handleQuickStart('테크/프로그래밍 교육 채널을 만들고 싶어요')}
                className="px-4 py-2 text-sm bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors flex items-center gap-2"
              >
                <Code className="w-4 h-4 text-emerald-400" />
                테크 채널
              </button>
              <button
                onClick={() => handleQuickStart('라이프스타일/미니멀리즘 채널을 만들고 싶어요')}
                className="px-4 py-2 text-sm bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors flex items-center gap-2"
              >
                <Leaf className="w-4 h-4 text-emerald-400" />
                라이프스타일 채널
              </button>
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, index) => (
              <ChatMessage
                key={msg.id}
                message={msg}
                isLast={index === messages.length - 1 && !isLoading}
              />
            ))}

            {isLoading && (
              <div className="flex justify-start mb-4">
                <div className="bg-zinc-800 rounded-2xl px-4 py-3 max-w-[85%]">
                  {latestProgress ? (
                    <div>
                      {/* 최신 진행 상황 */}
                      <div className="flex items-center gap-2 mb-2">
                        <div className="flex gap-1">
                          <span className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" />
                          <span className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce [animation-delay:0.1s]" />
                          <span className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce [animation-delay:0.2s]" />
                        </div>
                        <span className="text-sm text-emerald-400 font-medium">{latestProgress.status}</span>
                      </div>
                      <p className="text-sm text-zinc-400">{latestProgress.detail}</p>

                      {/* 이전 진행 기록 */}
                      {hasMultipleProgress && (
                        <div className="mt-2">
                          <button
                            onClick={() => setProgressExpanded(!progressExpanded)}
                            className="flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-400"
                          >
                            {progressExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                            이전 단계 {progressLog.length - 1}개
                          </button>
                          {progressExpanded && (
                            <div className="mt-2 space-y-1 max-h-32 overflow-y-auto">
                              {progressLog.slice(0, -1).map((p, i) => (
                                <div key={i} className="text-xs text-zinc-500">
                                  <span className="text-zinc-400">{p.status}:</span> {p.detail}
                                </div>
                              ))}
                              <div ref={progressEndRef} />
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <div className="flex gap-1">
                        <span className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" />
                        <span className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce [animation-delay:0.1s]" />
                        <span className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce [animation-delay:0.2s]" />
                      </div>
                      <span className="text-sm text-zinc-400">생각 중...</span>
                    </div>
                  )}
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input */}
      <ChatInput onSend={handleSend} disabled={isLoading} />
    </div>
  )
}
