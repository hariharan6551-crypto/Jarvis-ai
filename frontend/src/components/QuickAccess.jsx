import React from 'react';
import { motion } from 'framer-motion';
import useStore from '../stores/useStore';

const quickActions = [
  { icon: '🌐', label: 'Chrome', cmd: 'open chrome' },
  { icon: '📁', label: 'Files', cmd: 'open explorer' },
  { icon: '💻', label: 'VS Code', cmd: 'open vscode' },
  { icon: '📝', label: 'Notepad', cmd: 'open notepad' },
  { icon: '⚙️', label: 'Settings', cmd: 'open settings' },
  { icon: '🖥️', label: 'Terminal', cmd: 'open terminal' },
];

export default function QuickAccess() {
  const sendCommand = useStore(s => s.sendCommand);
  const chromeProfiles = useStore(s => s.chromeProfiles);

  return (
    <div className="panel quick-access-panel">
      <div className="panel-title"><span className="panel-title-dot" />QUICK ACTIONS</div>
      <div className="quick-grid">
        {quickActions.map((a, i) => (
          <motion.button
            key={a.label}
            className="quick-btn"
            whileHover={{ scale: 1.08, y: -2 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => sendCommand(a.cmd)}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            title={a.cmd}
          >
            <span className="quick-icon">{a.icon}</span>
            <span className="quick-label">{a.label}</span>
          </motion.button>
        ))}
      </div>

      {chromeProfiles.length > 0 && (
        <>
          <div className="panel-title" style={{ marginTop: 14, fontSize: 10 }}>
            <span className="panel-title-dot" style={{ background: '#4285f4' }} />CHROME PROFILES
          </div>
          <div className="profile-list">
            {chromeProfiles.map((p, i) => (
              <motion.button
                key={p.name || i}
                className="profile-btn"
                whileHover={{ scale: 1.03, x: 3 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => sendCommand(`open chrome and select ${p.name} account`)}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + i * 0.08 }}
              >
                <div className="profile-avatar">
                  {(p.name || 'U').charAt(0).toUpperCase()}
                </div>
                <div className="profile-info">
                  <div className="profile-name">{p.name}</div>
                  {p.email && <div className="profile-email">{p.email}</div>}
                </div>
                <div className="profile-arrow">→</div>
              </motion.button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
