const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000"

export interface AgentResponse {
  session_id: string
  current_step: string
  message: string
  images: string[]
  needs_feedback: boolean
  data?: Record<string, unknown>
  success: boolean
}

export interface ProgressEvent {
  type: "progress" | "result" | "done" | "error"
  status?: string
  detail?: string
  data?: AgentResponse
  message?: string
}

export interface DeleteResponse {
  success: boolean
  session_id: string
  deleted: string[]
}

export const agentApi = {
  async start(userRequest: string, sessionId?: string): Promise<AgentResponse> {
    const response = await fetch(API_BASE + "/api/agents/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_request: userRequest,
        session_id: sessionId
      })
    })
    
    if (!response.ok) {
      throw new Error("API Error: " + response.status)
    }
    
    return response.json()
  },
  
  async sendMessage(sessionId: string, message: string, images: string[] = []): Promise<AgentResponse> {
    const response = await fetch(API_BASE + "/api/agents/message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        message,
        images
      })
    })
    
    if (!response.ok) {
      throw new Error("API Error: " + response.status)
    }
    
    return response.json()
  },
  
  // SSE 스트리밍으로 메시지 전송 (진행 상황 실시간 수신)
  sendMessageStream(
    sessionId: string, 
    message: string, 
    images: string[] = [],
    onProgress: (status: string, detail: string) => void,
    onResult: (response: AgentResponse) => void,
    onError: (error: string) => void
  ): () => void {
    const params = new URLSearchParams({
      session_id: sessionId,
      message: message,
      images: JSON.stringify(images)
    })
    
    const eventSource = new EventSource(API_BASE + "/api/agents/message/stream?" + params.toString())
    
    eventSource.onmessage = (event) => {
      try {
        const data: ProgressEvent = JSON.parse(event.data)
        
        if (data.type === "progress") {
          onProgress(data.status || "", data.detail || "")
        } else if (data.type === "result" && data.data) {
          onResult(data.data)
        } else if (data.type === "error") {
          onError(data.message || "Unknown error")
          eventSource.close()
        } else if (data.type === "done") {
          eventSource.close()
        }
      } catch (e) {
        console.error("Failed to parse SSE data:", e)
      }
    }
    
    eventSource.onerror = () => {
      eventSource.close()
      onError("Connection lost")
    }
    
    // 취소 함수 반환
    return () => eventSource.close()
  },
  
  async getSession(sessionId: string): Promise<unknown> {
    const response = await fetch(API_BASE + "/api/agents/session/" + sessionId)
    
    if (!response.ok) {
      throw new Error("API Error: " + response.status)
    }
    
    return response.json()
  },
  
  async deleteSession(sessionId: string): Promise<DeleteResponse> {
    const response = await fetch(API_BASE + "/api/agents/session/" + sessionId, {
      method: "DELETE"
    })
    
    if (!response.ok) {
      throw new Error("API Error: " + response.status)
    }
    
    return response.json()
  }
}
