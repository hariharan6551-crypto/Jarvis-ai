import { create } from 'zustand';

const useStore = create((set, get) => ({
  // Connection
  ws: null,
  connected: false,
  backendUrl: 'ws://127.0.0.1:8765/ws',
  apiUrl: 'http://127.0.0.1:8765',

  // UI State
  currentPage: 'home',
  aiState: 'idle', // idle, listening, thinking, executing, speaking, error
  showBoot: true,
  sidebarCollapsed: false,

  // JARVIS active state (clap toggle)
  jarvisActive: false,

  // Data
  messages: [],
  chatMessages: [],
  recentCommands: [],
  systemInfo: null,
  aiResponse: '',
  transcription: '',
  chromeProfiles: [],
  frequentApps: [],

  // Audio
  isRecording: false,
  audioLevel: 0,
  waveformData: Array(32).fill(4),
  _autoDeactivateTimer: null,

  // Voice control state
  isSpeaking: false,          // true while TTS is playing (mutes mic)
  pushToTalkActive: false,    // true during push-to-talk capture

  // Theme
  theme: localStorage.getItem('jarvis-theme') || 'dark',

  // Settings
  settings: {
    provider: 'gemini',
    model: 'gemini-1.5-flash',
    ttsProvider: 'edge',
    userName: 'Hari',
    wakeWord: 'jarvis',
  },

  // Actions
  setPage: (page) => set({ currentPage: page }),
  setAiState: (state) => set({ aiState: state }),
  setConnected: (v) => set({ connected: v }),
  setShowBoot: (v) => set({ showBoot: v }),
  setRecording: (v) => set({ isRecording: v }),
  setAudioLevel: (v) => set({ audioLevel: v }),
  setTranscription: (t) => set({ transcription: t }),
  setSystemInfo: (info) => set({ systemInfo: info }),
  setJarvisActive: (v) => set({ jarvisActive: v }),
  setIsSpeaking: (v) => set({ isSpeaking: v }),
  setPushToTalkActive: (v) => set({ pushToTalkActive: v }),

  toggleTheme: () => {
    const newTheme = get().theme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('jarvis-theme', newTheme);
    set({ theme: newTheme });
  },
  setWaveformData: (data) => set({ waveformData: data }),

  addChatMessage: (msg) => set((s) => ({
    chatMessages: [...s.chatMessages, { ...msg, id: Date.now() + Math.random(), timestamp: new Date().toLocaleTimeString() }]
  })),

  addCommand: (cmd) => set((s) => ({
    recentCommands: [
      { ...cmd, id: Date.now(), time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) },
      ...s.recentCommands
    ].slice(0, 15)
  })),

  updateSettings: (key, val) => set((s) => ({
    settings: { ...s.settings, [key]: val }
  })),

  // ─── Speak using browser TTS ───────────────────────────────────
  speakBrowser: (text) => {
    const synth = window.speechSynthesis;
    if (!synth || !text) return;
    synth.cancel();
    const msg = new SpeechSynthesisUtterance(text);
    msg.rate = 1.0;
    msg.pitch = 0.9;
    msg.volume = 1.0;
    msg.lang = 'en-US';
    const voices = synth.getVoices();
    const preferred = voices.find(v =>
      v.name.includes('Google US English') || v.name.includes('David') || v.name.includes('Male')
    );
    if (preferred) msg.voice = preferred;
    synth.speak(msg);
  },

  // ─── Speak using backend TTS (higher quality), fallback to browser ─
  speakBackend: async (text) => {
    try {
      const res = await fetch(`${get().apiUrl}/api/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      const data = await res.json();
      if (data.audio) {
        get().playAudio(data.audio);
        return;
      }
    } catch (e) { /* fallback */ }
    get().speakBrowser(text);
  },

  // WebSocket
  connectWs: () => {
    const { backendUrl } = get();
    try {
      const ws = new WebSocket(backendUrl);
      ws.onopen = () => {
        set({ ws, connected: true });
        console.log('WebSocket connected');
      };
      ws.onclose = () => {
        set({ ws: null, connected: false });
        console.log('WebSocket disconnected');
        setTimeout(() => get().connectWs(), 3000);
      };
      ws.onerror = () => set({ connected: false });
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          get().handleWsMessage(data);
        } catch (e) { console.error('WS parse error', e); }
      };
    } catch (e) {
      console.error('WS connection error', e);
      setTimeout(() => get().connectWs(), 3000);
    }
  },

  handleWsMessage: (data) => {
    const { type } = data;

    if (type === 'state_change') {
      set({ aiState: data.data.state });

    } else if (type === 'response') {
      const d = data.data;
      const responseText = d.response_text || d.message || '';
      // If JARVIS is active, stay in 'listening' state so it keeps accepting commands
      const nextState = get().jarvisActive ? 'listening' : 'idle';
      set({ aiState: nextState, aiResponse: responseText });

      if (responseText) {
        get().addChatMessage({ role: 'assistant', content: responseText });
      }
      get().addCommand({
        text: d.intent || 'command',
        status: d.success ? 'success' : 'error',
        message: responseText,
        steps: d.plan_steps || 1,
      });

      if (d.audio) {
        get().playAudio(d.audio);
      }

      // Reset auto-deactivate timer after response so user has time for follow-up
      if (get().jarvisActive) {
        get()._startAutoDeactivateTimer();
      }

    } else if (type === 'transcription') {
      set({ transcription: data.data.text });
      get().addChatMessage({ role: 'user', content: data.data.text });

    } else if (type === 'clap_event') {
      // ━━━ CLAP DETECTION FROM BACKEND ━━━
      const d = data.data;
      const event = d.event;
      const isActive = d.jarvis_active;
      set({ jarvisActive: isActive });

      if (event === 'triple_clap') {
        // Triple clap → EMERGENCY STOP
        console.log('👏👏👏 Triple clap → EMERGENCY STOP');
        set({ aiState: 'idle', jarvisActive: false });
        get().addChatMessage({ role: 'assistant', content: d.message || 'Emergency stop activated.' });
        get().speakBackend(d.message || 'Emergency stop activated. All tasks halted.');
      } else if (isActive) {
        // Single clap → JARVIS ON
        console.log('👏 Single clap → JARVIS ACTIVATED');
        set({ aiState: 'listening' });
        get().addChatMessage({ role: 'assistant', content: d.message || 'Hey Hari, how can I help you?' });
        get().speakBackend(d.message || 'Hey Hari, how can I help you?');
        // Auto-deactivate after 30s of no commands
        get()._startAutoDeactivateTimer();
      } else {
        // Double clap → JARVIS OFF
        console.log('👏👏 Double clap → JARVIS DEACTIVATED');
        set({ aiState: 'idle' });
        get().addChatMessage({ role: 'assistant', content: d.message || 'Going offline Hari. Call me anytime.' });
        get().speakBackend(d.message || 'Going offline Hari. Call me anytime.');
      }

    } else if (type === 'wake_word') {
      // ━━━ WAKE WORD FROM BACKEND (Vosk/SR) ━━━
      const d = data.data;
      const wasAlreadyActive = get().jarvisActive;
      set({ jarvisActive: true, aiState: 'listening' });
      console.log('🗣️ Wake word detected (backend):', d.text);
      // Only acknowledge if JARVIS wasn't already active (prevents echo from dual recognition)
      if (!wasAlreadyActive) {
        get().addChatMessage({ role: 'assistant', content: d.message || 'Hey Hari, how can I help you?' });
        // Don't speakBackend here — the backend SR loop already triggered this,
        // and speaking would cause the mic to pick it up again
      }
      get()._startAutoDeactivateTimer();

    } else if (type === 'status') {
      set({
        systemInfo: data.data,
        chromeProfiles: data.data.chrome_profiles || [],
        frequentApps: data.data.frequent_apps || [],
      });
    } else if (type === 'profiles') {
      set({ chromeProfiles: data.data.profiles || [] });
    } else if (type === 'connected') {
      console.log('Server:', data.data.message);
    } else if (type === 'tts_audio') {
      // ━━━ SEPARATE TTS AUDIO (sent after response for speed) ━━━
      if (data.data.audio) {
        get().playAudio(data.data.audio);
      }
    }
  },

  // Auto-deactivate after 2 minutes idle (gives plenty of time for follow-up commands)
  _startAutoDeactivateTimer: () => {
    const prev = get()._autoDeactivateTimer;
    if (prev) clearTimeout(prev);
    const timer = setTimeout(() => {
      if (get().jarvisActive && get().aiState !== 'thinking' && get().aiState !== 'speaking') {
        console.log('⏱️ Auto-deactivating JARVIS after 2min idle');
        set({ jarvisActive: false, aiState: 'idle', _autoDeactivateTimer: null });
      }
    }, 120000);
    set({ _autoDeactivateTimer: timer });
  },

  sendCommand: (text) => {
    const { ws, connected } = get();
    if (!text.trim()) return;
    get().addChatMessage({ role: 'user', content: text });
    set({ aiState: 'thinking', transcription: text });

    // Reset auto-deactivate timer on each command
    get()._startAutoDeactivateTimer();

    if (ws && connected) {
      ws.send(JSON.stringify({ type: 'command', text }));
    } else {
      fetch(`${get().apiUrl}/api/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      })
        .then(r => r.json())
        .then(result => {
          const responseText = result.ai_response || result.message || '';
          set({ aiState: 'idle', aiResponse: responseText });
          if (responseText) get().addChatMessage({ role: 'assistant', content: responseText });
          get().addCommand({ text: result.intent || 'command', status: result.success ? 'success' : 'error', message: responseText });
        })
        .catch(() => {
          set({ aiState: 'error' });
          setTimeout(() => set({ aiState: 'idle' }), 2000);
        });
    }
  },

  fetchStatus: async () => {
    try {
      const res = await fetch(`${get().apiUrl}/api/status`);
      const data = await res.json();
      set({
        systemInfo: data,
        chromeProfiles: data.chrome_profiles || [],
        frequentApps: data.frequent_apps || [],
      });
    } catch (e) { /* backend not running */ }
  },

  fetchProfiles: async () => {
    try {
      const res = await fetch(`${get().apiUrl}/api/browser/profiles`);
      const data = await res.json();
      set({ chromeProfiles: data.profiles || [] });
    } catch (e) { /* ignore */ }
  },

  playAudio: (base64Audio) => {
    try {
      const binary = atob(base64Audio);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      const blob = new Blob([bytes], { type: 'audio/mp3' });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      set({ aiState: 'speaking', isSpeaking: true });
      audio.onended = () => {
        URL.revokeObjectURL(url);
        // Delay clearing isSpeaking so mic doesn't pick up tail-end
        setTimeout(() => {
          const nextState = get().jarvisActive ? 'listening' : 'idle';
          set({ aiState: nextState, isSpeaking: false });
        }, 600);
      };
      audio.onerror = () => {
        const nextState = get().jarvisActive ? 'listening' : 'idle';
        set({ aiState: nextState, isSpeaking: false });
      };
      audio.play().catch(() => set({ aiState: get().jarvisActive ? 'listening' : 'idle', isSpeaking: false }));
    } catch (e) { console.error('Audio play error', e); }
  },
}));

export default useStore;
