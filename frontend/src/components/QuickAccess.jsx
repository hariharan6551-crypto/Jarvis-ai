import React from 'react';
import useStore from '../stores/useStore';

const apps = [
  { name: 'Chrome', cmd: 'open chrome', icon: '🌐', color: '#4285f4' },
  { name: 'VS Code', cmd: 'open vs code', icon: '💻', color: '#007acc' },
  { name: 'Explorer', cmd: 'open file explorer', icon: '📁', color: '#f59e0b' },
  { name: 'Spotify', cmd: 'open spotify', icon: '🎵', color: '#1db954' },
  { name: 'YouTube', cmd: 'search youtube', icon: '▶️', color: '#ff0000' },
  { name: 'WhatsApp', cmd: 'open whatsapp', icon: '💬', color: '#25d366' },
  { name: 'Discord', cmd: 'open discord', icon: '🎮', color: '#5865f2' },
  { name: 'Terminal', cmd: 'open terminal', icon: '⌨️', color: '#a78bfa' },
];

export default function QuickAccess() {
  const sendCommand = useStore(s => s.sendCommand);
  return (
    <div className="panel">
      <div className="panel-title"><span className="panel-title-dot" />QUICK ACCESS</div>
      <div className="quick-access">
        {apps.map(a => (
          <button key={a.name} className="quick-btn" onClick={() => sendCommand(a.cmd)} title={a.name}>
            <span style={{ fontSize: 18 }}>{a.icon}</span>
            <span>{a.name}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
