import { useState, useEffect, useRef, type FormEvent } from 'react'
import './App.css'

type Role = 'user' | 'ai';

interface Message {
  id: string;
  role: Role;
  content: string;
  isLoading?: boolean;
}

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {

    var protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    var host = window.location.hostname;

    //! Change this later
    if (import.meta.env.DEV){
      protocol = 'http';
      host = 'localhost';
    }

    console.log(import.meta.env.VITE_API_PORT);


    const port = import.meta.env.VITE_API_PORT || 8080;

    // Make sure this matches your working port (e.g. 8080)
    const ws = new WebSocket(`${protocol}://${host}:${port}/ws/chat`);

    ws.onopen = () => {
      console.log('Connected to Jarvis');
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'chunk') {
        setIsProcessing(false); // Stop processing state as soon as we get the first chunk

        setMessages(prev => {
          const newMessages = [...prev];
          const lastMsg = newMessages[newMessages.length - 1];

          if (lastMsg && lastMsg.role === 'ai') {
            // If the message is marked as loading, overwrite it with the first chunk
            if (lastMsg.isLoading) {
              newMessages[newMessages.length - 1] = {
                ...lastMsg,
                content: data.content,
                isLoading: false
              };
            } else {
              // Append chunk to current AI message
              newMessages[newMessages.length - 1] = {
                ...lastMsg,
                content: lastMsg.content + data.content
              };
            }
            return newMessages;
          } else {
            // Create new AI message bubble (fallback)
            return [...newMessages, { id: Date.now().toString(), role: 'ai', content: data.content }];
          }
        });
      } else if (data.type === 'done') {
        setIsProcessing(false);
      }
    };

    ws.onclose = () => {
      console.log('Disconnected');
      setIsConnected(false);
      setIsProcessing(false);
    };

    wsRef.current = ws;

    return () => {
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    };
  }, []);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN || isProcessing) return;

    // 1. Add user message
    const newUserMsg: Message = { id: Date.now().toString(), role: 'user', content: input };

    // 2. Add placeholder AI thinking message
    const thinkingMsg: Message = { id: (Date.now() + 1).toString(), role: 'ai', content: '', isLoading: true };

    setMessages(prev => [...prev, newUserMsg, thinkingMsg]);
    setIsProcessing(true);

    // Send to Python backend
    wsRef.current.send(JSON.stringify({ text: input }));
    setInput('');
  };

  return (
    <div className="chat-container">
      <div className="message-list">
        {messages.length === 0 && (
          <div className="message-wrapper ai">
            <div className="message-bubble">
              System Online. Connection {isConnected ? 'established' : 'pending...'}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`message-wrapper ${msg.role}`}>
            <div className={`message-bubble ${msg.isLoading ? 'loading-text' : ''}`}>
              {msg.isLoading ? (
                <span className="typing-indicator">Processing</span>
              ) : (
                msg.content
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <form className="input-area" onSubmit={handleSubmit}>
        <span className="prompt-indicator">{`>_`}</span>
        <input
          type="text"
          className="cli-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={isProcessing ? "Processing..." : "Awaiting input..."}
          disabled={!isConnected || isProcessing}
          autoFocus
          autoComplete="off"
        />
      </form>
    </div>
  )
}

export default App
