import React from 'react';
import { motion } from 'framer-motion';
import useStore from '../stores/useStore';

export default function SettingsPanel() {
  const settings = useStore(s => s.settings);
  const update = useStore(s => s.updateSettings);
  const theme = useStore(s => s.theme);
  const toggleTheme = useStore(s => s.toggleTheme);
  const chromeProfiles = useStore(s => s.chromeProfiles);
  const connected = useStore(s => s.connected);

  return (
    <div className="settings-grid">
      {/* Theme */}
      <div className="setting-group">
        <div className="setting-group-title">🎨 APPEARANCE</div>
        <div className="setting-row">
          <span className="setting-label">Theme Mode</span>
          <div className="theme-toggle">
            <span className="theme-toggle-label">🌙</span>
            <label className="theme-switch">
              <input type="checkbox" checked={theme === 'light'} onChange={toggleTheme} />
              <span className="theme-slider" />
            </label>
            <span className="theme-toggle-label">☀️</span>
          </div>
        </div>
      </div>

      {/* AI Provider */}
      <div className="setting-group">
        <div className="setting-group-title">🧠 AI PROVIDER</div>
        <div className="setting-row">
          <span className="setting-label">Provider</span>
          <select className="setting-select" value={settings.provider} onChange={e => update('provider', e.target.value)}>
            <option value="gemini">Google Gemini</option>
            <option value="openai">OpenAI GPT</option>
            <option value="anthropic">Anthropic Claude</option>
            <option value="ollama">Ollama (Local/Offline)</option>
          </select>
        </div>
        <div className="setting-row">
          <span className="setting-label">Model</span>
          <input className="setting-input-field" value={settings.model} onChange={e => update('model', e.target.value)} />
        </div>
      </div>

      {/* Voice */}
      <div className="setting-group">
        <div className="setting-group-title">🎙️ VOICE</div>
        <div className="setting-row">
          <span className="setting-label">TTS Engine</span>
          <select className="setting-select" value={settings.ttsProvider} onChange={e => update('ttsProvider', e.target.value)}>
            <option value="edge">Edge TTS (Free)</option>
            <option value="elevenlabs">ElevenLabs (Premium)</option>
            <option value="pyttsx3">Offline (pyttsx3)</option>
          </select>
        </div>
        <div className="setting-row">
          <span className="setting-label">Wake Word</span>
          <input className="setting-input-field" value={settings.wakeWord} onChange={e => update('wakeWord', e.target.value)} />
        </div>
      </div>

      {/* User */}
      <div className="setting-group">
        <div className="setting-group-title">👤 USER</div>
        <div className="setting-row">
          <span className="setting-label">Name</span>
          <input className="setting-input-field" value={settings.userName} onChange={e => update('userName', e.target.value)} />
        </div>
      </div>

      {/* Browser Profiles */}
      <div className="setting-group">
        <div className="setting-group-title">🌐 BROWSER PROFILES</div>
        {chromeProfiles.length > 0 ? (
          chromeProfiles.map((p, i) => (
            <div className="setting-row" key={i}>
              <span className="setting-label">{p.name}</span>
              <span style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>{p.email || 'No email'}</span>
            </div>
          ))
        ) : (
          <div style={{ fontSize: 11, color: 'var(--text-dim)', padding: '4px 0' }}>
            {connected ? 'No Chrome profiles detected' : 'Waiting for backend connection...'}
          </div>
        )}
      </div>

      {/* System */}
      <div className="setting-group">
        <div className="setting-group-title">⚙️ SYSTEM</div>
        <div className="setting-row">
          <span className="setting-label">Backend</span>
          <span style={{ fontSize: 12, color: connected ? 'var(--green)' : 'var(--red)', fontFamily: 'var(--font-mono)' }}>
            {connected ? '● Connected' : '○ Disconnected'}
          </span>
        </div>
        <div className="setting-row">
          <span className="setting-label">Version</span>
          <span style={{ fontSize: 12, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>v2.0.0</span>
        </div>
      </div>
    </div>
  );
}
