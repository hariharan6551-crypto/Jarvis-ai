import React, { useState, useRef, useEffect, useCallback } from 'react';
import useStore from '../stores/useStore';

export default function CommandInput() {
  const [text, setText] = useState('');
  const sendCommand = useStore(s => s.sendCommand);
  const isRecording = useStore(s => s.isRecording);
  const setRecording = useStore(s => s.setRecording);
  const setAiState = useStore(s => s.setAiState);
  const setTranscription = useStore(s => s.setTranscription);
  const addChatMessage = useStore(s => s.addChatMessage);
  const recognitionRef = useRef(null);
  const [continuous, setContinuous] = useState(false);
  const [interim, setInterim] = useState('');

  // Initialize Web Speech API
  const initRecognition = useCallback(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.error('Speech Recognition not supported in this browser');
      return null;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      setRecording(true);
      setAiState('listening');
      console.log('🎤 Voice recognition started');
    };

    recognition.onresult = (event) => {
      let interimTranscript = '';
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript;
        } else {
          interimTranscript += transcript;
        }
      }

      // Show interim results
      if (interimTranscript) {
        setInterim(interimTranscript);
        setTranscription(interimTranscript);
      }

      // Process final transcript
      if (finalTranscript.trim()) {
        setInterim('');
        const cmd = finalTranscript.trim();
        console.log('🗣️ Heard:', cmd);
        setTranscription(cmd);

        // Check for wake word in continuous mode
        if (continuous) {
          const lower = cmd.toLowerCase();
          if (lower.includes('jarvis')) {
            // Remove "jarvis" and send the command
            const cleaned = lower.replace(/hey\s+jarvis|jarvis/gi, '').trim();
            if (cleaned) {
              sendCommand(cleaned);
            } else {
              // Just said "Jarvis" - acknowledge
              sendCommand('hello');
            }
          }
        } else {
          // Direct mode - send everything
          sendCommand(cmd);
          stopRecognition();
        }
      }
    };

    recognition.onerror = (event) => {
      console.error('Speech error:', event.error);
      if (event.error === 'not-allowed') {
        alert('Microphone access denied. Please allow microphone in browser settings.');
      }
      if (!continuous) {
        setRecording(false);
        setAiState('idle');
      }
    };

    recognition.onend = () => {
      if (continuous && isRecording) {
        // Restart for continuous listening
        try { recognition.start(); } catch (e) {}
      } else {
        setRecording(false);
        setAiState('idle');
      }
    };

    return recognition;
  }, [continuous, setRecording, setAiState, setTranscription, sendCommand, isRecording]);

  const startRecognition = useCallback(() => {
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch (e) {}
    }
    const rec = initRecognition();
    if (rec) {
      recognitionRef.current = rec;
      try {
        rec.start();
      } catch (e) {
        console.error('Failed to start recognition:', e);
      }
    }
  }, [initRecognition]);

  const stopRecognition = useCallback(() => {
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch (e) {}
      recognitionRef.current = null;
    }
    setRecording(false);
    setAiState('idle');
    setInterim('');
    setContinuous(false);
  }, [setRecording, setAiState]);

  const toggleRecord = () => {
    if (isRecording) {
      stopRecognition();
    } else {
      setContinuous(false);
      startRecognition();
    }
  };

  const toggleContinuous = () => {
    if (continuous) {
      stopRecognition();
    } else {
      setContinuous(true);
      startRecognition();
    }
  };

  // Cleanup
  useEffect(() => {
    return () => { if (recognitionRef.current) { try { recognitionRef.current.stop(); } catch (e) {} } };
  }, []);

  const submit = () => { if (text.trim()) { sendCommand(text.trim()); setText(''); } };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, flexShrink: 0 }}>
      {/* Interim transcript display */}
      {interim && (
        <div style={{
          padding: '6px 16px', fontSize: 12, color: 'var(--cyan)',
          fontFamily: 'var(--font-mono)', opacity: 0.7,
          background: 'rgba(0,180,255,0.05)', borderRadius: 8,
          border: '1px solid var(--border-dim)',
        }}>
          🎤 {interim}
        </div>
      )}

      <div className="cmd-input-bar">
        {/* Screenshot button */}
        <button className="cmd-input-btn" onClick={() => sendCommand('take screenshot')} title="Screenshot">📷</button>

        {/* Text input */}
        <input className="cmd-input" value={text} onChange={e => setText(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && submit()}
          placeholder={isRecording ? (continuous ? '🔴 Always listening for "Jarvis"...' : '🎤 Listening... speak now') : 'Type a command or ask J.A.R.V.I.S anything...'}
        />

        {/* Push-to-talk mic button */}
        <button className={`cmd-input-btn ${isRecording && !continuous ? 'recording' : ''}`}
          onClick={toggleRecord} title="Push to Talk (click to speak)">
          🎤
        </button>

        {/* Continuous listening (wake word) button */}
        <button className={`cmd-input-btn ${continuous ? 'recording' : ''}`}
          onClick={toggleContinuous}
          title={continuous ? 'Stop continuous listening' : 'Always listen for "Jarvis"'}
          style={continuous ? { background: 'var(--purple)', borderColor: 'var(--purple)' } : {}}>
          {continuous ? '👂' : '🔊'}
        </button>

        {/* Send button */}
        <button className="cmd-input-btn" onClick={submit} title="Send">➤</button>
      </div>
    </div>
  );
}
