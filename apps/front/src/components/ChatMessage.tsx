import type { ChatMessage as Message } from "../types/chat"
import { useChatStore } from "../stores/chatStore"
import { useState } from "react"
import ReactMarkdown from "react-markdown"
import { Download, X } from "lucide-react"

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
}

// 메시지에서 퀵 액션 추출
function extractQuickActions(content: string): QuickAction[] {
  const actions: QuickAction[] = []

  // "확인" 또는 "맞아" 패턴
  if (content.includes("맞으면") && (content.includes("확인") || content.includes("맞아"))) {
    actions.push({ label: "확인", value: "확인" })
  }

  // "분석 시작" 또는 "시작" 패턴
  if (content.includes("분석을 시작하려면") || content.includes("분석 시작") ||
      (content.includes("시작") && content.includes("\"시작\""))) {
    actions.push({ label: "분석 시작", value: "시작" })
  }

  // "추가" 패턴
  if (content.includes("추가하려면") && content.includes("확인")) {
    // 이미 확인이 있으면 추가하지 않음
    if (!actions.some(a => a.label === "확인")) {
      actions.push({ label: "확인", value: "확인" })
    }
  }

  // "다음" 또는 "확인" 패턴 (리포트 확인 후)
  if (content.includes("다음 단계로 진행하려면") || content.includes("리포트 확인 완료")) {
    actions.push({ label: "다음 단계", value: "다음" })
  }

  // "스킵" 패턴
  if (content.includes("스킵") || content.includes("건너뛰")) {
    actions.push({ label: "스킵", value: "스킵" })
  }

  return actions
}

export function ChatMessage({ message, isLast = false }: Props) {
  const { sendMessage, isLoading } = useChatStore()
  const [enlargedImage, setEnlargedImage] = useState<string | null>(null)
  const isAgent = message.role === "assistant" || message.role === "agent"

  const timestamp = message.timestamp instanceof Date
    ? message.timestamp
    : new Date(message.timestamp)

  const options: SelectionOption[] = (message.metadata?.data?.options as SelectionOption[]) || []
  const isSelection = message.metadata?.data?.type === "selection"

  // 퀵 액션 추출 (마지막 에이전트 메시지이고 로딩 중이 아닐 때만)
  const quickActions = isAgent && isLast && !isLoading && message.content
    ? extractQuickActions(message.content)
    : []

  const handleOptionClick = (option: SelectionOption) => {
    if (!isLoading) {
      sendMessage(String(option.id), [])
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

  const msgIsAgent = isAgent
  const stepName = message.metadata?.step as string | undefined

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
                <ReactMarkdown>{message.content}</ReactMarkdown>
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
            <div className="flex gap-2 mt-2 ml-1">
              {quickActions.map((action, idx) => (
                <button
                  key={idx}
                  onClick={() => handleQuickAction(action)}
                  disabled={isLoading}
                  className="px-4 py-2 text-sm font-medium bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {action.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

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
