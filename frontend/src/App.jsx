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
import WeatherWidget from './components/WeatherWidget';
import NotificationToast, { showToast } from './components/NotificationToast';

const pageAnim = { initial: { opacity: 0, y: 20 }, animate: { opacity: 1, y: 0 }, exit: { opacity: 0, y: -20 }, transition: { duration: 0.3 } };

function HomePage() {
  const aiState = useStore(s => s.aiState);
  const aiResponse = useStore(s => s.aiResponse);
  const connected = useStore(s => s.connected);
  const jarvisActive = useStore(s => s.jarvisActive);
  
  const generateWaveform = (count) => {
    return Array.from({ length: count }).map((_, i) => (
      <div key={i} className="waveform-bar active" style={{
        height: `${Math.floor(Math.random() * 24) + 8}px`,
        animationDuration: `${0.3 + Math.random() * 0.4}s`,
        animationDelay: `${Math.random() * 0.5}s`
      }}></div>
    ));
  };

  return (
    <div className="cinematic-home">
      <div className="top-dashboard">
        <div className="left-panel-group">
          <SystemOverview />
          <WeatherWidget />
          <QuickAccess />
        </div>
        
        <div className="center-panel-group">
          <AICore state={aiState} />
        </div>
        
        <div className="right-panel-group">
          <div className="panel ai-assistant-panel">
            <div className="panel-title"><span className="panel-title-dot" />AI ASSISTANT</div>
            <div className="assistant-greeting">Hello, Hari</div>
            <div className="assistant-msg">{aiResponse || 'How can I assist you today?'}</div>
            <div className="waveform-container" style={{background: 'none', border: 'none', marginTop: 12, height: '30px', padding: 0}}>
               {generateWaveform(24)}
            </div>
          </div>
          <RecentCommands />
          <div className="panel sys-alerts-panel">
            <div className="panel-title"><span className="panel-title-dot" />SYSTEM ALERTS</div>
            <div className="sys-alert" style={{background: 'transparent', border: '1px solid var(--border-dim)'}}>
              <span className="sys-alert-icon" style={{color: 'var(--cyan)', fontSize: 24}}>🛡️</span>
              <div className="sys-alert-text">
                <div className="sys-alert-title" style={{color: 'var(--text-primary)', fontSize: 13}}>System Alerts</div>
                <div className="sys-alert-desc" style={{color: 'var(--text-secondary)', marginTop: 4}}>
                  All systems are running optimally.
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div className="bottom-dashboard">
        <div className="bottom-row">
          <div className="panel bottom-panel">
            <div className="panel-title" style={{justifyContent: 'center'}}>LISTENING</div>
            <div className="bottom-panel-content">
              <div className="waveform-bg left">{generateWaveform(12)}</div>
              <div className="mini-ring">
                 <div className="mini-center">
                    <span className="mini-text">J.A.R.V.I.S</span>
                 </div>
              </div>
              <div className="waveform-bg right">{generateWaveform(12)}</div>
            </div>
            <div className="mini-status">I'm listening...</div>
            <div style={{textAlign: 'center', marginTop: 4}}><span style={{color: 'var(--cyan)'}}>🎙️</span></div>
          </div>
          <div className="panel bottom-panel">
            <div className="panel-title" style={{justifyContent: 'center'}}>THINKING</div>
            <div className="bottom-panel-content" style={{flexDirection: 'column', gap: 16}}>
              <div className="mini-ring" style={{borderStyle: 'dashed'}}>
                 <div className="mini-center" style={{background: 'radial-gradient(circle, rgba(0,180,255,0.1), transparent)'}}>
                    <span style={{fontSize: 28}}>🧠</span>
                 </div>
              </div>
              <div className="mini-status">Processing your command...</div>
              <div className="progress-bar-container" style={{width: '80%', display: 'flex', alignItems: 'center', gap: 8}}>
                 <div className="progress-bar" style={{flex: 1, margin: 0, height: 2}}><div className="progress-fill" style={{width: '72%'}}></div></div>
                 <span style={{fontSize: 9, color: 'var(--text-dim)'}}>72%</span>
              </div>
            </div>
          </div>
          <div className="panel bottom-panel">
            <div className="panel-title" style={{justifyContent: 'center'}}>EXECUTING</div>
            <div className="bottom-panel-content" style={{flexDirection: 'column', gap: 16}}>
              <div className="mini-ring" style={{border: 'none', animation: 'none'}}>
                 <div className="mini-center" style={{background: 'transparent', border: 'none', boxShadow: 'none'}}>
                    <img src="https://upload.wikimedia.org/wikipedia/commons/e/e1/Google_Chrome_icon_%28February_2022%29.svg" alt="Chrome" style={{width: 64, height: 64, filter: 'drop-shadow(0 0 10px rgba(255,255,255,0.2))'}} />
                 </div>
              </div>
              <div className="mini-status">Opening Google Chrome...</div>
              <div className="progress-bar-container" style={{width: '80%', display: 'flex', alignItems: 'center', gap: 8}}>
                 <div className="progress-bar" style={{flex: 1, margin: 0, height: 2}}><div className="progress-fill" style={{width: '100%', background: 'var(--blue)'}}></div></div>
                 <span style={{fontSize: 9, color: 'var(--text-dim)'}}>100%</span>
              </div>
            </div>
          </div>
        </div>
        
        <div className="bottom-row">
          <div className="panel bottom-panel">
            <div className="panel-title" style={{justifyContent: 'center'}}>SPEAKING</div>
            <div className="bottom-panel-content">
              <div className="waveform-bg left">{generateWaveform(12)}</div>
              <div className="mini-ring">
                 <div className="mini-center">
                    <span className="mini-text">J.A.R.V.I.S</span>
                 </div>
              </div>
              <div className="waveform-bg right">{generateWaveform(12)}</div>
            </div>
            <div className="mini-status">Opening your browser now, sir.</div>
            <div style={{textAlign: 'center', marginTop: 4}}><span style={{color: 'var(--cyan)'}}>🎙️</span></div>
          </div>
          <div className="panel bottom-panel" style={{padding: 8}}>
             {/* Scale down dashboard panel */}
             <div style={{transform: 'scale(0.85)', transformOrigin: 'top center', width: '117%', height: '117%'}}>
                <DashboardPanel />
             </div>
          </div>
          <div className="panel bottom-panel" style={{padding: 8}}>
             <div style={{transform: 'scale(0.85)', transformOrigin: 'top center', width: '117%', height: '117%', display: 'flex', flexDirection: 'column'}}>
                <ChatPanel />
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
// Handles wake word "JARVIS" detection + active-mode command capture.
// Clap detection is handled by the BACKEND via sounddevice.
function startVoiceRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    console.warn('Web Speech API not supported in this browser');
    return null;
  }

  const rec = new SR();
  rec.continuous = true;
  rec.interimResults = true;
  rec.lang = 'en-US';
  rec.maxAlternatives = 1;

  rec.onstart = () => {
    useStore.getState().setRecording(true);
    console.log('🎤 Voice recognition active — say "JARVIS" to activate');
  };

  // Track whether wake word was already triggered in the current speech phrase
  let wakeWordTriggeredThisPhrase = false;

  rec.onresult = (event) => {
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const isFinal = event.results[i].isFinal;
      const transcript = event.results[i][0].transcript.trim();
      const lower = transcript.toLowerCase();

      if (!lower) continue;

      if (isFinal) {
        console.log('🗣️ Final:', transcript);
      }

      const store = useStore.getState();
      const hasWakeWord = /jarvis|j\.?a\.?r\.?v\.?i\.?s\.?/i.test(lower);

      // ━━━ 1. DEACTIVATION COMMANDS (always check first) ━━━
      if (isFinal && /^(turn off|go to sleep|stop listening|deactivate|good\s*night|shut down|jarvis stop)$/i.test(lower)) {
        store.setJarvisActive(false);
        store.setAiState('idle');
        wakeWordTriggeredThisPhrase = false;
        showToast({ title: 'J.A.R.V.I.S', message: 'Going offline Hari. Call me anytime.', type: 'info' });
        store.addChatMessage({ role: 'assistant', content: 'Going offline Hari. Call me anytime.' });
        speakBackend('Going offline Hari. Call me anytime.');
        return; // Done processing this batch
      }

      // ━━━ 2. WAKE WORD DETECTION ━━━
      if (hasWakeWord && !wakeWordTriggeredThisPhrase) {
        wakeWordTriggeredThisPhrase = true;
        store.setJarvisActive(true);
        store.setAiState('listening');
        console.log('🗣️ Wake word detected — JARVIS activated');

        if (!isFinal) {
          // Interim result: just activate UI, wait for the final sentence
          continue;
        }
      }

      // Only process final results from here
      if (!isFinal) continue;

      // ━━━ 3. WAKE WORD + COMMAND IN SAME PHRASE ━━━
      if (wakeWordTriggeredThisPhrase) {
        wakeWordTriggeredThisPhrase = false; // Reset for next phrase

        // Extract command text after the wake word
        const cleaned = lower
          .replace(/hey\s+(jarvis|j\.?a\.?r\.?v\.?i\.?s\.?)|(jarvis|j\.?a\.?r\.?v\.?i\.?s\.?)/gi, '')
          .replace(/^\s*[,.\s]+/, '')
          .trim();

        if (cleaned) {
          // Wake word + command: "JARVIS open chrome"
          console.log('🎯 Wake word + command:', cleaned);
          showToast({ title: 'J.A.R.V.I.S', message: `Processing: "${cleaned}"`, type: 'info' });
          store.sendCommand(cleaned);
        } else {
          // Just the wake word: "JARVIS" / "Hey JARVIS"
          showToast({ title: 'J.A.R.V.I.S', message: 'Hey Hari, how can I help you?', type: 'info' });
          store.addChatMessage({ role: 'assistant', content: 'Hey Hari, how can I help you?' });
          speakBackend('Hey Hari, how can I help you?');
        }
        store._startAutoDeactivateTimer();
        return; // Done processing this batch
      }

      // ━━━ 4. COMMAND WHILE JARVIS IS ALREADY ACTIVE (no wake word needed) ━━━
      if (store.jarvisActive) {
        console.log('🎯 Active mode command:', transcript);
        showToast({ title: 'J.A.R.V.I.S', message: `Processing: "${transcript}"`, type: 'info' });
        store.sendCommand(transcript);
        store._startAutoDeactivateTimer();
        return; // Done processing this batch
      }

      // If JARVIS is not active and no wake word, ignore the speech
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
