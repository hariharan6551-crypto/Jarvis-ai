import React from 'react';
import useStore from '../stores/useStore';

export default function DashboardPanel() {
  const si = useStore(s => s.systemInfo);
  const sys = si?.system || {};
  const cpu = sys.cpu || {};
  const mem = sys.memory || {};
  const disk = sys.disk || {};
  const bat = sys.battery || {};
  const net = sys.network || {};
  const procs = sys.top_processes || [];

  const Gauge = ({ value, label, sub }) => (
    <div style={{ textAlign: 'center' }}>
      <div className="gauge-ring" style={{ background: `conic-gradient(var(--cyan) ${value * 3.6}deg, rgba(0,180,255,0.1) 0deg)` }}>
        <div style={{ width: '65px', height: '65px', borderRadius: '50%', background: 'var(--bg-panel)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
          <span className="gauge-value">{value}%</span>
        </div>
      </div>
      <div className="gauge-label" style={{ marginTop: 6 }}>{label}</div>
      {sub && <div className="gauge-label">{sub}</div>}
    </div>
  );

  return (
    <div>
      <div className="panel-title"><span className="panel-title-dot" />DASHBOARD</div>
      <div className="dashboard-grid">
        <div className="dashboard-card">
          <div className="dashboard-card-title">PERFORMANCE</div>
          <div style={{ display: 'flex', gap: 16, justifyContent: 'center' }}>
            <Gauge value={Math.round(cpu.usage_percent || 0)} label="CPU" />
            <Gauge value={Math.round(mem.usage_percent || 0)} label="RAM" />
          </div>
        </div>
        <div className="dashboard-card">
          <div className="dashboard-card-title">STORAGE</div>
          <Gauge value={Math.round(disk.usage_percent || 0)} label={`${disk.used_gb || 0} / ${disk.total_gb || 0} GB`} />
        </div>
        <div className="dashboard-card">
          <div className="dashboard-card-title">NETWORK</div>
          <div className="net-stat">↑ Sent: <span className="net-stat-value">{net.bytes_sent_mb || 0} MB</span></div>
          <div className="net-stat">↓ Recv: <span className="net-stat-value">{net.bytes_recv_mb || 0} MB</span></div>
          {bat.percent != null && <div className="net-stat">🔋 Battery: <span className="net-stat-value">{bat.percent}%</span> {bat.plugged_in ? '⚡' : ''}</div>}
        </div>
        <div className="dashboard-card">
          <div className="dashboard-card-title">TOP PROCESSES</div>
          {procs.map((p, i) => (
            <div key={i} className="temp-row"><span className="temp-label">{p.name}</span><span className="temp-value">{p.cpu_percent?.toFixed(1)}%</span></div>
          ))}
          {procs.length === 0 && <div style={{ color: 'var(--text-dim)', fontSize: 11 }}>Fetching...</div>}
        </div>
      </div>
    </div>
  );
}
