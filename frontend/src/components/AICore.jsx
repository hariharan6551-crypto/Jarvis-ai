import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import useStore from '../stores/useStore';

const stateConfig = {
  idle:      { label: 'STANDBY', color: 'var(--cyan)',   glow: 'rgba(0,180,255,0.4)',   emoji: '💎' },
  listening: { label: 'LISTENING', color: '#22c55e',     glow: 'rgba(34,197,94,0.5)',    emoji: '🎤' },
  thinking:  { label: 'PROCESSING', color: '#a78bfa',    glow: 'rgba(167,139,250,0.5)',  emoji: '🧠' },
  executing: { label: 'EXECUTING', color: '#f59e0b',     glow: 'rgba(245,158,11,0.5)',   emoji: '⚡' },
  speaking:  { label: 'SPEAKING', color: '#22c55e',      glow: 'rgba(34,197,94,0.5)',    emoji: '🔊' },
  error:     { label: 'ERROR', color: '#ef4444',         glow: 'rgba(239,68,68,0.5)',    emoji: '⚠️' },
};

export default function AICore({ state }) {
  const jarvisActive = useStore(s => s.jarvisActive);
  const connected = useStore(s => s.connected);
  const cfg = stateConfig[state] || stateConfig.idle;

  const bars = useMemo(() => Array.from({ length: 32 }, (_, i) => {
    const active = state === 'listening' || state === 'speaking';
    const h = active ? 4 + Math.random() * 24 : 4 + Math.sin(i * 0.5) * 3;
    return { h, delay: i * 0.03 };
  }), [state]);

  return (
    <div className="ai-core-container">
      {/* State label above the orb */}
      <motion.div
        key={state}
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        style={{
          fontFamily: 'var(--font-display)', fontSize: 10, letterSpacing: 3,
          color: cfg.color, marginBottom: 12, textAlign: 'center',
          textShadow: `0 0 10px ${cfg.glow}`,
        }}
      >
        {cfg.emoji} {cfg.label}
      </motion.div>

      {/* Core orb */}
      <motion.div
        className={`ai-core ${state}`}
        animate={{
          scale: state === 'thinking' ? [1, 1.04, 1] : 1,
        }}
        transition={{ repeat: state === 'thinking' ? Infinity : 0, duration: 1.5 }}
      >
        <div className="ai-ring ai-ring-1" style={{ borderColor: `${cfg.color}30` }} />
        <div className="ai-ring ai-ring-2" style={{ borderColor: `${cfg.color}40` }} />
        <div className="ai-ring ai-ring-3" style={{ borderColor: `${cfg.color}20` }} />
        <div className="ai-ring-dash" style={{ borderColor: `${cfg.color}25` }} />
        <motion.div
          className="ai-center"
          animate={{
            scale: state === 'speaking' ? [1, 1.1, 1] : state === 'listening' ? [1, 1.06, 1] : 1,
            boxShadow: [
              `0 0 20px ${cfg.glow}, inset 0 0 25px ${cfg.glow}`,
              `0 0 40px ${cfg.glow}, inset 0 0 35px ${cfg.glow}`,
              `0 0 20px ${cfg.glow}, inset 0 0 25px ${cfg.glow}`,
            ],
          }}
          transition={{
            repeat: Infinity,
            duration: state === 'speaking' ? 0.5 : state === 'listening' ? 1 : 2,
          }}
          style={{ borderColor: cfg.color }}
        >
          <span className="ai-center-text" style={{ color: cfg.color, textShadow: `0 0 12px ${cfg.glow}` }}>
            J.A.R.V.I.S
          </span>
        </motion.div>
      </motion.div>

      {/* Waveform */}
      <div className="voice-section">
        <div className="waveform-container">
          {bars.map((b, i) => (
            <motion.div key={i}
              className={`waveform-bar ${state === 'listening' || state === 'speaking' ? 'active' : ''}`}
              style={{ background: cfg.color, boxShadow: `0 0 4px ${cfg.glow}` }}
              animate={{
                height: state === 'listening' || state === 'speaking'
                  ? [4, 4 + Math.random() * 24, 4]
                  : b.h
              }}
              transition={{ repeat: Infinity, duration: 0.4 + Math.random() * 0.4, delay: b.delay }}
            />
          ))}
        </div>
      </div>

      {/* Connection + active status */}
      <div style={{ display: 'flex', gap: 8, marginTop: 10, justifyContent: 'center' }}>
        {/* Connection badge */}
        <div style={{
          padding: '3px 10px', borderRadius: 12,
          background: connected ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
          border: `1px solid ${connected ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)'}`,
          fontSize: 9, fontFamily: 'var(--font-display)', letterSpacing: 2,
          color: connected ? '#22c55e' : '#ef4444',
        }}>
          {connected ? '● CONNECTED' : '○ OFFLINE'}
        </div>

        {/* JARVIS active badge */}
        {jarvisActive && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            style={{
              padding: '3px 10px', borderRadius: 12,
              background: 'rgba(0,180,255,0.1)',
              border: '1px solid rgba(0,180,255,0.3)',
              fontSize: 9, fontFamily: 'var(--font-display)', letterSpacing: 2,
              color: 'var(--cyan)',
            }}
          >
            ● ACTIVE
          </motion.div>
        )}
      </div>

      {/* Status text */}
      <motion.div className="ai-status-text" key={state + '-text'} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
        {state === 'idle' && <><span className="greeting">Welcome back, Hari Sir.</span><br />All systems operational. Say "JARVIS" or clap to begin.</>}
        {state === 'listening' && 'I\'m listening, Sir... say your command.'}
        {state === 'thinking' && 'Processing your command, Sir...'}
        {state === 'executing' && 'Executing now, Sir...'}
        {state === 'speaking' && 'Speaking...'}
        {state === 'error' && 'Something went wrong. Trying again, Sir.'}
      </motion.div>
    </div>
  );
}
