import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ChatMessage, SessionItem, WSServerMessage, AgentStep } from '@/types'
import { createSession, deleteSession as apiDeleteSession, WSConnection } from '@/api/chat'

const SESSIONS_KEY = 'qa_sessions'
const LAST_ACTIVE_KEY = 'qa_last_active'

function loadSessions(): SessionItem[] {
  try {
    const raw = localStorage.getItem(SESSIONS_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveSessions(sessions: SessionItem[]) {
  localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions))
}

function getLastActiveSessionId(): string | null {
  return localStorage.getItem(LAST_ACTIVE_KEY)
}

function setLastActiveSessionId(id: string) {
  localStorage.setItem(LAST_ACTIVE_KEY, id)
}

function genId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

export const useChatStore = defineStore('chat', () => {
  const sessions = ref<SessionItem[]>(loadSessions())
  const currentSessionId = ref<string | null>(
    getLastActiveSessionId() ?? (sessions.value[0]?.id ?? null)
  )
  const messages = ref<ChatMessage[]>(
    sessions.value.find(s => s.id === currentSessionId.value)?.messages ?? []
  )
  const wsConn = ref<WSConnection | null>(null)
  const isStreaming = ref(false)
  const sidebarOpen = ref(true)
  const error = ref<string | null>(null)

  function saveCurrentSessionMessages() {
    if (!currentSessionId.value) return
    const idx = sessions.value.findIndex(s => s.id === currentSessionId.value)
    if (idx !== -1) {
      sessions.value[idx]!.messages = messages.value.map(m => ({ ...m }))
      saveSessions(sessions.value)
    }
  }

  const currentSession = computed(() =>
    sessions.value.find((s) => s.id === currentSessionId.value) ?? null,
  )

  function handleMessage(msg: WSServerMessage) {
    console.log('[WS] Received:', msg.type, msg)
    if (msg.type === 'agent_step' && msg.step_type && msg.content) {
      // 查找最后一个 RAG Agent 消息
      const lastRagMsg = [...messages.value].reverse().find(m => m.message_type === 'rag_agent' && !m.streaming)
      if (lastRagMsg && lastRagMsg.agent_steps) {
        lastRagMsg.agent_steps.push({
          id: genId(),
          step_type: msg.step_type,
          content: msg.content,
          timestamp: Date.now(),
        })
      } else {
        // 没有现有的 RAG 消息，创建新的
        messages.value.push({
          id: genId(),
          role: 'assistant',
          content: '',
          message_type: 'rag_agent',
          agent_steps: [{
            id: genId(),
            step_type: msg.step_type,
            content: msg.content,
            timestamp: Date.now(),
          }],
          streaming: false,
          timestamp: Date.now(),
        })
      }
    } else if (msg.type === 'chunk' && msg.message_id !== undefined) {
      const existing = messages.value.find((m) => m.id === `stream-${msg.message_id}` || m.id === 'stream-pending')
      if (existing) {
        existing.content += msg.content ?? ''
        if (existing.id === 'stream-pending') {
          existing.id = `stream-${msg.message_id}`
        }
      } else {
        messages.value.push({
          id: `stream-${msg.message_id}`,
          role: 'assistant',
          content: msg.content ?? '',
          streaming: true,
          timestamp: Date.now(),
        })
      }
    } else if (msg.type === 'done' && msg.message_id !== undefined) {
      const existing = messages.value.find((m) => m.id === `stream-${msg.message_id}` || m.id === 'stream-pending')
      if (existing) {
        existing.content = msg.content ?? existing.content
        existing.streaming = false
        existing.id = `done-${msg.message_id}`
      } else {
        messages.value.push({
          id: `done-${msg.message_id}`,
          role: 'assistant',
          content: msg.content ?? '',
          streaming: false,
          timestamp: Date.now(),
        })
      }
      isStreaming.value = false

      const idx = sessions.value.findIndex(s => s.id === currentSessionId.value)
      if (idx !== -1) {
        sessions.value[idx]!.updatedAt = Date.now()
        const userMsg = messages.value.find(m => m.role === 'user')
        const allAssistant = messages.value.filter(m => m.role === 'assistant')
        const lastAssistant = allAssistant[allAssistant.length - 1]
        if (lastAssistant) {
          sessions.value[idx]!.title = (userMsg?.content ?? 'new_chat').slice(0, 40)
        }
        if (msg.cursor) {
          sessions.value[idx]!.cursor = msg.cursor
        }
        sessions.value[idx]!.messages = messages.value.map(m => ({ ...m }))
        saveSessions(sessions.value)
      }
    } else if (msg.type === 'error') {
      error.value = msg.error ?? 'Unknown error'
      isStreaming.value = false
    }
  }

  function handleClose() {
    wsConn.value = null
    isStreaming.value = false
  }

  async function sendMessage(content: string) {
    error.value = null

    const userMsg: ChatMessage = {
      id: genId(),
      role: 'user',
      content,
      timestamp: Date.now(),
    }
    messages.value.push(userMsg)
    saveCurrentSessionMessages()
    isStreaming.value = true

    if (!currentSessionId.value) {
      const { session_id } = await createSession()
      const item: SessionItem = {
        id: session_id,
        title: content.slice(0, 40),
        updatedAt: Date.now(),
        messages: [],
        cursor: undefined,
      }
      sessions.value.unshift(item)
      saveSessions(sessions.value)
      setLastActiveSessionId(session_id)
      currentSessionId.value = session_id
    }

    if (!wsConn.value) {
      wsConn.value = new WSConnection(
        currentSessionId.value!,
        handleMessage,
        handleClose,
      )
    }

    await wsConn.value.waitOpen()
    wsConn.value.sendMessage(content)
  }

  function switchSession(id: string) {
    saveCurrentSessionMessages()
    if (wsConn.value) {
      wsConn.value.close()
      wsConn.value = null
    }
    const targetSession = sessions.value.find(s => s.id === id)
    messages.value = targetSession?.messages ? targetSession.messages.map(m => ({ ...m })) : []
    currentSessionId.value = id
    setLastActiveSessionId(id)
    isStreaming.value = false
    error.value = null
  }

  function connectWS() {
    if (!currentSessionId.value || wsConn.value) return
    wsConn.value = new WSConnection(
      currentSessionId.value,
      handleMessage,
      handleClose,
    )
  }

  async function createNewSession(): Promise<string> {
    saveCurrentSessionMessages()
    const { session_id } = await createSession()
    const item: SessionItem = {
      id: session_id,
      title: '新对话',
      updatedAt: Date.now(),
      messages: [],
      cursor: undefined,
    }
    sessions.value.unshift(item)
    saveSessions(sessions.value)
    setLastActiveSessionId(session_id)
    return session_id
  }

  async function deleteSession(id: string) {
    console.log('[Store] deleteSession called:', id)
    try {
      const result = await apiDeleteSession(id)
      console.log('[Store] deleteSession result:', result)
    } catch (e) {
      console.error('[Store] Failed to delete session on server:', e)
    }
    const idx = sessions.value.findIndex((s) => s.id === id)
    if (idx !== -1) {
      sessions.value.splice(idx, 1)
      saveSessions(sessions.value)
      if (currentSessionId.value === id) {
        if (wsConn.value) {
          wsConn.value.close()
          wsConn.value = null
        }
        messages.value = []
        currentSessionId.value = sessions.value[0]?.id ?? null
        if (currentSessionId.value) {
          setLastActiveSessionId(currentSessionId.value)
          const targetSession = sessions.value.find(s => s.id === currentSessionId.value)
          messages.value = targetSession?.messages ? targetSession.messages.map(m => ({ ...m })) : []
        } else {
          localStorage.removeItem(LAST_ACTIVE_KEY)
        }
      }
    }
  }

  function toggleSidebar() {
    sidebarOpen.value = !sidebarOpen.value
  }

  function stopGeneration() {
    if (wsConn.value) {
      wsConn.value.sendStop()
    }
    isStreaming.value = false
  }

  function clearCurrentMessages() {
    if (currentSessionId.value) {
      saveCurrentSessionMessages()
      const idx = sessions.value.findIndex(s => s.id === currentSessionId.value)
      if (idx !== -1) {
        sessions.value[idx]!.messages = []
        sessions.value[idx]!.cursor = undefined
        saveSessions(sessions.value)
      }
    }
    messages.value = []
    if (wsConn.value) {
      wsConn.value.close()
      wsConn.value = null
    }
    isStreaming.value = false
    error.value = null
  }

  return {
    sessions,
    currentSessionId,
    currentSession,
    messages,
    isStreaming,
    sidebarOpen,
    error,
    createNewSession,
    switchSession,
    sendMessage,
    deleteSession,
    toggleSidebar,
    clearCurrentMessages,
    stopGeneration,
    wsConn,
    connectWS,
  }
})
