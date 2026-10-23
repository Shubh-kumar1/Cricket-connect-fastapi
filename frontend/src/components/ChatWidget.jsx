import { useEffect, useRef, useState } from 'react'
import { LoaderCircle, MessageCircle, Send, X } from 'lucide-react'
import { api } from '../lib/api'

const welcomeMessage = {
  id: 'welcome',
  role: 'assistant',
  content: 'Hi! I can help with Cricket Connect sessions, bookings, providers, and venues.',
}
const examples = [
  'How do I find cricket sessions?',
  'How do bookings work?',
  'What information is available about a venue?',
  'How can a provider manage a session?',
]

export default function ChatWidget() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([welcomeMessage])
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const listRef = useRef(null)
  const nextId = useRef(0)
  const sendingRef = useRef(false)

  useEffect(() => {
    if (open && listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight
  }, [open, messages])

  const sendMessage = async (value = draft) => {
    const text = value.trim()
    if (!text || sendingRef.current) return
    sendingRef.current = true
    const previous = messages.filter(item => item.id !== 'welcome' && !item.error)
    const userMessage = { id: ++nextId.current, role: 'user', content: text }
    const pendingId = ++nextId.current
    setMessages(current => [...current, userMessage, { id: pendingId, role: 'assistant', pending: true }].slice(-12))
    setDraft('')
    setSending(true)
    try {
      const result = await api.chat({
        message: text,
        history: previous.slice(-8).map(({ role, content }) => ({ role, content })),
      })
      setMessages(current => current.map(item => item.id === pendingId
        ? { id: pendingId, role: 'assistant', content: result.answer, sources: result.sources || [] }
        : item))
    } catch (error) {
      setMessages(current => current.map(item => item.id === pendingId
        ? { id: pendingId, role: 'assistant', content: error.message || 'Unable to send your message. Please try again.', error: true }
        : item))
    } finally {
      sendingRef.current = false
      setSending(false)
    }
  }

  return <div className="chat-widget">
    {open && <section className="chat-panel" aria-label="Cricket Connect assistant">
      <header className="chat-header">
        <div><strong>Cricket Connect assistant</strong><span>Grounded help for your game</span></div>
        <button type="button" onClick={() => setOpen(false)} aria-label="Close chat"><X size={20} /></button>
      </header>
      <div className="chat-messages" ref={listRef} aria-live="polite">
        {messages.map(item => <div key={item.id} className={`chat-message ${item.role}${item.error ? ' chat-error' : ''}`}>
          {item.pending ? <span className="chat-loading"><LoaderCircle size={16} className="chat-spinner" /> Thinking…</span> : item.content}
          {item.sources?.length > 0 && <div className="chat-sources">Sources: {item.sources.map(source => source.title).join(' · ')}</div>}
        </div>)}
        {messages.length === 1 && <div className="chat-examples">
          <p>Try asking:</p>
          {examples.map(example => <button key={example} type="button" onClick={() => sendMessage(example)}>{example}</button>)}
        </div>}
      </div>
      <form className="chat-composer" onSubmit={event => { event.preventDefault(); sendMessage() }}>
        <textarea
          value={draft}
          onChange={event => setDraft(event.target.value)}
          onKeyDown={event => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              sendMessage()
            }
          }}
          placeholder="Ask about sessions, bookings, or venues…"
          aria-label="Your message"
          maxLength={2000}
          rows={2}
          disabled={sending}
        />
        <button type="submit" aria-label="Send message" disabled={sending || !draft.trim()}><Send size={18} /></button>
      </form>
      <div className="chat-hint">Answers use verified platform guidance and current public listings.</div>
    </section>}
    <button
      type="button"
      className="chat-launcher"
      onClick={() => setOpen(value => !value)}
      aria-label={open ? 'Close assistant' : 'Open Cricket Connect assistant'}
      aria-expanded={open}
    >
      {open ? <X size={24} /> : <MessageCircle size={24} />}
    </button>
  </div>
}
