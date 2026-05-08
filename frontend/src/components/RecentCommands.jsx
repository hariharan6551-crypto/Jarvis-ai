import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import useStore from '../stores/useStore';

export default function RecentCommands() {
  const cmds = useStore(s => s.recentCommands);

  return (
    <div className="panel">
      <div className="panel-title"><span className="panel-title-dot" />RECENT COMMANDS</div>
      <div className="cmd-list">
        <AnimatePresence>
          {cmds.length === 0 && (
            <div style={{ fontSize: 11, color: 'var(--text-dim)', textAlign: 'center', padding: 10 }}>
              No commands yet — say "Jarvis" to start
            </div>
          )}
          {cmds.slice(0, 6).map((cmd, i) => (
            <motion.div
              key={cmd.id}
              className="cmd-item"
              initial={{ opacity: 0, x: -15 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.25, delay: i * 0.03 }}
            >
              <span className={`cmd-dot ${cmd.status}`} />
              <span className="cmd-text">
                {(cmd.message || cmd.text || '').substring(0, 60)}
                {(cmd.message || cmd.text || '').length > 60 ? '…' : ''}
              </span>
              {cmd.steps > 1 && (
                <span style={{ fontSize: 9, color: 'var(--purple-bright)', fontFamily: 'var(--font-mono)' }}>
                  {cmd.steps}★
                </span>
              )}
              <span className="cmd-time">{cmd.time}</span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
