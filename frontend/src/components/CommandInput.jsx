import React, { useState, useRef } from 'react';
import useStore from '../stores/useStore';

export default function CommandInput() {
  const [text, setText] = useState('');
  const sendCommand = useStore(s => s.sendCommand);
  const isRecording = useStore(s => s.isRecording);
  const setRecording = useStore(s => s.setRecording);
  const setAiState = useStore(s => s.setAiState);
  const mediaRef = useRef(null);
  const chunksRef = useRef([]);

  const submit = () => { if (text.trim()) { sendCommand(text.trim()); setText(''); } };

  const toggleRecord = async () => {
    if (isRecording) {
      mediaRef.current?.stop();
      setRecording(false);
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { sampleRate: 16000, channelCount: 1 } });
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      chunksRef.current = [];
      recorder.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        const buf = await blob.arrayBuffer();
        const b64 = btoa(String.fromCharCode(...new Uint8Array(buf)));
        const ws = useStore.getState().ws;
        if (ws && ws.readyState === 1) {
          ws.send(JSON.stringify({ type: 'audio', audio: b64 }));
        }
        setAiState('thinking');
      };
      mediaRef.current = recorder;
      recorder.start();
      setRecording(true);
      setAiState('listening');
    } catch (e) { console.error('Mic error:', e); }
  };

  return (
    <div className="cmd-input-bar">
      <button className="cmd-input-btn" onClick={() => sendCommand('take screenshot')} title="Screenshot">📷</button>
      <input className="cmd-input" value={text} onChange={e => setText(e.target.value)} onKeyDown={e => e.key === 'Enter' && submit()} placeholder="Type a command or ask J.A.R.V.I.S anything..." />
      <button className={`cmd-input-btn ${isRecording ? 'recording' : ''}`} onClick={toggleRecord} title="Voice Input">🎤</button>
      <button className="cmd-input-btn" onClick={submit} title="Send">➤</button>
    </div>
  );
}
