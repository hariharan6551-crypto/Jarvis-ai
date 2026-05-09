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
import DiagnosticsPanel from './components/DiagnosticsPanel';
import NotificationToast, { showToast } from './components/NotificationToast';

const pageAnim = { initial: { opacity: 0, y: 20 }, animate: { opacity: 1, y: 0 }, exit: { opacity: 0, y: -20 }, transition: { duration: 0.3 } };

function HomePage() {
  const aiState = useStore(s => s.aiState);
  const aiResponse = useStore(s => s.aiResponse);
  const connected = useStore(s => s.connected);
  const jarvisActive = useStore(s => s.jarvisActive);
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
              <div className="sys-alert-desc">
                {jarvisActive ? '🟢 JARVIS active — listening' : connected ? 'Running optimally' : 'Attempting backend connection'}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Speak using browser TTS ──────────────────────────────────────
function speakBrowser(text) {
  const synth = window.speechSynthesis;
  if (!synth || !text) return;
  synth.cancel();
  const msg = new SpeechSynthesisUtterance(text);
  msg.rate = 1.0;
  msg.pitch = 0.9;
  msg.volume = 1.0;
  msg.lang = 'en-US';
  const voices = synth.getVoices();
  const preferred = voices.find(v => v.name.includes('Google US English') || v.name.includes('David') || v.name.includes('Male'));
  if (preferred) msg.voice = preferred;
  synth.speak(msg);
}

// ─── Backend TTS with browser fallback ────────────────────────────
async function speakBackend(text) {
  try {
    const res = await fetch('http://127.0.0.1:8765/api/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    const data = await res.json();
    if (data.audio) {
      const binary = atob(data.audio);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      const blob = new Blob([bytes], { type: 'audio/mp3' });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.play().catch(() => speakBrowser(text));
      audio.onended = () => URL.revokeObjectURL(url);
      return;
    }
  } catch (e) { /* fallback */ }
  speakBrowser(text);
}

// ─── Voice Recognition (Web Speech API) ──────────────────────────
// Handles wake word "JARVIS" detection from voice input.
// Clap detection is handled by the BACKEND via sounddevice.
function startVoiceRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    console.warn('Web Speech API not supported in this browser');
    return null;
  }

  const rec = new SR();
  rec.continuous = true;
  rec.interimResults = false; // Only final results for reliability
  rec.lang = 'en-US';
  rec.maxAlternatives = 3;

  rec.onstart = () => {
    useStore.getState().setRecording(true);
    console.log('🎤 Voice recognition active — say "JARVIS" to activate');
  };

  rec.onresult = (event) => {
    for (let i = event.resultIndex; i < event.results.length; i++) {
      if (!event.results[i].isFinal) continue;

      // Check all alternatives for better wake word detection
      for (let alt = 0; alt < event.results[i].length; alt++) {
        const transcript = event.results[i][alt].transcript.trim();
        const lower = transcript.toLowerCase();

        if (!lower) continue;
        console.log('🗣️ Heard:', transcript);

        // ━━━ WAKE WORD: "JARVIS" ━━━
        // Check if any variant of "jarvis" is spoken
        const hasWakeWord = /jarvis|j\.?a\.?r\.?v\.?i\.?s\.?/i.test(lower);

        if (hasWakeWord) {
          const store = useStore.getState();

          // Count how many times "jarvis" appears (urgent call)
          const jarvisCount = (lower.match(/jarvis|j\.?a\.?r\.?v\.?i\.?s\.?/gi) || []).length;

          // Extract command after the wake word
          const cleaned = lower
            .replace(/hey\s+(jarvis|j\.?a\.?r\.?v\.?i\.?s\.?)|(jarvis|j\.?a\.?r\.?v\.?i\.?s\.?)/gi, '')
            .replace(/^\s*[,.\s]+/, '')
            .trim();

          // Activate JARVIS
          store.setJarvisActive(true);
          store.setAiState('listening');

          if (jarvisCount >= 2) {
            // Multiple "JARVIS" calls = urgent
            console.log('🚨 Urgent wake word ×' + jarvisCount);
            showToast({ title: 'J.A.R.V.I.S', message: "Yes, I'm here. How can I help?", type: 'info' });
            store.addChatMessage({ role: 'assistant', content: "Yes, I'm here. How can I help?" });
            speakBackend("Yes, I'm here. How can I help?");
          } else if (cleaned) {
            // Wake word + command
            showToast({ title: 'J.A.R.V.I.S', message: `Processing: "${cleaned}"`, type: 'info' });
            store.sendCommand(cleaned);
          } else {
            // Just wake word, no command
            showToast({ title: 'J.A.R.V.I.S', message: 'Hey Hari, how can I help you?', type: 'info' });
            store.addChatMessage({ role: 'assistant', content: 'Hey Hari, how can I help you?' });
            speakBackend('Hey Hari, how can I help you?');
          }

          // Found wake word in this alternative, stop checking others
          break;
        }

        // ━━━ DEACTIVATION COMMANDS ━━━
        if (/^(turn off|go to sleep|stop listening|deactivate|good\s*night|shut down)$/i.test(lower)) {
          const store = useStore.getState();
          store.setJarvisActive(false);
          store.setAiState('idle');
          showToast({ title: 'J.A.R.V.I.S', message: 'Going offline Hari. Call me anytime.', type: 'info' });
          store.addChatMessage({ role: 'assistant', content: 'Going offline Hari. Call me anytime.' });
          speakBackend('Going offline Hari. Call me anytime.');
          break;
        }

        // If JARVIS is active and user speaks a command without wake word
        if (useStore.getState().jarvisActive) {
          const store = useStore.getState();
          store.sendCommand(transcript);
          break;
        }
      }
    }
  };

  rec.onerror = (event) => {
    if (event.error !== 'no-speech') {
      console.warn('Voice error:', event.error);
    }
  };

  // Auto-restart on end to keep listening forever
  rec.onend = () => {
    useStore.getState().setRecording(false);
    if (!rec._stopped) {
      setTimeout(() => {
        try { rec.start(); } catch (e) {
          setTimeout(() => { try { rec.start(); } catch (e2) {} }, 1500);
        }
      }, 500);
    }
  };

  rec._stopped = false;
  try { rec.start(); } catch (e) {
    setTimeout(() => { try { rec.start(); } catch (e2) {} }, 1500);
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
    setTimeout(() => speakBackend("Welcome back Hari. All systems are operational. How may I assist you today?"), 500);
    setTimeout(() => {
      if (!voiceRef.current) {
        voiceRef.current = startVoiceRecognition();
      }
    }, 1500);
  }, [setShowBoot]);

  useEffect(() => {
    const t = setTimeout(() => {
      connectWs();
      fetchStatus();
      useStore.getState().fetchProfiles();
      const saved = localStorage.getItem('jarvis-theme') || 'dark';
      document.documentElement.setAttribute('data-theme', saved);
    }, 500);
    const interval = setInterval(fetchStatus, 8000);

    if (window.speechSynthesis) {
      window.speechSynthesis.getVoices();
    }

    return () => {
      clearTimeout(t);
      clearInterval(interval);
      if (voiceRef.current) {
        try { voiceRef.current._stopped = true; voiceRef.current.onend = null; voiceRef.current.stop(); } catch (e) {}
      }
    };
  }, [connectWs, fetchStatus]);

  const renderPage = () => {
    switch (currentPage) {
      case 'home': return <HomePage />;
      case 'system': case 'commands': return <motion.div {...pageAnim} style={{ flex: 1, overflow: 'auto' }}><div className="panel" style={{ height: '100%' }}><DashboardPanel /></div></motion.div>;
      case 'chat': return <motion.div {...pageAnim} style={{ flex: 1 }}><div className="panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}><ChatPanel /></div></motion.div>;
      case 'settings': case 'config': return <motion.div {...pageAnim} style={{ flex: 1, overflow: 'auto' }}><div className="panel"><div className="panel-title"><span className="panel-title-dot" />SETTINGS</div><SettingsPanel /></div></motion.div>;
      case 'diagnostics': return <motion.div {...pageAnim} style={{ flex: 1, overflow: 'auto' }}><div className="panel"><DiagnosticsPanel /></div></motion.div>;
      default: return <motion.div {...pageAnim} style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><div style={{ textAlign: 'center', color: 'var(--text-dim)' }}><div style={{ fontSize: 48, marginBottom: 16 }}>🚀</div><div style={{ fontFamily: 'var(--font-display)', fontSize: 14, letterSpacing: 3 }}>{currentPage.toUpperCase()} MODULE</div><div style={{ fontSize: 12, marginTop: 8 }}>Coming soon</div></div></motion.div>;
    }
  };

  return (
    <>
      {showBoot && <BootSequence onComplete={onBootComplete} />}
      <NotificationToast />
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
