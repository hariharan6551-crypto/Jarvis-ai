import React from 'react';
import useStore from '../stores/useStore';

export default function SettingsPanel() {
  const settings = useStore(s => s.settings);
  const update = useStore(s => s.updateSettings);

  return (
    <div className="settings-grid">
      <div className="setting-group">
        <div className="setting-group-title">AI PROVIDER</div>
        <div className="setting-row">
          <span className="setting-label">Provider</span>
          <select className="setting-select" value={settings.provider} onChange={e => update('provider', e.target.value)}>
            <option value="gemini">Google Gemini</option>
            <option value="openai">OpenAI GPT</option>
            <option value="anthropic">Anthropic Claude</option>
            <option value="ollama">Ollama (Local)</option>
          </select>
        </div>
        <div className="setting-row">
          <span className="setting-label">Model</span>
          <input className="setting-input-field" value={settings.model} onChange={e => update('model', e.target.value)} />
        </div>
      </div>
      <div className="setting-group">
        <div className="setting-group-title">VOICE</div>
        <div className="setting-row">
          <span className="setting-label">TTS Engine</span>
          <select className="setting-select" value={settings.ttsProvider} onChange={e => update('ttsProvider', e.target.value)}>
            <option value="edge">Edge TTS (Free)</option>
            <option value="elevenlabs">ElevenLabs</option>
            <option value="pyttsx3">Offline (pyttsx3)</option>
          </select>
        </div>
        <div className="setting-row">
          <span className="setting-label">Wake Word</span>
          <input className="setting-input-field" value={settings.wakeWord} onChange={e => update('wakeWord', e.target.value)} />
        </div>
      </div>
      <div className="setting-group">
        <div className="setting-group-title">USER</div>
        <div className="setting-row">
          <span className="setting-label">Name</span>
          <input className="setting-input-field" value={settings.userName} onChange={e => update('userName', e.target.value)} />
        </div>
      </div>
    </div>
  );
}
