import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const bootLines = [
  { text: '> Initializing J.A.R.V.I.S neural core...', icon: '🧠', delay: 0 },
  { text: '> Loading AI provider: Gemini 1.5 Flash', icon: '⚡', delay: 400 },
  { text: '> Connecting voice pipeline (Edge TTS)...', icon: '🎤', delay: 800 },
  { text: '> Calibrating automation engine...', icon: '⚙️', delay: 1200 },
  { text: '> Mounting desktop control modules...', icon: '🖥️', delay: 1600 },
  { text: '> Initializing memory engine (SQLite + ChromaDB)...', icon: '💾', delay: 2000 },
  { text: '> Scanning system resources...', icon: '📊', delay: 2400 },
  { text: '> Loading weather service (Chennai, TN)...', icon: '🌤️', delay: 2700 },
  { text: '> Activating clap detection module...', icon: '👏', delay: 3000 },
  { text: '> All systems nominal. Status: ONLINE', icon: '✅', delay: 3300 },
];

const diagnostics = [
  { label: 'CPU', value: 'OK', color: '#22c55e' },
  { label: 'RAM', value: 'OK', color: '#22c55e' },
  { label: 'AI', value: 'READY', color: '#00b4ff' },
  { label: 'VOICE', value: 'ACTIVE', color: '#00b4ff' },
  { label: 'NET', value: 'ONLINE', color: '#22c55e' },
  { label: 'DISK', value: 'OK', color: '#22c55e' },
];

export default function BootSequence({ onComplete }) {
  const [visibleLines, setVisibleLines] = useState(0);
  const [progress, setProgress] = useState(0);
  const [phase, setPhase] = useState('boot'); // boot, diagnostics, ready
  const [done, setDone] = useState(false);
  const timerRef = useRef(null);

  useEffect(() => {
    // Animate lines appearing
    bootLines.forEach((line, i) => {
      setTimeout(() => setVisibleLines(i + 1), line.delay);
    });

    // Progress bar
    const progressInterval = setInterval(() => {
      setProgress(p => {
        if (p >= 100) { clearInterval(progressInterval); return 100; }
        return p + 2;
      });
    }, 70);

    // Phase transitions
    setTimeout(() => setPhase('diagnostics'), 3400);
    setTimeout(() => setPhase('ready'), 4200);
    setTimeout(() => { setDone(true); setTimeout(onComplete, 800); }, 5000);

    return () => {
      clearInterval(progressInterval);
    };
  }, [onComplete]);

  const now = new Date();
  const timeStr = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  const dateStr = now.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });

  return (
    <AnimatePresence>
      {!done && (
        <motion.div className="boot-screen" exit={{ opacity: 0 }} transition={{ duration: 0.8 }}>
          {/* Scanline effect */}
          <div style={{
            position: 'absolute', inset: 0, pointerEvents: 'none',
            background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,180,255,0.03) 2px, rgba(0,180,255,0.03) 4px)',
            zIndex: 1,
          }} />

          {/* Logo */}
          <motion.div className="boot-logo"
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: 'spring', duration: 0.8 }}
          >
            <span className="boot-logo-text">J.A.R.V.I.S</span>
          </motion.div>

          {/* Title */}
          <motion.div className="boot-title"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.6 }}
          >
            J . A . R . V . I . S
          </motion.div>

          <motion.div style={{ fontSize: 11, color: 'var(--text-dim)', letterSpacing: 4, fontFamily: 'var(--font-display)', marginTop: 6 }}
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}
          >
            JUST A RATHER VERY INTELLIGENT SYSTEM
          </motion.div>

          {/* Boot lines */}
          <div className="boot-status" style={{ marginTop: 24, maxWidth: 420, textAlign: 'left' }}>
            {bootLines.slice(0, visibleLines).map((line, i) => (
              <motion.div key={i} className="boot-status-line"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3 }}
                style={{ display: 'flex', gap: 8, alignItems: 'center' }}
              >
                <span style={{ width: 18, textAlign: 'center' }}>{line.icon}</span>
                <span style={{
                  color: i === visibleLines - 1 && i === bootLines.length - 1
                    ? 'var(--green)' : 'var(--text-dim)'
                }}>{line.text}</span>
              </motion.div>
            ))}
          </div>

          {/* Progress bar */}
          <div className="boot-progress" style={{ width: 320, marginTop: 20 }}>
            <div className="boot-progress-fill" style={{ width: `${progress}%`, transition: 'width 0.15s linear' }} />
          </div>
          <div style={{ fontSize: 10, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', marginTop: 6 }}>
            {progress}% LOADED
          </div>

          {/* Diagnostics grid */}
          {phase !== 'boot' && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
              style={{ display: 'flex', gap: 16, marginTop: 20 }}
            >
              {diagnostics.map((d, i) => (
                <motion.div key={i}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: i * 0.08 }}
                  style={{
                    padding: '6px 12px', borderRadius: 6,
                    border: `1px solid ${d.color}40`,
                    background: `${d.color}10`,
                    textAlign: 'center', minWidth: 50,
                  }}
                >
                  <div style={{ fontSize: 9, color: 'var(--text-dim)', fontFamily: 'var(--font-display)', letterSpacing: 1 }}>{d.label}</div>
                  <div style={{ fontSize: 10, color: d.color, fontWeight: 600, fontFamily: 'var(--font-mono)', marginTop: 2 }}>{d.value}</div>
                </motion.div>
              ))}
            </motion.div>
          )}

          {/* SYSTEM ONLINE */}
          {phase === 'ready' && (
            <motion.div
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ type: 'spring', duration: 0.5 }}
              className="boot-online"
            >
              ● SYSTEM ONLINE
            </motion.div>
          )}

          {/* Time & date */}
          <motion.div style={{
            position: 'absolute', bottom: 30, fontSize: 11,
            color: 'var(--text-dim)', fontFamily: 'var(--font-mono)',
            textAlign: 'center', letterSpacing: 1,
          }} initial={{ opacity: 0 }} animate={{ opacity: 0.6 }} transition={{ delay: 1 }}>
            {dateStr} — {timeStr}<br />
            Chennai, Tamil Nadu, India
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
