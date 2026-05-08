import React, { useState } from 'react';
import useStore from '../stores/useStore';

export default function CommandInput() {
  const [text, setText] = useState('');
  const sendCommand = useStore(s => s.sendCommand);
  const isRecording = useStore(s => s.isRecording);
  const aiState = useStore(s => s.aiState);
  const transcription = useStore(s => s.transcription);
  const jarvisActive = useStore(s => s.jarvisActive);

  const submit = () => {
    if (text.trim()) {
      sendCommand(text.trim());
      setText('');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, flexShrink: 0 }}>
      {/* Show what JARVIS heard */}
      {aiState === 'listening' && transcription && (
        <div style={{
          padding: '6px 16px', fontSize: 12, color: 'var(--cyan)',
          fontFamily: 'var(--font-mono)',
          background: 'rgba(0,180,255,0.08)', borderRadius: 8,
          border: '1px solid rgba(0,180,255,0.2)',
        }}>
          🎤 {transcription}
        </div>
      )}

      <div className="cmd-input-bar">
        <button className="cmd-input-btn" onClick={() => sendCommand('take screenshot')} title="Screenshot">📷</button>

        <input className="cmd-input" value={text} onChange={e => setText(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && submit()}
          placeholder={
            jarvisActive
              ? '🟢 JARVIS active — speak or type your command'
              : isRecording
                ? '🎤 Voice active — say "JARVIS" or clap to activate'
                : '🔴 Voice inactive — type a command here'
          }
        />

        {/* Voice + clap status indicator */}
        <div style={{
          display: 'flex', gap: 4, alignItems: 'center',
        }}>
          {/* Mic status */}
          <div style={{
            width: 32, height: 32, borderRadius: '50%', display: 'flex',
            alignItems: 'center', justifyContent: 'center', fontSize: 14,
            background: isRecording ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)',
            border: `1px solid ${isRecording ? 'var(--green)' : 'var(--red)'}`,
            color: isRecording ? 'var(--green)' : 'var(--red)',
            boxShadow: isRecording ? '0 0 12px rgba(34,197,94,0.4)' : 'none',
            animation: isRecording ? 'pulse-dot 2s ease infinite' : 'none',
          }} title={isRecording ? 'Mic active' : 'Mic inactive'}>
            {isRecording ? '🎤' : '🔇'}
          </div>

          {/* JARVIS active indicator */}
          <div style={{
            width: 32, height: 32, borderRadius: '50%', display: 'flex',
            alignItems: 'center', justifyContent: 'center', fontSize: 14,
            background: jarvisActive ? 'rgba(0,180,255,0.15)' : 'rgba(100,100,100,0.15)',
            border: `1px solid ${jarvisActive ? 'rgba(0,180,255,0.5)' : 'rgba(100,100,100,0.3)'}`,
            color: jarvisActive ? 'var(--cyan)' : 'var(--text-dim)',
            boxShadow: jarvisActive ? '0 0 12px rgba(0,180,255,0.4)' : 'none',
            animation: jarvisActive ? 'pulse-dot 2s ease infinite' : 'none',
          }} title={jarvisActive ? 'JARVIS active (double-clap to deactivate)' : 'JARVIS inactive (clap to activate)'}>
            {jarvisActive ? '👂' : '💤'}
          </div>
        </div>

        <button className="cmd-input-btn" onClick={submit} title="Send">➤</button>
      </div>
    </div>
  );
}
