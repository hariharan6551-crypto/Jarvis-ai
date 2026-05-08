import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import useStore from '../stores/useStore';

export default function ChatPanel() {
  const [input, setInput] = useState('');
  const msgs = useStore(s => s.chatMessages);
  const sendCommand = useStore(s => s.sendCommand);
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [msgs]);

  const send = () => { if (input.trim()) { sendCommand(input.trim()); setInput(''); } };

  return (
    <div className="chat-container">
      <div className="panel-title"><span className="panel-title-dot" />AI CHAT</div>
      <div className="chat-messages">
        {msgs.length === 0 && <div style={{ textAlign: 'center', color: 'var(--text-dim)', padding: 40, fontSize: 13 }}>Start a conversation with J.A.R.V.I.S</div>}
        {msgs.map(m => (
          <motion.div key={m.id} className={`chat-msg ${m.role}`} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <div className="chat-msg-content">{m.content}</div>
          </motion.div>
        ))}
        <div ref={endRef} />
      </div>
      <div className="chat-input-row">
        <input className="chat-input" value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && send()} placeholder="Type a message..." />
        <button className="chat-send-btn" onClick={send}>➤</button>
      </div>
    </div>
  );
}
