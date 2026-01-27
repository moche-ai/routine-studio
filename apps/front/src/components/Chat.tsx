import { useEffect, useRef, useState } from "react"
import { useChatStore } from "../stores/chatStore"
import { ChatMessage } from "./ChatMessage"
import { ChatInput } from "./ChatInput"
import { AgentStatus } from "./AgentStatus"
import { Sidebar } from "./Sidebar"
import { Bot, MessageSquare, Check, Wallet, Rocket, Code, Leaf, ChevronDown, ChevronUp } from "lucide-react"

const STEP_LABELS: Record<string, string> = {
  idle: "대기중",
  channel_name: "1단계: 채널명 생성",
  benchmarking: "2단계: 채널 벤치마킹",
  character: "3단계: 캐릭터 생성",
  character_confirmed: "3단계: 캐릭터 확정",
  tts_settings: "4단계: 음성 설정",
  logo: "5단계: 브랜딩 생성",
  logo_review: "5단계: 브랜딩 선택",
  video_ideas: "6단계: 영상 아이디어",
  script: "7단계: 대본 작성",
  image_prompt: "8단계: 이미지 프롬프트",
  image_generate: "9단계: 이미지 생성",
  voiceover: "10단계: 보이스오버",
  compose: "11단계: 영상 합성",
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

  // 새 진행 항목 추가시 애니메이션 트리거
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
  const showStepBadge = currentStep !== "idle" && currentStep !== "completed"

  // 최신 진행 기록 가져오기
  const latestProgress = progressLog.length > 0 ? progressLog[progressLog.length - 1] : null
  const hasMultipleProgress = progressLog.length > 1

  return (
    <div className="flex h-screen bg-zinc-900">
      {/* 애니메이션 스타일 */}
      <style>{`
        @keyframes fadeSlideIn {
          from {
            opacity: 0;
            transform: translateY(-8px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        @keyframes pulse-glow {
          0%, 100% {
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
          }
          50% {
            box-shadow: 0 0 8px 2px rgba(16, 185, 129, 0.3);
          }
        }
        .animate-fade-slide-in {
          animation: fadeSlideIn 0.4s ease-out forwards;
        }
        .animate-pulse-glow {
          animation: pulse-glow 0.6s ease-in-out;
        }
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
        <header className="flex items-center justify-between p-4 border-b border-zinc-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-emerald-500 to-emerald-700 rounded-full flex items-center justify-center">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="font-semibold text-white">Routine Agent</h1>
              <p className="text-sm text-zinc-400">
                {stepLabel}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {showStepBadge && (
              <span className="px-2 py-1 text-xs bg-emerald-500/20 text-emerald-400 rounded-full">
                {currentStep}
              </span>
            )}
            {hasMessages && (
              <button
                onClick={clearCurrentConversation}
                className="text-sm text-zinc-500 hover:text-zinc-300 px-3 py-1 rounded hover:bg-zinc-800 transition-colors"
              >
                초기화
              </button>
            )}
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-4">
          {noMessages ? (
            <div className="flex flex-col items-center justify-center h-full text-zinc-500">
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
                        {/* 헤더 - 클릭으로 토글 */}
                        <button
                          onClick={() => setProgressExpanded(!progressExpanded)}
                          className="flex items-center justify-between w-full text-xs text-zinc-500 mb-2 hover:text-zinc-400 transition-colors"
                        >
                          <span>진행 기록 ({progressLog.length})</span>
                          {hasMultipleProgress && (
                            progressExpanded ? (
                              <ChevronUp className="w-3 h-3" />
                            ) : (
                              <ChevronDown className="w-3 h-3" />
                            )
                          )}
                        </button>

                        {/* 접힌 상태: 최신 항목만 표시 (애니메이션 적용) */}
                        {!progressExpanded && latestProgress && (
                          <div
                            className={`flex items-start gap-2 text-xs rounded px-1 py-0.5 -mx-1 ${
                              animateLatest ? 'animate-fade-slide-in animate-pulse-glow' : ''
                            }`}
                          >
                            <span className="text-zinc-600 whitespace-nowrap">
                              {new Date(latestProgress.timestamp).toLocaleTimeString("ko-KR", {
                                hour: "2-digit",
                                minute: "2-digit",
                                second: "2-digit"
                              })}
                            </span>
                            <Check className={`w-3 h-3 mt-0.5 flex-shrink-0 transition-colors ${
                              animateLatest ? 'text-emerald-300' : 'text-emerald-400'
                            }`} />
                            <span className={`transition-colors ${
                              animateLatest ? 'text-white' : 'text-zinc-300'
                            }`}>{latestProgress.status}</span>
                            {latestProgress.detail && (
                              <span className="text-zinc-500 truncate max-w-[200px]">- {latestProgress.detail}</span>
                            )}
                          </div>
                        )}

                        {/* 펼친 상태: 전체 히스토리 */}
                        {progressExpanded && (
                          <div className="space-y-1 max-h-40 overflow-y-auto">
                            {progressLog.map((item, idx) => (
                              <div
                                key={idx}
                                className={`flex items-start gap-2 text-xs rounded px-1 py-0.5 -mx-1 ${
                                  idx === progressLog.length - 1 && animateLatest
                                    ? 'animate-fade-slide-in animate-pulse-glow'
                                    : ''
                                }`}
                              >
                                <span className="text-zinc-600 whitespace-nowrap">
                                  {new Date(item.timestamp).toLocaleTimeString("ko-KR", {
                                    hour: "2-digit",
                                    minute: "2-digit",
                                    second: "2-digit"
                                  })}
                                </span>
                                <Check className={`w-3 h-3 mt-0.5 flex-shrink-0 ${
                                  idx === progressLog.length - 1 && animateLatest
                                    ? 'text-emerald-300'
                                    : 'text-emerald-400'
                                }`} />
                                <span className={`${
                                  idx === progressLog.length - 1 && animateLatest
                                    ? 'text-white'
                                    : 'text-zinc-300'
                                }`}>{item.status}</span>
                                {item.detail && (
                                  <span className="text-zinc-500">- {item.detail}</span>
                                )}
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

        <ChatInput onSend={handleSend} disabled={isLoading} />
      </div>
    </div>
  )
}
