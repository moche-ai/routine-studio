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
  setLoading: (loading: boolean) => void
  setSidebarCollapsed: (collapsed: boolean) => void
  clearCurrentConversation: () => void
  addProgress: (status: string, detail: string) => void
  clearProgress: () => void
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
      
      sendMessage: async (content: string, images: string[] = []) => {
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
        conversations: state.conversations,
        currentConversationId: state.currentConversationId,
        sidebarCollapsed: state.sidebarCollapsed
      })
    }
  )
)
