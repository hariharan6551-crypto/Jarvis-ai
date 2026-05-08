import React, { useState, useRef, useEffect, useCallback } from 'react';
import useStore from '../stores/useStore';

export default function CommandInput() {
  const [text, setText] = useState('');
  const sendCommand = useStore(s => s.sendCommand);
  const isRecording = useStore(s => s.isRecording);
  const setRecording = useStore(s => s.setRecording);
  const aiState = useStore(s => s.aiState);
  const setAiState = useStore(s => s.setAiState);
  const setTranscription = useStore(s => s.setTranscription);
  const recognitionRef = useRef(null);
  const [interim, setInterim] = useState('');
  const autoStarted = useRef(false);

  const initAndStart = useCallback(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return;

    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch (e) {}
    }

    const rec = new SR();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = 'en-US';

    rec.onstart = () => {
      setRecording(true);
      console.log('🎤 Always-on voice active — say "Jarvis" to give commands');
    };

    rec.onresult = (event) => {
      let interimT = '';
      let finalT = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const t = event.results[i][0].transcript;
        if (event.results[i].isFinal) finalT += t;
        else interimT += t;
      }

      if (interimT) {
        setInterim(interimT);
        // Check if wake word is being said
        if (interimT.toLowerCase().includes('jarvis')) {
          setAiState('listening');
        }
      }

      if (finalT.trim()) {
        setInterim('');
        const cmd = finalT.trim();
        const lower = cmd.toLowerCase();
        console.log('🗣️ Heard:', cmd);

        // Only process commands that contain "jarvis"
        if (lower.includes('jarvis')) {
          const cleaned = lower
            .replace(/hey\s+jarvis/gi, '')
            .replace(/jarvis/gi, '')
            .replace(/^\s*[,.\s]+/, '')
            .trim();

          if (cleaned) {
            setTranscription(cleaned);
            setAiState('thinking');
            sendCommand(cleaned);
          } else {
            setTranscription('jarvis');
            sendCommand('hello, I am here');
          }
        }
      }
    };

    rec.onerror = (event) => {
      console.log('Speech error:', event.error);
      if (event.error === 'not-allowed') {
        console.error('Mic denied! Click mic button to retry.');
        setRecording(false);
        return;
      }
      // Auto restart on other errors
    };

    rec.onend = () => {
      // Always restart — keep listening forever
      console.log('🔄 Restarting voice listener...');
      setTimeout(() => {
        try { rec.start(); } catch (e) {
          // If start fails, try again after delay
          setTimeout(() => { try { rec.start(); } catch (e2) {} }, 1000);
        }
      }, 300);
    };

    recognitionRef.current = rec;
    try { rec.start(); } catch (e) {
      console.error('Start failed, retrying...', e);
      setTimeout(() => { try { rec.start(); } catch (e2) {} }, 1000);
    }
  }, [setRecording, setAiState, setTranscription, sendCommand]);

  // AUTO START voice on page load
  useEffect(() => {
    if (!autoStarted.current) {
      autoStarted.current = true;
      // Small delay to let page settle
      const timer = setTimeout(() => {
        console.log('🚀 Auto-starting voice recognition...');
        initAndStart();
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [initAndStart]);

  // Cleanup
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch (e) {}
      }
    };
  }, []);

  const manualToggle = () => {
    if (isRecording) {
      if (recognitionRef.current) {
        recognitionRef.current.onend = null; // Prevent auto-restart
        try { recognitionRef.current.stop(); } catch (e) {}
        recognitionRef.current = null;
      }
      setRecording(false);
      setAiState('idle');
    } else {
      initAndStart();
    }
  };

  const submit = () => {
    if (text.trim()) {
      sendCommand(text.trim());
      setText('');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, flexShrink: 0 }}>
      {interim && interim.toLowerCase().includes('jarvis') && (
        <div style={{
          padding: '6px 16px', fontSize: 12, color: 'var(--cyan)',
          fontFamily: 'var(--font-mono)',
          background: 'rgba(0,180,255,0.08)', borderRadius: 8,
          border: '1px solid rgba(0,180,255,0.2)',
          animation: 'fadeInUp 0.2s ease',
        }}>
          🎤 Listening: {interim}
        </div>
      )}

      <div className="cmd-input-bar">
        <button className="cmd-input-btn" onClick={() => sendCommand('take screenshot')} title="Screenshot">📷</button>

        <input className="cmd-input" value={text} onChange={e => setText(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && submit()}
          placeholder={isRecording ? '🟢 Voice active — say "Jarvis" followed by your command' : 'Click mic or type a command...'}
        />

        <button className={`cmd-input-btn ${isRecording ? 'recording' : ''}`}
          onClick={manualToggle}
          title={isRecording ? 'Stop voice' : 'Start voice'}
          style={isRecording ? { background: '#22c55e', borderColor: '#22c55e', boxShadow: '0 0 12px rgba(34,197,94,0.5)' } : {}}>
          {isRecording ? '👂' : '🎤'}
        </button>

        <button className="cmd-input-btn" onClick={submit} title="Send">➤</button>
      </div>
    </div>
  );
}
