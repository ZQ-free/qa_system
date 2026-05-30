export interface SourceInfo {
  museum: string
  url: string
  object_id: string
  image_url?: string
  accession_number?: string
}

export interface AskResponse {
  answer_id: string
  question: string
  answer: string
  intent: string
  entity: string
  sources: SourceInfo[]
  has_kg_facts: boolean
  has_llm_content: boolean
  not_found: boolean
}

export type WSMessageType =
  | 'connected'
  | 'chunk'
  | 'done'
  | 'error'
  | 'resume_remaining'
  | 'pong'
  | 'agent_step'

export interface WSServerMessage {
  type: WSMessageType
  session_id?: string
  last_message_id?: number
  streaming_done?: boolean
  last_content?: string
  sent_offset?: number
  message_id?: number
  content?: string
  done?: boolean
  remaining?: string
  cursor?: string
  error?: string
  intent?: string
  sources?: SourceInfo[]
  tool_name?: string
  tool_args?: string
  tool_result?: string
  thinking_content?: string
  step_type?: 'reasoning' | 'tool_call' | 'tool_result'
}

export type MessageType = 'text' | 'rag_agent'

export interface AgentStep {
  id: string
  step_type: 'reasoning' | 'tool_call' | 'tool_result'
  content: string
  timestamp: number
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'tool'
  content: string
  sources?: SourceInfo[]
  streaming?: boolean
  intent?: string
  timestamp: number
  message_type?: MessageType
  tool_name?: string
  agent_steps?: AgentStep[]
}

export interface SessionItem {
  id: string
  title: string
  updatedAt: number
  messages?: ChatMessage[]
  cursor?: string
}