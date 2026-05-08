import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import useStore from '../stores/useStore';

export default function ChatPanel() {
  const [input, setInput] = useState('');
  const chatMessages = useStore(s => s.chatMessages);
  const sendCommand = useStore(s => s.sendCommand);
  const aiState = useStore(s => s.aiState);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const handleSend = () => {
    if (!input.trim()) return;
    sendCommand(input.trim());
    setInput('');
  };

  return (
    <div className="chat-container">
      <div className="panel-title"><span className="panel-title-dot" />AI CONVERSATION</div>
      <div className="chat-messages">
        {chatMessages.length === 0 && (
          <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-dim)' }}>
            <div style={{ fontSize: 36, marginBottom: 12 }}>🤖</div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: 12, letterSpacing: 2, marginBottom: 6 }}>
              J.A.R.V.I.S READY
            </div>
            <div style={{ fontSize: 12 }}>
              Type a command or say "Jarvis" to begin
            </div>
          </div>
        )}
        <AnimatePresence>
          {chatMessages.map((msg) => (
            <motion.div
              key={msg.id}
              className={`chat-msg ${msg.role}`}
              initial={{ opacity: 0, y: 12, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ duration: 0.25 }}
            >
              <div className="chat-msg-avatar">
                {msg.role === 'user' ? '👤' : '🤖'}
              </div>
              <div style={{ flex: 1 }}>
                <div className="chat-msg-content">{msg.content}</div>
                <div style={{ fontSize: 9, color: 'var(--text-dim)', marginTop: 3, fontFamily: 'var(--font-mono)' }}>
                  {msg.timestamp}
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        {aiState === 'thinking' && (
          <motion.div
            className="chat-msg assistant"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <div className="chat-msg-avatar">🤖</div>
            <div className="thinking-dots">
              <span className="dot" /><span className="dot" /><span className="dot" />
            </div>
          </motion.div>
        )}
        <div ref={endRef} />
      </div>
      <div className="chat-input-row">
        <input
          className="chat-input"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSend()}
          placeholder="Type your command here…"
          spellCheck={false}
        />
        <button className="chat-send-btn" onClick={handleSend} disabled={!input.trim()}>
          ➤
        </button>
      </div>
    </div>
  );
}
