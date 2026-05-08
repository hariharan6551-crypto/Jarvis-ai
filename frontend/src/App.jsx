import React, { useEffect, useCallback } from 'react';
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

export default function App() {
  const showBoot = useStore(s => s.showBoot);
  const setShowBoot = useStore(s => s.setShowBoot);
  const currentPage = useStore(s => s.currentPage);
  const setPage = useStore(s => s.setPage);
  const connectWs = useStore(s => s.connectWs);
  const fetchStatus = useStore(s => s.fetchStatus);

  const onBootComplete = useCallback(() => setShowBoot(false), [setShowBoot]);

  useEffect(() => {
    const t = setTimeout(() => { connectWs(); fetchStatus(); }, 1000);
    const interval = setInterval(fetchStatus, 5000);
    return () => { clearTimeout(t); clearInterval(interval); };
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
