import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const lines = [
  'Initializing neural network...',
  'Loading AI models...',
  'Connecting voice pipeline...',
  'Calibrating automation engine...',
  'Scanning system resources...',
  'All systems nominal.',
];

export default function BootSequence({ onComplete }) {
  const [step, setStep] = useState(0);
  const [done, setDone] = useState(false);

  useEffect(() => {
    const t = setInterval(() => setStep(s => { if (s < lines.length - 1) return s + 1; clearInterval(t); return s; }), 500);
    const end = setTimeout(() => { setDone(true); setTimeout(onComplete, 800); }, 4000);
    return () => { clearInterval(t); clearTimeout(end); };
  }, [onComplete]);

  return (
    <AnimatePresence>
      {!done && (
        <motion.div className="boot-screen" exit={{ opacity: 0 }} transition={{ duration: 0.8 }}>
          <div className="boot-logo"><span className="boot-logo-text">J.A.R.V.I.S</span></div>
          <div className="boot-title">J.A.R.V.I.S</div>
          <div className="boot-status">
            {lines.slice(0, step + 1).map((l, i) => (
              <motion.div key={i} className="boot-status-line" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}>
                {l}
              </motion.div>
            ))}
          </div>
          <div className="boot-progress"><div className="boot-progress-fill" /></div>
          {step >= lines.length - 1 && <div className="boot-online">SYSTEM ONLINE</div>}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
