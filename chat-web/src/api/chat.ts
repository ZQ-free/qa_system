import type { WSServerMessage } from '@/types'

const WS_BASE = 'ws://localhost:8000/api/qa/ws'
const HTTP_BASE = 'http://localhost:8000/api/qa'

export async function createSession(): Promise<{ session_id: string }> {
  const res = await fetch(`${HTTP_BASE}/session`, { method: 'POST' })
  if (!res.ok) throw new Error(`Session creation failed: ${res.status}`)
  return res.json()
}

export async function deleteSession(sessionId: string): Promise<{ session_id: string; deleted_count: number }> {
  console.log('[API] deleteSession called:', sessionId)
  const url = `${HTTP_BASE}/session/${sessionId}`
  console.log('[API] DELETE URL:', url)
  const res = await fetch(url, { method: 'DELETE' })
  console.log('[API] deleteSession response status:', res.status)
  if (!res.ok) throw new Error(`Session deletion failed: ${res.status}`)
  const result = await res.json()
  console.log('[API] deleteSession result:', result)
  return result
}

export async function fetchHistory(sessionId: string) {
  const res = await fetch(`${HTTP_BASE}/history/${sessionId}`)
  if (!res.ok) throw new Error(`History fetch failed: ${res.status}`)
  return res.json()
}

type MessageHandler = (msg: WSServerMessage) => void
type CloseHandler = () => void

class WSConnection {
  private ws: WebSocket
  private _onMessage: MessageHandler
  private _onClose: CloseHandler
  private _openPromise: Promise<void>
  private _resolved = false

  constructor(sessionId: string, onMessage: MessageHandler, onClose: CloseHandler) {
    this._onMessage = onMessage
    this._onClose = onClose
    this.ws = new WebSocket(`${WS_BASE}?session_id=${sessionId}`)

    this._openPromise = new Promise((resolve, reject) => {
      this.ws.onopen = () => {
        this._resolved = true
        console.log('[WS] Connected')
        resolve()
      }
      this.ws.onerror = (e) => {
        this._resolved = true
        console.error('[WS] Error:', e)
        reject(new Error('WebSocket connection error'))
      }
    })

    this.ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data) as WSServerMessage
        this._onMessage(data)
      } catch {
        this._onMessage({ type: 'error', error: 'Invalid JSON from server' })
      }
    }

    this.ws.onclose = () => this._onClose()
    this.ws.onerror = () => this._onClose()
  }

  async waitOpen(): Promise<void> {
    if (this._resolved) return
    return this._openPromise
  }

  send(data: object) {
    if (this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }

  sendMessage(content: string) {
    this.send({ type: 'message', content })
  }

  sendResume(cursor: string) {
    this.send({ type: 'resume', cursor })
  }

  sendPing() {
    this.send({ type: 'ping' })
  }

  sendStop() {
    this.send({ type: 'stop' })
  }

  close() {
    this.ws.close()
  }
}

export { WSConnection }