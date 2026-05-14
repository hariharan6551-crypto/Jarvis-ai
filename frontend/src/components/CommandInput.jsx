import React, { useState } from 'react';
import useStore from '../stores/useStore';

export default function CommandInput() {
  const [text, setText] = useState('');
  const sendCommand = useStore(s => s.sendCommand);
  const isRecording = useStore(s => s.isRecording);
  const aiState = useStore(s => s.aiState);
  const transcription = useStore(s => s.transcription);
  const jarvisActive = useStore(s => s.jarvisActive);
  const pushToTalkActive = useStore(s => s.pushToTalkActive);
  const isSpeaking = useStore(s => s.isSpeaking);

  const submit = () => {
    if (text.trim()) {
      sendCommand(text.trim());
      setText('');
    }
  };

  // Push-to-talk: click the big mic button to speak a command
  const handlePushToTalk = () => {
    if (window._jarvisPushToTalk) {
      window._jarvisPushToTalk();
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
            pushToTalkActive
              ? '🎤 Listening... speak your command now'
              : jarvisActive
                ? '🟢 JARVIS active — speak or type your command'
                : isRecording
                  ? '🎤 Voice active — say "JARVIS" or click 🎙️ to speak'
                  : '💬 Type a command here or click 🎙️ to speak'
          }
        />

        {/* ━━━ PUSH-TO-TALK MIC BUTTON (PRIMARY VOICE INPUT) ━━━ */}
        <button
          onClick={handlePushToTalk}
          disabled={isSpeaking || aiState === 'thinking'}
          title={pushToTalkActive ? 'Listening...' : 'Click to speak a command (Push-to-Talk)'}
          style={{
            width: 44, height: 44, borderRadius: '50%', display: 'flex',
            alignItems: 'center', justifyContent: 'center', fontSize: 20,
            background: pushToTalkActive
              ? 'rgba(239,68,68,0.25)'
              : 'rgba(0,180,255,0.15)',
            border: `2px solid ${pushToTalkActive ? 'var(--red)' : 'var(--cyan)'}`,
            color: pushToTalkActive ? 'var(--red)' : 'var(--cyan)',
            cursor: isSpeaking ? 'not-allowed' : 'pointer',
            boxShadow: pushToTalkActive
              ? '0 0 20px rgba(239,68,68,0.5), inset 0 0 10px rgba(239,68,68,0.2)'
              : '0 0 12px rgba(0,180,255,0.3)',
            animation: pushToTalkActive ? 'pulse-dot 0.8s ease infinite' : 'none',
            transition: 'all 0.2s ease',
            flexShrink: 0,
          }}
        >
          {pushToTalkActive ? '⏺' : '🎙️'}
        </button>

        {/* Voice status indicators */}
        <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
          {/* Continuous listening status */}
          <div style={{
            width: 28, height: 28, borderRadius: '50%', display: 'flex',
            alignItems: 'center', justifyContent: 'center', fontSize: 12,
            background: isRecording ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)',
            border: `1px solid ${isRecording ? 'var(--green)' : 'var(--red)'}`,
            color: isRecording ? 'var(--green)' : 'var(--red)',
            boxShadow: isRecording ? '0 0 8px rgba(34,197,94,0.3)' : 'none',
          }} title={isRecording ? 'Background listening active (say "JARVIS")' : 'Background listening inactive'}>
            {isRecording ? '🟢' : '🔴'}
          </div>

          {/* JARVIS active indicator */}
          <div style={{
            width: 28, height: 28, borderRadius: '50%', display: 'flex',
            alignItems: 'center', justifyContent: 'center', fontSize: 12,
            background: jarvisActive ? 'rgba(0,180,255,0.15)' : 'rgba(100,100,100,0.15)',
            border: `1px solid ${jarvisActive ? 'rgba(0,180,255,0.5)' : 'rgba(100,100,100,0.3)'}`,
            color: jarvisActive ? 'var(--cyan)' : 'var(--text-dim)',
            boxShadow: jarvisActive ? '0 0 8px rgba(0,180,255,0.3)' : 'none',
            animation: jarvisActive ? 'pulse-dot 2s ease infinite' : 'none',
          }} title={jarvisActive ? 'JARVIS active — listening for commands' : 'JARVIS inactive — say "JARVIS" or click mic'}>
            {jarvisActive ? '👂' : '💤'}
          </div>
        </div>

        <button className="cmd-input-btn" onClick={submit} title="Send">➤</button>
      </div>

      {/* Voice help text */}
      <div style={{
        fontSize: 10, color: 'var(--text-dim)', textAlign: 'center',
        fontFamily: 'var(--font-mono)', letterSpacing: 0.5,
        padding: '2px 0',
      }}>
        {pushToTalkActive
          ? '🔴 RECORDING — Speak now...'
          : isSpeaking
            ? '🔊 JARVIS is speaking...'
            : isRecording
              ? '🟢 Say "JARVIS" to activate • Or click 🎙️ for push-to-talk'
              : '⚪ Click 🎙️ to speak a command'
        }
      </div>
    </div>
  );
}
