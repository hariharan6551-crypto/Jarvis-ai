import React, { useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import useStore from './stores/useStore';
import BootSequence from './components/BootSequence';
import TitleBar from './components/TitleBar';
import Sidebar from './components/Sidebar';
import AICore from './components/AICore';
import SystemOverview from './components/SystemOverview';
import QuickAccess from './components/QuickAccess';
import RecentCommands from './components/RecentCommands';
import CommandInput from './components/CommandInput';
import ChatPanel from './components/ChatPanel';
import SettingsPanel from './components/SettingsPanel';
import DashboardPanel from './components/DashboardPanel';

const pageAnim = { initial: { opacity: 0, y: 20 }, animate: { opacity: 1, y: 0 }, exit: { opacity: 0, y: -20 }, transition: { duration: 0.3 } };

function HomePage() {
  const aiState = useStore(s => s.aiState);
  const aiResponse = useStore(s => s.aiResponse);
  const connected = useStore(s => s.connected);
  return (
    <div className="content-grid">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, overflow: 'auto' }}>
        <SystemOverview />
        <QuickAccess />
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <AICore state={aiState} />
      </div>
      <div className="right-panel">
        <div className="panel ai-assistant-panel">
          <div className="panel-title"><span className="panel-title-dot" />AI ASSISTANT</div>
          <div className="assistant-greeting">Hello, Hari</div>
          <div className="assistant-msg">{aiResponse || 'How can I assist you today?'}</div>
        </div>
        <RecentCommands />
        <div className="panel">
          <div className="panel-title"><span className="panel-title-dot" />SYSTEM ALERTS</div>
          <div className="sys-alert">
            <span className="sys-alert-icon">✓</span>
            <div className="sys-alert-text">
              <div className="sys-alert-title">All systems {connected ? 'operational' : 'connecting...'}</div>
              <div className="sys-alert-desc">{connected ? 'Running optimally' : 'Attempting backend connection'}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Speaks welcome message using browser TTS (instant, no backend needed)
function speakWelcome() {
  const synth = window.speechSynthesis;
  if (!synth) return;
  // Cancel any ongoing speech
  synth.cancel();
  const msg = new SpeechSynthesisUtterance("Welcome back Hari. All systems are operational. How may I assist you today?");
  msg.rate = 1.0;
  msg.pitch = 0.9;
  msg.volume = 1.0;
  msg.lang = 'en-US';
  // Try to find a good male voice
  const voices = synth.getVoices();
  const preferred = voices.find(v => v.name.includes('Google US English') || v.name.includes('David') || v.name.includes('Male'));
  if (preferred) msg.voice = preferred;
  synth.speak(msg);
}

// Also try backend TTS (higher quality) if available
async function speakWelcomeBackend() {
  try {
    const res = await fetch('http://127.0.0.1:8765/api/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: "Welcome back Hari. All systems are operational. How may I assist you today?" }),
    });
    const data = await res.json();
    if (data.audio) {
      const binary = atob(data.audio);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      const blob = new Blob([bytes], { type: 'audio/mp3' });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.play().catch(() => {
        // If backend TTS fails to play, use browser TTS
        speakWelcome();
      });
      audio.onended = () => URL.revokeObjectURL(url);
      return;
    }
  } catch (e) {}
  // Fallback to browser TTS
  speakWelcome();
}

// Auto-start voice recognition globally
function autoStartVoice() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return null;

  const rec = new SR();
  rec.continuous = true;
  rec.interimResults = true;
  rec.lang = 'en-US';

  rec.onstart = () => {
    useStore.getState().setRecording(true);
    console.log('🎤 JARVIS voice active — say "Jarvis" followed by your command');
  };

  rec.onresult = (event) => {
    let finalT = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      if (event.results[i].isFinal) {
        finalT += event.results[i][0].transcript;
      }
    }

    if (finalT.trim()) {
      const cmd = finalT.trim();
      const lower = cmd.toLowerCase();
      console.log('🗣️ Heard:', cmd);

      if (lower.includes('jarvis')) {
        const cleaned = lower.replace(/hey\s+jarvis|jarvis/gi, '').replace(/^\s*[,.\s]+/, '').trim();
        useStore.getState().setAiState('thinking');
        if (cleaned) {
          useStore.getState().setTranscription(cleaned);
          useStore.getState().sendCommand(cleaned);
        } else {
          useStore.getState().sendCommand('hello');
        }
      }
    }
  };

  rec.onerror = (event) => {
    console.log('Voice error:', event.error);
  };

  rec.onend = () => {
    // Always restart
    setTimeout(() => {
      try { rec.start(); } catch (e) {
        setTimeout(() => { try { rec.start(); } catch (e2) {} }, 1000);
      }
    }, 300);
  };

  try { rec.start(); } catch (e) {
    setTimeout(() => { try { rec.start(); } catch (e2) {} }, 1000);
  }

  return rec;
}

export default function App() {
  const showBoot = useStore(s => s.showBoot);
  const setShowBoot = useStore(s => s.setShowBoot);
  const currentPage = useStore(s => s.currentPage);
  const setPage = useStore(s => s.setPage);
  const connectWs = useStore(s => s.connectWs);
  const fetchStatus = useStore(s => s.fetchStatus);
  const voiceRef = useRef(null);

  const onBootComplete = useCallback(() => {
    setShowBoot(false);

    // Auto-speak welcome message after boot
    setTimeout(() => {
      speakWelcomeBackend();
    }, 500);

    // Auto-start voice recognition after welcome
    setTimeout(() => {
      if (!voiceRef.current) {
        voiceRef.current = autoStartVoice();
      }
    }, 1500);
  }, [setShowBoot]);

  useEffect(() => {
    // Connect WebSocket and fetch status
    const t = setTimeout(() => { connectWs(); fetchStatus(); }, 500);
    const interval = setInterval(fetchStatus, 5000);

    // Load voices for browser TTS
    if (window.speechSynthesis) {
      window.speechSynthesis.getVoices();
    }

    return () => {
      clearTimeout(t);
      clearInterval(interval);
      if (voiceRef.current) {
        try { voiceRef.current.onend = null; voiceRef.current.stop(); } catch (e) {}
      }
    };
  }, [connectWs, fetchStatus]);

  const renderPage = () => {
    switch (currentPage) {
      case 'home': return <HomePage />;
      case 'system': case 'commands': return <motion.div {...pageAnim} style={{ flex: 1, overflow: 'auto' }}><div className="panel" style={{ height: '100%' }}><DashboardPanel /></div></motion.div>;
      case 'chat': return <motion.div {...pageAnim} style={{ flex: 1 }}><div className="panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}><ChatPanel /></div></motion.div>;
      case 'settings': case 'config': return <motion.div {...pageAnim} style={{ flex: 1, overflow: 'auto' }}><div className="panel"><div className="panel-title"><span className="panel-title-dot" />SETTINGS</div><SettingsPanel /></div></motion.div>;
      default: return <motion.div {...pageAnim} style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><div style={{ textAlign: 'center', color: 'var(--text-dim)' }}><div style={{ fontSize: 48, marginBottom: 16 }}>🚀</div><div style={{ fontFamily: 'var(--font-display)', fontSize: 14, letterSpacing: 3 }}>{currentPage.toUpperCase()} MODULE</div><div style={{ fontSize: 12, marginTop: 8 }}>Coming soon</div></div></motion.div>;
    }
  };

  return (
    <>
      {showBoot && <BootSequence onComplete={onBootComplete} />}
      <TitleBar />
      <div className="app-layout">
        <Sidebar currentPage={currentPage} onNavigate={setPage} />
        <main className="main-content">
          <AnimatePresence mode="wait">{renderPage()}</AnimatePresence>
          <CommandInput />
        </main>
      </div>
      <div className="bottom-bar">
        <span className="bottom-item">VOICE CONTROL</span>
        <span className="bottom-item">SYSTEM CONTROL</span>
        <span className="bottom-item">AI ASSISTANCE</span>
        <span className="bottom-item">REAL TIME MONITORING</span>
        <span className="bottom-item">CINEMATIC UI/UX</span>
      </div>
    </>
  );
}
