import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

let _showToast = null;

/** Call this from anywhere to show a toast: showToast({ title, message, type }) */
export function showToast({ title = 'J.A.R.V.I.S', message = '', type = 'info', duration = 4000 }) {
  if (_showToast) _showToast({ title, message, type, duration, id: Date.now() });
}

const typeStyles = {
  info: { bg: 'rgba(0,180,255,0.12)', border: 'rgba(0,180,255,0.3)', icon: 'ℹ️' },
  success: { bg: 'rgba(34,197,94,0.12)', border: 'rgba(34,197,94,0.3)', icon: '✓' },
  warning: { bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.3)', icon: '⚠' },
  error: { bg: 'rgba(239,68,68,0.12)', border: 'rgba(239,68,68,0.3)', icon: '✗' },
};

export default function NotificationToast() {
  const [toasts, setToasts] = useState([]);

  useEffect(() => {
    _showToast = (toast) => {
      setToasts(prev => [...prev.slice(-4), toast]);
      setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== toast.id));
      }, toast.duration);
    };
    return () => { _showToast = null; };
  }, []);

  return (
    <div style={{
      position: 'fixed', top: 50, right: 16, zIndex: 10000,
      display: 'flex', flexDirection: 'column', gap: 8,
      pointerEvents: 'none', maxWidth: 360,
    }}>
      <AnimatePresence>
        {toasts.map(toast => {
          const style = typeStyles[toast.type] || typeStyles.info;
          return (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, x: 80, scale: 0.9 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 80, scale: 0.9 }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
              style={{
                padding: '10px 16px', borderRadius: 10,
                background: style.bg, border: `1px solid ${style.border}`,
                backdropFilter: 'blur(12px)',
                pointerEvents: 'auto', cursor: 'pointer',
                boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
              }}
              onClick={() => setToasts(prev => prev.filter(t => t.id !== toast.id))}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 16 }}>{style.icon}</span>
                <div>
                  <div style={{
                    fontFamily: 'var(--font-display)', fontSize: 10, letterSpacing: 1.5,
                    color: 'var(--text-primary)', marginBottom: 2,
                  }}>
                    {toast.title}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                    {toast.message}
                  </div>
                </div>
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
