import React from 'react';
import useStore from '../stores/useStore';

export default function RecentCommands() {
  const cmds = useStore(s => s.recentCommands);
  return (
    <div className="panel">
      <div className="panel-title"><span className="panel-title-dot" />RECENT COMMANDS</div>
      <div className="cmd-list">
        {cmds.length === 0 && <div style={{ fontSize: 12, color: 'var(--text-dim)' }}>No commands yet. Try saying something!</div>}
        {cmds.map(c => (
          <div key={c.id} className="cmd-item">
            <span className={`cmd-dot ${c.status}`} />
            <span className="cmd-text">{c.message || c.text}</span>
            <span className="cmd-time">{c.time}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
