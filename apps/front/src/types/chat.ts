export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'agent'
  content: string
  images: string[]
  timestamp: Date
  metadata?: {
    step?: string
    needs_feedback?: boolean
    data?: Record<string, unknown>
  }
}

export interface Agent {
  id: string
  name: string
  avatar?: string
  description: string
}

export interface WorkflowStep {
  id: string
  name: string
  status: 'pending' | 'active' | 'completed'
}
