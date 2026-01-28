import { create } from "zustand"
import { persist } from "zustand/middleware"
import { agentApi } from "../services/api"
import type { ChatMessage } from "../types/chat"

const generateId = (): string => {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === "x" ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

interface Conversation {
  id: string
  sessionId: string | null
  title: string
  messages: ChatMessage[]
  currentStep: string
  createdAt: Date
  updatedAt: Date
}

interface ProgressItem {
  status: string
  detail: string
  timestamp: Date
}

interface ChatState {
  conversations: Conversation[]
  currentConversationId: string | null
  isLoading: boolean
  sidebarCollapsed: boolean
  progressLog: ProgressItem[]
  currentStatus: string
  
  getCurrentConversation: () => Conversation | null
  getMessages: () => ChatMessage[]
  getCurrentStep: () => string
  getSessionId: () => string | null
  
  createConversation: () => string
  selectConversation: (id: string) => void
  deleteConversation: (id: string) => Promise<void>
  startWorkflow: (userRequest: string) => Promise<void>
  sendMessage: (content: string, images?: string[]) => Promise<void>
  sendInlineMessage: (content: string) => Promise<void>
  setLoading: (loading: boolean) => void
  setSidebarCollapsed: (collapsed: boolean) => void
  clearCurrentConversation: () => void
  addProgress: (status: string, detail: string) => void
  clearProgress: () => void
}


// 채널 저장 완료 시 리다이렉트 처리
const handleChannelSaved = (response: { current_step: string; data?: { redirect_to?: string; redirect_delay?: number; error?: string; error_detail?: string } }) => {
  if (response.current_step === 'channel_saved' && response.data?.redirect_to) {
    const delay = response.data.redirect_delay || 3000
    setTimeout(() => {
      window.location.href = response.data!.redirect_to!
    }, delay)
  }
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      conversations: [],
      currentConversationId: null,
      isLoading: false,
      sidebarCollapsed: false,
      progressLog: [],
      currentStatus: "",
      
      getCurrentConversation: () => {
        const state = get()
        return state.conversations.find(c => c.id === state.currentConversationId) || null
      },
      
      getMessages: () => {
        const conv = get().getCurrentConversation()
        return conv?.messages || []
      },
      
      getCurrentStep: () => {
        const conv = get().getCurrentConversation()
        return conv?.currentStep || "idle"
      },
      
      getSessionId: () => {
        const conv = get().getCurrentConversation()
        return conv?.sessionId || null
      },
      
      createConversation: () => {
        const id = generateId()
        const newConv: Conversation = {
          id,
          sessionId: null,
          title: "새 대화",
          messages: [],
          currentStep: "idle",
          createdAt: new Date(),
          updatedAt: new Date()
        }
        
        set(state => ({
          conversations: [newConv, ...state.conversations],
          currentConversationId: id
        }))
        
        return id
      },
      
      selectConversation: (id: string) => {
        set({ currentConversationId: id, progressLog: [], currentStatus: "" })
      },
      
      deleteConversation: async (id: string) => {
        const state = get()
        const conversation = state.conversations.find(c => c.id === id)
        const sessionId = conversation?.sessionId
        
        if (sessionId) {
          try {
            await agentApi.deleteSession(sessionId)
          } catch (error) {
            console.error("Failed to delete session:", error)
          }
        }
        
        set(state => {
          const filtered = state.conversations.filter(c => c.id !== id)
          const newCurrentId = state.currentConversationId === id
            ? (filtered[0]?.id || null)
            : state.currentConversationId
          
          return {
            conversations: filtered,
            currentConversationId: newCurrentId
          }
        })
      },
      
      addProgress: (status: string, detail: string) => {
        set(state => ({
          progressLog: [...state.progressLog, { status, detail, timestamp: new Date() }],
          currentStatus: status
        }))
      },
      
      clearProgress: () => {
        set({ progressLog: [], currentStatus: "" })
      },
      
      startWorkflow: async (userRequest: string) => {
        const state = get()
        let convId = state.currentConversationId
        
        if (!convId) {
          convId = get().createConversation()
        }
        
        set({ isLoading: true, progressLog: [], currentStatus: "워크플로우 시작 중..." })
        
        const userMessage: ChatMessage = {
          id: generateId(),
          role: "user",
          content: userRequest,
          images: [],
          timestamp: new Date()
        }
        
        set(state => ({
          conversations: state.conversations.map(c =>
            c.id === convId
              ? {
                  ...c,
                  messages: [...c.messages, userMessage],
                  title: userRequest.slice(0, 30) + (userRequest.length > 30 ? "..." : ""),
                  updatedAt: new Date()
                }
              : c
          )
        }))
        
        try {
          get().addProgress("연결 중", "서버에 연결하는 중...")
          const response = await agentApi.start(userRequest)
          get().addProgress("완료", "응답 수신 완료")
          
          const agentMessage: ChatMessage = {
            id: generateId(),
            role: "assistant",
            content: response.message,
            images: response.images,
            timestamp: new Date(),
            metadata: {
              step: response.current_step,
              needs_feedback: response.needs_feedback,
              data: response.data
            }
          }
          
          set(state => ({
            conversations: state.conversations.map(c =>
              c.id === convId
                ? {
                    ...c,
                    sessionId: response.session_id,
                    messages: [...c.messages, agentMessage],
                    currentStep: response.current_step,
                    updatedAt: new Date()
                  }
                : c
            ),
            isLoading: false,
            progressLog: [],
            currentStatus: ""
          }))
        } catch (error) {
          console.error("Start workflow error:", error)
          get().addProgress("오류", String(error))
          set({ isLoading: false })
        }
      },
      
      // 인라인 메시지 - 마지막 assistant 메시지를 교체 (사용자 메시지 없음)
      sendInlineMessage: async (content: string) => {
        const state = get()
        const convId = state.currentConversationId
        const sessionId = state.getSessionId()

        if (!convId || !sessionId) return

        set({ isLoading: true, currentStatus: "처리 중..." })

        try {
          const response = await agentApi.sendMessage(sessionId, content, [])

          const newAssistantMessage: ChatMessage = {
            id: generateId(),
            role: "assistant",
            content: response.message,
            images: response.images,
            timestamp: new Date(),
            metadata: {
              step: response.current_step,
              needs_feedback: response.needs_feedback,
              data: response.data
            }
          }

          // 마지막 assistant 메시지를 교체
          set(state => ({
            conversations: state.conversations.map(c => {
              if (c.id === convId) {
                const messages = [...c.messages]
                // 마지막 assistant 메시지 인덱스 찾기
                let lastAssistantIdx = -1
                for (let i = messages.length - 1; i >= 0; i--) {
                  if (messages[i].role === "assistant") {
                    lastAssistantIdx = i
                    break
                  }
                }
                
                if (lastAssistantIdx >= 0) {
                  // 마지막 assistant 메시지 교체
                  messages[lastAssistantIdx] = newAssistantMessage
                } else {
                  // assistant 메시지가 없으면 추가
                  messages.push(newAssistantMessage)
                }
                
                return {
                  ...c,
                  messages,
                  currentStep: response.current_step,
                  updatedAt: new Date()
                }
              }
              return c
            }),
            isLoading: false,
            currentStatus: ""
          }))

          handleChannelSaved(response)
        } catch (error) {
          console.error("Inline message error:", error)
          set({ isLoading: false, currentStatus: "" })
        }
      },

      sendMessage: async (content: string, images: string[] = []) => {
        console.log("[sendMessage] Called with:", content)
        const state = get()
        const convId = state.currentConversationId
        const sessionId = state.getSessionId()
        
        if (!convId) {
          return state.startWorkflow(content)
        }
        
        if (!sessionId) {
          return state.startWorkflow(content)
        }
        
        set({ isLoading: true, progressLog: [], currentStatus: "처리 시작..." })
        
        const userMessage: ChatMessage = {
          id: generateId(),
          role: "user",
          content,
          images,
          timestamp: new Date()
        }
        
        set(state => ({
          conversations: state.conversations.map(c =>
            c.id === convId
              ? {
                  ...c,
                  messages: [...c.messages, userMessage],
                  updatedAt: new Date()
                }
              : c
          )
        }))
        
        // SSE 스트리밍 사용
        void agentApi.sendMessageStream(
          sessionId,
          content,
          images,
          // onProgress
          (status, detail) => {
            get().addProgress(status, detail)
          },
          // onResult
          (response) => {
            const agentMessage: ChatMessage = {
              id: generateId(),
              role: "assistant",
              content: response.message,
              images: response.images,
              timestamp: new Date(),
              metadata: {
                step: response.current_step,
                needs_feedback: response.needs_feedback,
                data: response.data
              }
            }
            
            set(state => ({
              conversations: state.conversations.map(c =>
                c.id === convId
                  ? {
                      ...c,
                      messages: [...c.messages, agentMessage],
                      currentStep: response.current_step,
                      updatedAt: new Date()
                    }
                  : c
              ),
              isLoading: false,
              progressLog: [],
              currentStatus: ""
            }))
          },
          // onError - fallback to regular API
          async (error) => {
            console.warn("SSE failed, falling back to regular API:", error)
            
            try {
              const response = await agentApi.sendMessage(sessionId, content, images)
              
              const agentMessage: ChatMessage = {
                id: generateId(),
                role: "assistant",
                content: response.message,
                images: response.images,
                timestamp: new Date(),
                metadata: {
                  step: response.current_step,
                  needs_feedback: response.needs_feedback,
                  data: response.data
                }
              }
              
              set(state => ({
                conversations: state.conversations.map(c =>
                  c.id === convId
                    ? {
                        ...c,
                        messages: [...c.messages, agentMessage],
                        currentStep: response.current_step,
                        updatedAt: new Date()
                      }
                    : c
                ),
                isLoading: false,
                progressLog: [],
                currentStatus: ""
              }))
            } catch (apiError) {
              console.error("API also failed:", apiError)
              
              const errorMessage: ChatMessage = {
                id: generateId(),
                role: "assistant",
                content: "죄송합니다. 오류가 발생했습니다. 다시 시도해주세요.",
                images: [],
                timestamp: new Date()
              }
              
              set(state => ({
                conversations: state.conversations.map(c =>
                  c.id === convId
                    ? { ...c, messages: [...c.messages, errorMessage] }
                    : c
                ),
                isLoading: false,
                progressLog: [],
                currentStatus: ""
              }))
            }
          }
        )
      },
      
      setLoading: (loading) => set({ isLoading: loading }),
      
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
      
      clearCurrentConversation: () => {
        const state = get()
        if (state.currentConversationId) {
          set(state => ({
            conversations: state.conversations.map(c =>
              c.id === state.currentConversationId
                ? {
                    ...c,
                    messages: [],
                    sessionId: null,
                    currentStep: "idle",
                    title: "새 대화",
                    updatedAt: new Date()
                  }
                : c
            ),
            progressLog: [],
            currentStatus: ""
          }))
        }
      }
    }),
    {
      name: "routine-chat-storage",
      partialize: (state) => ({
        conversations: state.conversations.map(conv => ({
          ...conv,
          messages: conv.messages.map(msg => ({
            ...msg,
            images: []  // localStorage에서 이미지 제외 (서버에서 로드)
          }))
        })),
        currentConversationId: state.currentConversationId,
        sidebarCollapsed: state.sidebarCollapsed
      }),
      onRehydrateStorage: () => (state) => {
        // localStorage에서 복원 후 서버 히스토리 로드 (이미지 포함)
        if (state?.currentConversationId) {
          const conv = state.conversations.find(c => c.id === state.currentConversationId)
          if (conv?.sessionId) {
            // selectConversation 호출하여 서버 히스토리 로드
            setTimeout(() => {
              state.selectConversation(state.currentConversationId!)
            }, 100)
          }
        }
      }
    }
  )
)
