import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import useStore from '../stores/useStore';

const statusColors = {
  running: 'var(--green)',
  ok: 'var(--green)',
  healthy: 'var(--green)',
  degraded: 'var(--orange)',
  crashed: 'var(--red)',
  failed: 'var(--red)',
  stopped: 'var(--text-dim)',
  starting: 'var(--cyan)',
  unknown: 'var(--text-dim)',
};

const statusIcons = {
  running: '●',
  ok: '●',
  healthy: '●',
  degraded: '◐',
  crashed: '✗',
  failed: '✗',
  stopped: '○',
  starting: '◌',
  unknown: '?',
};

export default function DiagnosticsPanel() {
  const [health, setHealth] = useState(null);
  const [watchdog, setWatchdog] = useState(null);
  const apiUrl = useStore(s => s.apiUrl);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [hRes, wRes] = await Promise.all([
          fetch(`${apiUrl}/api/health`).then(r => r.json()).catch(() => null),
          fetch(`${apiUrl}/api/watchdog`).then(r => r.json()).catch(() => null),
        ]);
        if (hRes) setHealth(hRes);
        if (wRes) setWatchdog(wRes);
      } catch (e) { /* backend not running */ }
    };
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [apiUrl]);

  const engines = health?.engines || {};
  const services = watchdog?.services || {};
  const allItems = [
    ...Object.entries(engines).map(([name, info]) => ({
      name, status: info.status, type: 'engine', details: info.details || {},
    })),
    ...Object.entries(services).map(([name, info]) => ({
      name, status: info.status, type: 'service',
      restarts: info.restart_count, uptime: info.uptime_seconds,
    })),
  ];

  return (
    <div>
      <div className="panel-title"><span className="panel-title-dot" />SYSTEM DIAGNOSTICS</div>

      {/* Overall Status */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px',
        background: 'rgba(0,180,255,0.05)', borderRadius: 10, marginBottom: 16,
        border: '1px solid var(--border-dim)',
      }}>
        <div style={{
          width: 48, height: 48, borderRadius: '50%',
          background: health?.status === 'healthy' ? 'rgba(34,197,94,0.15)' : 'rgba(245,158,11,0.15)',
          border: `2px solid ${health?.status === 'healthy' ? 'var(--green)' : 'var(--orange)'}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 20, boxShadow: `0 0 15px ${health?.status === 'healthy' ? 'rgba(34,197,94,0.3)' : 'rgba(245,158,11,0.3)'}`,
        }}>
          {health?.status === 'healthy' ? '✓' : '⚠'}
        </div>
        <div>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 12, letterSpacing: 2, color: 'var(--text-primary)' }}>
            SYSTEM {(health?.status || 'LOADING').toUpperCase()}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
            Uptime: {health?.uptime_human || '--'} | Python {health?.platform?.python || '--'}
          </div>
        </div>
      </div>

      {/* Module Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        {allItems.length === 0 && (
          <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: 20, color: 'var(--text-dim)', fontSize: 12 }}>
            Waiting for backend connection...
          </div>
        )}
        {allItems.map((item, i) => (
          <motion.div
            key={item.name}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            style={{
              padding: '12px 14px', borderRadius: 10,
              background: 'var(--bg-card)', border: '1px solid var(--border-dim)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
              <span style={{
                fontFamily: 'var(--font-display)', fontSize: 10, letterSpacing: 1.5,
                color: 'var(--text-primary)', textTransform: 'uppercase',
              }}>
                {item.name}
              </span>
              <span style={{
                fontSize: 11, color: statusColors[item.status] || 'var(--text-dim)',
                fontFamily: 'var(--font-mono)', fontWeight: 600,
              }}>
                {statusIcons[item.status] || '?'} {item.status}
              </span>
            </div>
            <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>
              {item.type === 'service' && item.uptime != null && (
                <span>Uptime: {Math.round(item.uptime)}s</span>
              )}
              {item.restarts > 0 && (
                <span style={{ marginLeft: 8, color: 'var(--orange)' }}>Restarts: {item.restarts}</span>
              )}
              {item.type === 'engine' && <span>Type: Engine</span>}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Watchdog Status */}
      {watchdog && (
        <div style={{ marginTop: 16, padding: '10px 14px', borderRadius: 8, background: 'rgba(0,180,255,0.03)', border: '1px solid var(--border-dim)' }}>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 9, letterSpacing: 2, color: 'var(--cyan)', marginBottom: 6 }}>
            WATCHDOG
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
            Status: {watchdog.watchdog_running ? '● Active' : '○ Inactive'} | Check interval: {watchdog.check_interval}s
          </div>
        </div>
      )}
    </div>
  );
}
