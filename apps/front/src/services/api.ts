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

export interface SessionData {
  id: string
  current_step: string
  context: Record<string, unknown>
  history: Array<{role: string, content: string, images?: string[], step?: string, timestamp?: string}>
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
  // 이미지가 있으면 POST, 없으면 GET 사용
  sendMessageStream(
    sessionId: string, 
    message: string, 
    images: string[] = [],
    onProgress: (status: string, detail: string) => void,
    onResult: (response: AgentResponse) => void,
    onError: (error: string) => void
  ): () => void {
    // 이미지가 있으면 POST 사용 (URL 길이 제한 회피)
    if (images.length > 0) {
      return this._sendMessageStreamPost(sessionId, message, images, onProgress, onResult, onError)
    }
    
    // 이미지 없으면 기존 GET 방식 (EventSource)
    const params = new URLSearchParams({
      session_id: sessionId,
      message: message,
      images: "[]"
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
    
    return () => eventSource.close()
  },
  
  // POST 방식 SSE (fetch + ReadableStream)
  _sendMessageStreamPost(
    sessionId: string, 
    message: string, 
    images: string[],
    onProgress: (status: string, detail: string) => void,
    onResult: (response: AgentResponse) => void,
    onError: (error: string) => void
  ): () => void {
    const controller = new AbortController()
    
    fetch(API_BASE + "/api/agents/message/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        message: message,
        images: images
      }),
      signal: controller.signal
    })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error("API Error: " + response.status)
      }
      
      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error("No response body")
      }
      
      const decoder = new TextDecoder()
      let buffer = ""
      
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        buffer += decoder.decode(value, { stream: true })
        
        // SSE 형식 파싱: "data: {...}\n\n"
        const lines = buffer.split("\n\n")
        buffer = lines.pop() || ""
        
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data: ProgressEvent = JSON.parse(line.slice(6))
              
              if (data.type === "progress") {
                onProgress(data.status || "", data.detail || "")
              } else if (data.type === "result" && data.data) {
                onResult(data.data)
              } else if (data.type === "error") {
                onError(data.message || "Unknown error")
              }
            } catch (e) {
              console.error("Failed to parse SSE data:", e)
            }
          }
        }
      }
    })
    .catch((e) => {
      if (e.name !== "AbortError") {
        onError(e.message || "Connection lost")
      }
    })
    
    return () => controller.abort()
  },
  
  async getSession(sessionId: string): Promise<SessionData> {
    const response = await fetch(API_BASE + "/api/agents/session/" + sessionId)
    
    if (!response.ok) {
      throw new Error("Session not found")
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
