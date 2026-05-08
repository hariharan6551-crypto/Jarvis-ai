import React, { useMemo } from 'react';
import { motion } from 'framer-motion';

export default function AICore({ state }) {
  const bars = useMemo(() => Array.from({ length: 32 }, (_, i) => {
    const active = state === 'listening' || state === 'speaking';
    const h = active ? 4 + Math.random() * 24 : 4 + Math.sin(i * 0.5) * 3;
    return { h, delay: i * 0.03 };
  }), [state]);

  return (
    <div className="ai-core-container">
      <motion.div className={`ai-core ${state}`} animate={{ scale: state === 'thinking' ? [1, 1.03, 1] : 1 }} transition={{ repeat: state === 'thinking' ? Infinity : 0, duration: 1.5 }}>
        <div className="ai-ring ai-ring-1" />
        <div className="ai-ring ai-ring-2" />
        <div className="ai-ring ai-ring-3" />
        <div className="ai-ring-dash" />
        <motion.div className="ai-center" animate={{ scale: state === 'speaking' ? [1, 1.08, 1] : state === 'listening' ? [1, 1.05, 1] : 1 }} transition={{ repeat: Infinity, duration: state === 'speaking' ? 0.6 : 1.2 }}>
          <span className="ai-center-text">J.A.R.V.I.S</span>
        </motion.div>
      </motion.div>
      <div className="voice-section">
        <div className="waveform-container">
          {bars.map((b, i) => (
            <motion.div key={i} className={`waveform-bar ${state === 'listening' || state === 'speaking' ? 'active' : ''}`}
              animate={{ height: state === 'listening' || state === 'speaking' ? [4, 4 + Math.random() * 24, 4] : b.h }}
              transition={{ repeat: Infinity, duration: 0.4 + Math.random() * 0.4, delay: b.delay }} />
          ))}
        </div>
      </div>
      <motion.div className="ai-status-text" key={state} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
        {state === 'idle' && <><span className="greeting">Welcome back Hari.</span><br />All systems are operational.<br />How may I assist you today?</>}
        {state === 'listening' && 'Listening...'}
        {state === 'thinking' && 'Processing your command...'}
        {state === 'executing' && 'Executing command...'}
        {state === 'speaking' && 'Speaking...'}
        {state === 'error' && 'An error occurred. Please try again.'}
      </motion.div>
    </div>
  );
}
