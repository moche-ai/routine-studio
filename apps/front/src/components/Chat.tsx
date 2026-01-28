import { useEffect, useRef, useState } from "react"
import { useChatStore } from "../stores/chatStore"
import { ChatMessage } from "./ChatMessage"
import { ChatInput } from "./ChatInput"
import { AgentStatus } from "./AgentStatus"
import { Sidebar } from "./Sidebar"
import { Bot, MessageSquare, Check, Wallet, Rocket, Code, Leaf, ChevronDown, ChevronUp } from "lucide-react"

// 워크플로우 단계 정의 (6번, 7번 제거)
const WORKFLOW_STEPS = [
  { key: "channel_name", label: "채널명", short: "1" },
  { key: "benchmarking", label: "벤치마킹", short: "2" },
  { key: "character", label: "캐릭터", short: "3" },
  { key: "tts_settings", label: "음성", short: "4" },
  { key: "logo", label: "브랜딩", short: "5" },
]

// 단계 상태 계산
function getStepStatus(stepKey: string, currentStep: string): "completed" | "current" | "pending" {
  const stepIndex = WORKFLOW_STEPS.findIndex(s => s.key === currentStep || currentStep.startsWith(s.key))
  const thisIndex = WORKFLOW_STEPS.findIndex(s => s.key === stepKey)

  if (thisIndex < stepIndex) return "completed"
  if (thisIndex === stepIndex) return "current"
  return "pending"
}

// 프로그레스 바 컴포넌트
function WorkflowProgress({ 
  currentStep,
  onStepClick 
}: { 
  currentStep: string
  onStepClick?: (stepKey: string) => void 
}) {
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
                <button
                  onClick={() => onStepClick?.(step.key)}
                  className="w-6 h-6 rounded-full bg-emerald-500 flex items-center justify-center hover:bg-emerald-400 hover:scale-110 transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-emerald-300 focus:ring-offset-2 focus:ring-offset-zinc-900"
                  title={`${step.label}로 돌아가기`}
                >
                  <Check className="w-3.5 h-3.5 text-white" />
                </button>
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
                {status === "completed" && " - 클릭하여 돌아가기"}
              </div>
            </div>

            {/* 연결선 */}
            {!isLast && (
              <div className={`w-4 h-0.5 ${
                status === "completed" ? "bg-emerald-500" : "bg-zinc-700"
              }`} />
            )}
          </div>
        )
      })}
    </div>
  )
}

const STEP_LABELS: Record<string, string> = {
  idle: "대기중",
  channel_name: "채널명 생성",
  benchmarking: "채널 벤치마킹",
  character: "캐릭터 생성",
  character_confirmed: "캐릭터 확정",
  tts_settings: "음성 설정",
  logo: "브랜딩 생성",
  logo_review: "브랜딩 선택",
  video_ideas: "영상 아이디어",
  script: "대본 작성",
  image_prompt: "이미지 프롬프트",
  image_generate: "이미지 생성",
  voiceover: "보이스오버",
  compose: "영상 합성",
  completed: "완료"
}

export function Chat() {
  const {
    conversations,
    currentConversationId,
    isLoading,
    sidebarCollapsed,
    progressLog,
    currentStatus,
    getMessages,
    getCurrentStep,
    getSessionId,
    sendMessage,
    createConversation,
    selectConversation,
    deleteConversation,
    clearCurrentConversation,
    setSidebarCollapsed
  } = useChatStore()

  const messages = getMessages()
  const currentStep = getCurrentStep()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const progressEndRef = useRef<HTMLDivElement>(null)
  const [progressExpanded, setProgressExpanded] = useState(false)
  const [animateLatest, setAnimateLatest] = useState(false)
  const prevProgressCountRef = useRef(0)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isLoading, progressLog])

  useEffect(() => {
    progressEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [progressLog])

  useEffect(() => {
    if (progressLog.length > prevProgressCountRef.current) {
      setAnimateLatest(true)
      const timer = setTimeout(() => setAnimateLatest(false), 500)
      return () => clearTimeout(timer)
    }
    prevProgressCountRef.current = progressLog.length
  }, [progressLog.length])

  const handleSend = async (content: string, images: string[]) => {
    await sendMessage(content, images)
  }

  const handleGoToStep = async (stepKey: string) => {
    const sessionId = getSessionId()
    console.log("[GoToStep] Clicked:", stepKey, "sessionId:", sessionId, "isLoading:", isLoading)
    
    if (!sessionId) {
      console.warn("[GoToStep] No active session, ignoring click")
      return
    }
    if (isLoading) {
      console.warn("[GoToStep] Loading in progress, ignoring click")
      return
    }
    
    console.log("[GoToStep] Sending message:", stepKey + " 다시")
    await sendMessage(`${stepKey} 다시`, [])
    console.log("[GoToStep] Message sent")
  }

  const handleNewConversation = () => {
    createConversation()
  }

  const conversationList = conversations.map(c => ({
    id: c.id,
    title: c.title,
    step: c.currentStep,
    updatedAt: new Date(c.updatedAt)
  }))

  const noMessages = messages.length === 0
  const hasMessages = messages.length > 0
  const stepLabel = STEP_LABELS[currentStep] || currentStep
  const showProgress = currentStep !== "idle" && currentStep !== "completed"

  const latestProgress = progressLog.length > 0 ? progressLog[progressLog.length - 1] : null
  const hasMultipleProgress = progressLog.length > 1

  return (
    <div className="flex h-screen bg-zinc-900">
      <style>{`
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(-8px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes pulse-glow {
          0%, 100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
          50% { box-shadow: 0 0 8px 2px rgba(16, 185, 129, 0.3); }
        }
        .animate-fade-slide-in { animation: fadeSlideIn 0.4s ease-out forwards; }
        .animate-pulse-glow { animation: pulse-glow 0.6s ease-in-out; }
      `}</style>

      <Sidebar
        conversations={conversationList}
        currentId={currentConversationId}
        onSelect={selectConversation}
        onNew={handleNewConversation}
        onDelete={deleteConversation}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />

      <div className="flex-1 flex flex-col">
        {/* 헤더 - 중앙 정렬 */}
        <header className="border-b border-zinc-800">
          <div className="max-w-4xl mx-auto w-full flex items-center justify-between p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-emerald-500 to-emerald-700 rounded-full flex items-center justify-center">
                <Bot className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="font-semibold text-white">채널 기획 어시스턴트</h1>
                {showProgress ? (
                  <div className="flex items-center gap-2 mt-1">
                    <WorkflowProgress currentStep={currentStep} onStepClick={handleGoToStep} />
                    <span className="text-xs text-emerald-400">{stepLabel}</span>
                  </div>
                ) : (
                  <p className="text-sm text-zinc-400">{stepLabel}</p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {hasMessages && (
                <button
                  onClick={clearCurrentConversation}
                  className="text-sm text-zinc-500 hover:text-zinc-300 px-3 py-1 rounded hover:bg-zinc-800 transition-colors"
                >
                  초기화
                </button>
              )}
            </div>
          </div>
        </header>

        {/* 메시지 영역 - 중앙 정렬 */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-4xl mx-auto w-full p-4">
            {noMessages ? (
              <div className="flex flex-col items-center justify-center h-full min-h-[60vh] text-zinc-500">
                <MessageSquare className="w-16 h-16 mb-4 text-zinc-600" />
                <p className="text-lg mb-2 text-white">유튜브 채널 기획을 시작해보세요</p>
                <p className="text-sm text-center max-w-md">
                  어떤 주제의 채널을 만들고 싶은지 알려주세요.<br/>
                  예: 경제/투자 관련 교육 채널을 만들고 싶어요
                </p>
                <div className="mt-6 grid grid-cols-2 gap-2">
                  <button
                    onClick={() => handleSend("경제/투자 교육 채널을 만들고 싶어요", [])}
                    className="px-4 py-2 text-sm bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors flex items-center gap-2"
                  >
                    <Wallet className="w-4 h-4 text-emerald-400" />
                    경제/투자 채널
                  </button>
                  <button
                    onClick={() => handleSend("자기계발/동기부여 채널을 만들고 싶어요", [])}
                    className="px-4 py-2 text-sm bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors flex items-center gap-2"
                  >
                    <Rocket className="w-4 h-4 text-emerald-400" />
                    자기계발 채널
                  </button>
                  <button
                    onClick={() => handleSend("테크/프로그래밍 교육 채널을 만들고 싶어요", [])}
                    className="px-4 py-2 text-sm bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors flex items-center gap-2"
                  >
                    <Code className="w-4 h-4 text-emerald-400" />
                    테크 채널
                  </button>
                  <button
                    onClick={() => handleSend("라이프스타일/미니멀리즘 채널을 만들고 싶어요", [])}
                    className="px-4 py-2 text-sm bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors flex items-center gap-2"
                  >
                    <Leaf className="w-4 h-4 text-emerald-400" />
                    라이프스타일 채널
                  </button>
                </div>
              </div>
            ) : (
              <>
                <AgentStatus currentStep={currentStep} isLoading={isLoading} />

                {messages.map((msg, idx) => (
                  <ChatMessage
                    key={msg.id}
                    message={msg}
                    isLast={idx === messages.length - 1}
                  />
                ))}

                {isLoading && (
                  <div className="flex justify-start mb-4">
                    <div className="bg-zinc-800 rounded-2xl px-4 py-3 max-w-[85%]">
                      <div className="flex items-center gap-2 mb-3">
                        <div className="flex gap-1">
                          <span className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" />
                          <span className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" style={{animationDelay: "0.1s"}} />
                          <span className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" style={{animationDelay: "0.2s"}} />
                        </div>
                        <span className="text-sm text-emerald-400 font-medium">
                          {currentStatus || "처리 중..."}
                        </span>
                      </div>

                      {progressLog.length > 0 && (
                        <div className="border-t border-zinc-700 pt-2 mt-2">
                          <button
                            onClick={() => setProgressExpanded(!progressExpanded)}
                            className="flex items-center justify-between w-full text-xs text-zinc-500 mb-2 hover:text-zinc-400 transition-colors"
                          >
                            <span>진행 기록 ({progressLog.length})</span>
                            {hasMultipleProgress && (
                              progressExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />
                            )}
                          </button>

                          {!progressExpanded && latestProgress && (
                            <div className={`flex items-start gap-2 text-xs rounded px-1 py-0.5 -mx-1 ${animateLatest ? 'animate-fade-slide-in animate-pulse-glow' : ''}`}>
                              <span className="text-zinc-600 whitespace-nowrap">
                                {new Date(latestProgress.timestamp).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                              </span>
                              <Check className={`w-3 h-3 mt-0.5 flex-shrink-0 transition-colors ${animateLatest ? 'text-emerald-300' : 'text-emerald-400'}`} />
                              <span className={`transition-colors ${animateLatest ? 'text-white' : 'text-zinc-300'}`}>{latestProgress.status}</span>
                              {latestProgress.detail && <span className="text-zinc-500 truncate max-w-[200px]">- {latestProgress.detail}</span>}
                            </div>
                          )}

                          {progressExpanded && (
                            <div className="space-y-1 max-h-40 overflow-y-auto">
                              {progressLog.map((item, idx) => (
                                <div key={idx} className={`flex items-start gap-2 text-xs rounded px-1 py-0.5 -mx-1 ${idx === progressLog.length - 1 && animateLatest ? 'animate-fade-slide-in animate-pulse-glow' : ''}`}>
                                  <span className="text-zinc-600 whitespace-nowrap">
                                    {new Date(item.timestamp).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                                  </span>
                                  <Check className={`w-3 h-3 mt-0.5 flex-shrink-0 ${idx === progressLog.length - 1 && animateLatest ? 'text-emerald-300' : 'text-emerald-400'}`} />
                                  <span className={idx === progressLog.length - 1 && animateLatest ? 'text-white' : 'text-zinc-300'}>{item.status}</span>
                                  {item.detail && <span className="text-zinc-500">- {item.detail}</span>}
                                </div>
                              ))}
                              <div ref={progressEndRef} />
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </>
            )}
          </div>
        </div>

        {/* 입력 영역 - 중앙 정렬 */}
        <div className="border-t border-zinc-800">
          <div className="max-w-4xl mx-auto w-full">
            <ChatInput onSend={handleSend} disabled={isLoading} />
          </div>
        </div>
      </div>
    </div>
  )
}
