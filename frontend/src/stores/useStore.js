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

  toggleTheme: () => {
    const newTheme = get().theme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('jarvis-theme', newTheme);
    set({ theme: newTheme });
  },
  setWaveformData: (data) => set({ waveformData: data }),

  addChatMessage: (msg) => set((s) => ({
    chatMessages: [...s.chatMessages, { ...msg, id: Date.now(), timestamp: new Date().toLocaleTimeString() }]
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
      set({ aiState: 'idle', aiResponse: responseText });

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
    } else if (type === 'transcription') {
      set({ transcription: data.data.text });
      get().addChatMessage({ role: 'user', content: data.data.text });
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
    }
  },

  sendCommand: (text) => {
    const { ws, connected } = get();
    if (!text.trim()) return;
    get().addChatMessage({ role: 'user', content: text });
    set({ aiState: 'thinking', transcription: text });

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
      set({ aiState: 'speaking' });
      audio.onended = () => { set({ aiState: 'idle' }); URL.revokeObjectURL(url); };
      audio.play().catch(() => set({ aiState: 'idle' }));
    } catch (e) { console.error('Audio play error', e); }
  },
}));

export default useStore;
