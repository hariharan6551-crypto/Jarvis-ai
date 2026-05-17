import React, { useEffect, useCallback, useRef, useState } from 'react';
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
import WeatherWidget from './components/WeatherWidget';
import NotificationToast, { showToast } from './components/NotificationToast';

const pageAnim = { initial: { opacity: 0, y: 20 }, animate: { opacity: 1, y: 0 }, exit: { opacity: 0, y: -20 }, transition: { duration: 0.3 } };

// ─── Clean Home Page ──────────────────────────────────────────────
function HomePage() {
  const aiState = useStore(s => s.aiState);
  const aiResponse = useStore(s => s.aiResponse);
  const connected = useStore(s => s.connected);
  const jarvisActive = useStore(s => s.jarvisActive);

  return (
    <div className="home-layout">
      {/* Left Column — System Info */}
      <div className="home-left">
        <SystemOverview />
        <WeatherWidget />
        <QuickAccess />
      </div>

      {/* Center Column — AI Core + Status */}
      <div className="home-center">
        <AICore state={aiState} />
        <div className="center-status">
          <div className="status-badge" data-state={aiState}>
            <span className="status-dot" />
            <span className="status-text">
              {connected ? (
                aiState === 'listening' ? 'Listening...' :
                aiState === 'thinking' ? 'Processing...' :
                aiState === 'speaking' ? 'Speaking...' :
                aiState === 'executing' ? 'Executing...' :
                jarvisActive ? 'Ready' : 'Standing By'
              ) : 'Connecting...'}
            </span>
          </div>
          {aiResponse && (
            <div className="ai-response-bubble">
              <p>{aiResponse}</p>
            </div>
          )}
        </div>
      </div>

      {/* Right Column — Chat */}
      <div className="home-right">
        <div className="panel chat-full-panel">
          <div className="panel-title"><span className="panel-title-dot" />CONVERSATION</div>
          <ChatPanel />
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
  // Set speaking flag to mute mic during TTS
  useStore.getState().setIsSpeaking(true);
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
      audio.onended = () => {
        URL.revokeObjectURL(url);
        setTimeout(() => useStore.getState().setIsSpeaking(false), 600);
      };
      audio.onerror = () => {
        useStore.getState().setIsSpeaking(false);
      };
      audio.play().catch(() => {
        speakBrowser(text);
        setTimeout(() => useStore.getState().setIsSpeaking(false), 2000);
      });
      return;
    }
  } catch (e) { /* fallback */ }
  speakBrowser(text);
  setTimeout(() => useStore.getState().setIsSpeaking(false), 2000);
}

// ═══════════════════════════════════════════════════════════════════
//  VOICE RECOGNITION ENGINE v3.2 — Anti-Echo + Cooldown + Smart Filters
// ═══════════════════════════════════════════════════════════════════

// Global voice state
let _voiceRecInstance = null;
let _voiceRestartCount = 0;
let _voiceHeartbeatInterval = null;
let _voiceLastResultTime = 0;
let _micBlockedNotified = false;
let _wakeWordCooldownUntil = 0;  // Prevent rapid re-trigger

// Common JARVIS response phrases that the mic picks up (echo filter)
const ECHO_PHRASES = [
  'yes sir', "i'm listening", 'how can i help', 'going offline',
  'call me anytime', 'all systems', 'welcome back', 'hey hari',
  'good morning', 'good afternoon', 'good evening',
];

function startVoiceRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    console.warn('Web Speech API not supported');
    if (!_micBlockedNotified) {
      showToast({ title: 'Voice Unavailable', message: 'Use Chrome or Edge for voice commands.', type: 'warning' });
      _micBlockedNotified = true;
    }
    return null;
  }

  const rec = new SR();
  rec.continuous = true;
  rec.interimResults = true;
  rec.lang = 'en-IN';
  rec.maxAlternatives = 3;

  let wakeWordTriggeredThisPhrase = false;

  rec.onstart = () => {
    useStore.getState().setRecording(true);
    _voiceRestartCount = 0;
    _micBlockedNotified = false;
    console.log('Voice recognition STARTED');
  };

  rec.onresult = (event) => {
    _voiceLastResultTime = Date.now();
    const store = useStore.getState();

    // ANTI-FEEDBACK: Skip ALL processing while JARVIS is speaking
    if (store.isSpeaking) return;

    for (let i = event.resultIndex; i < event.results.length; i++) {
      const isFinal = event.results[i].isFinal;
      const transcript = event.results[i][0].transcript.trim();
      const lower = transcript.toLowerCase();

      if (!lower || lower.length < 2) continue;

      // ECHO FILTER: If the heard text matches common JARVIS responses, skip it
      if (isFinal && ECHO_PHRASES.some(ep => lower.includes(ep)) && !/jarvis/i.test(lower)) {
        console.log('Voice: filtered echo ->', lower);
        continue;
      }

      // Check ALL alternatives for wake word
      let hasWakeWord = /jarvis|j[.\s]*a[.\s]*r[.\s]*v[.\s]*i[.\s]*s/i.test(lower);
      if (!hasWakeWord) {
        for (let a = 1; a < event.results[i].length; a++) {
          const alt = (event.results[i][a]?.transcript || '').toLowerCase();
          if (/jarvis|j[.\s]*a[.\s]*r[.\s]*v[.\s]*i[.\s]*s/i.test(alt)) {
            hasWakeWord = true;
            break;
          }
        }
      }

      // 1. DEACTIVATION COMMANDS
      if (isFinal && /^(turn off|go to sleep|stop listening|deactivate|good\s*night|shut down|jarvis stop|stop jarvis|jarvis off)$/i.test(lower)) {
        store.setJarvisActive(false);
        store.setAiState('idle');
        wakeWordTriggeredThisPhrase = false;
        _wakeWordCooldownUntil = Date.now() + 5000;
        store.addChatMessage({ role: 'assistant', content: 'Going offline, Sir. Call me anytime.' });
        speakBackend('Going offline, Sir. Call me anytime.');
        return;
      }

      // 2. WAKE WORD DETECTION (with cooldown)
      if (hasWakeWord && !wakeWordTriggeredThisPhrase) {
        // Cooldown check: don't re-trigger within 5 seconds
        if (Date.now() < _wakeWordCooldownUntil) {
          console.log('Voice: wake word cooldown active, skipping');
          continue;
        }

        wakeWordTriggeredThisPhrase = true;
        
        // Only activate + acknowledge if JARVIS wasn't already active
        const wasAlreadyActive = store.jarvisActive;
        store.setJarvisActive(true);
        store.setAiState('listening');

        if (!isFinal) continue;
      }

      if (!isFinal) continue;

      // 3. WAKE WORD + COMMAND IN SAME PHRASE
      if (wakeWordTriggeredThisPhrase) {
        wakeWordTriggeredThisPhrase = false;
        _wakeWordCooldownUntil = Date.now() + 5000; // Set cooldown

        const cleaned = lower
          .replace(/hey\s+(jarvis|j[.\s]*a[.\s]*r[.\s]*v[.\s]*i[.\s]*s)|(jarvis|j[.\s]*a[.\s]*r[.\s]*v[.\s]*i[.\s]*s)/gi, '')
          .replace(/^\s*[,.\s]+/, '')
          .trim();

        if (cleaned && cleaned.length > 1) {
          store.sendCommand(cleaned);
        } else {
          // Just the wake word — only acknowledge if not already active
          store.addChatMessage({ role: 'assistant', content: 'Yes Sir, I\'m listening.' });
          speakBackend('Yes Sir, I\'m listening.');
        }
        store._startAutoDeactivateTimer();
        return;
      }

      // 4. COMMAND WHILE JARVIS IS ACTIVE
      if (store.jarvisActive) {
        store.sendCommand(transcript);
        store._startAutoDeactivateTimer();
        return;
      }
    }
  };

  rec.onerror = (event) => {
    if (event.error === 'no-speech' || event.error === 'aborted') return;
    console.warn('Voice error:', event.error);
    if (event.error === 'not-allowed') {
      if (!_micBlockedNotified) {
        showToast({ title: 'Microphone Access', message: 'Allow microphone in browser settings for voice commands.', type: 'warning', duration: 6000 });
        _micBlockedNotified = true;
      }
      useStore.getState().setRecording(false);
    }
  };

  // ROBUST AUTO-RESTART
  rec.onend = () => {
    useStore.getState().setRecording(false);
    wakeWordTriggeredThisPhrase = false;

    if (rec._stopped) return;

    _voiceRestartCount++;
    const delay = Math.min(300 * Math.pow(1.5, Math.min(_voiceRestartCount - 1, 5)), 3000);

    setTimeout(() => {
      if (rec._stopped) return;
      try { rec.start(); } catch (e) {
        setTimeout(() => {
          if (rec._stopped) return;
          try { rec.start(); } catch (e2) {}
        }, 2000);
      }
    }, delay);
  };

  rec._stopped = false;
  try {
    rec.start();
  } catch (e) {
    setTimeout(() => {
      try { rec.start(); } catch (e2) {}
    }, 2000);
  }

  _voiceRecInstance = rec;

  // HEARTBEAT: Check every 15s if recognition is still alive
  if (_voiceHeartbeatInterval) clearInterval(_voiceHeartbeatInterval);
  _voiceHeartbeatInterval = setInterval(() => {
    if (rec._stopped) {
      clearInterval(_voiceHeartbeatInterval);
      return;
    }
    if (!useStore.getState().isRecording) {
      try { rec.start(); } catch (e) {}
    }
  }, 15000);

  return rec;
}

// ─── PUSH-TO-TALK ─────────────────────────────────────────────────
window._jarvisPushToTalk = function() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    showToast({ title: 'Voice Unavailable', message: 'Speech recognition not supported.', type: 'warning' });
    return;
  }

  const store = useStore.getState();

  if (_voiceRecInstance && !_voiceRecInstance._stopped) {
    try {
      _voiceRecInstance._stopped = true;
      _voiceRecInstance.stop();
    } catch (e) {}
  }

  const ptt = new SR();
  ptt.continuous = false;
  ptt.interimResults = false;
  ptt.lang = 'en-IN';
  ptt.maxAlternatives = 3;

  store.setJarvisActive(true);
  store.setAiState('listening');
  store.setPushToTalkActive(true);

  ptt.onresult = (event) => {
    const transcript = event.results[0][0].transcript.trim();
    if (!transcript) return;

    const cleaned = transcript.replace(/hey\s+jarvis|jarvis/gi, '').replace(/^\s*[,.\s]+/, '').trim();
    const command = cleaned || transcript;
    store.sendCommand(command);
    store._startAutoDeactivateTimer();
  };

  ptt.onerror = (event) => {
    store.setPushToTalkActive(false);
    if (event.error === 'no-speech') {
      showToast({ title: 'No Speech', message: 'I didn\'t hear anything. Try again.', type: 'info' });
    }
  };

  ptt.onend = () => {
    store.setPushToTalkActive(false);
    setTimeout(() => {
      if (_voiceRecInstance) {
        _voiceRecInstance._stopped = false;
        try { _voiceRecInstance.start(); } catch (e) {}
      }
    }, 500);
  };

  try { ptt.start(); } catch (e) {
    store.setPushToTalkActive(false);
  }
};

// ─── Main App ─────────────────────────────────────────────────────
export default function App() {
  const showBoot = useStore(s => s.showBoot);
  const setShowBoot = useStore(s => s.setShowBoot);
  const currentPage = useStore(s => s.currentPage);
  const setPage = useStore(s => s.setPage);
  const connectWs = useStore(s => s.connectWs);
  const fetchStatus = useStore(s => s.fetchStatus);
  const connected = useStore(s => s.connected);
  const aiState = useStore(s => s.aiState);
  const voiceRef = useRef(null);

  const onBootComplete = useCallback(() => {
    setShowBoot(false);
    setTimeout(() => speakBackend("Welcome back Sir. All systems operational."), 500);
    setTimeout(() => {
      if (!voiceRef.current) {
        voiceRef.current = startVoiceRecognition();
      }
    }, 2000);
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
      if (_voiceHeartbeatInterval) clearInterval(_voiceHeartbeatInterval);
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
      default: return <motion.div {...pageAnim} style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><div style={{ textAlign: 'center', color: 'var(--text-dim)' }}><div style={{ fontFamily: 'var(--font-display)', fontSize: 14, letterSpacing: 3 }}>{currentPage.toUpperCase()} MODULE</div><div style={{ fontSize: 12, marginTop: 8 }}>Coming soon</div></div></motion.div>;
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
        <span className="bottom-item" data-active={connected}>
          <span className="bottom-dot" style={{background: connected ? 'var(--green)' : 'var(--red)'}} />
          {connected ? 'CONNECTED' : 'OFFLINE'}
        </span>
        <span className="bottom-item">
          <span className="bottom-dot" style={{background: aiState === 'idle' ? 'var(--text-dim)' : 'var(--cyan)'}} />
          {aiState.toUpperCase()}
        </span>
        <span className="bottom-item">J.A.R.V.I.S v2.5</span>
      </div>
    </>
  );
}
