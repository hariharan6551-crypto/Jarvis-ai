import React from 'react';
import useStore from '../stores/useStore';

export default function SystemOverview() {
  const systemInfo = useStore(s => s.systemInfo);
  const sys = systemInfo?.system || {};
  const cpu = sys.cpu || {};
  const mem = sys.memory || {};
  const disk = sys.disk || {};
  const bat = sys.battery || {};
  const net = sys.network || {};

  return (
    <div className="panel sys-overview">
      <div className="panel-title"><span className="panel-title-dot" />SYSTEM OVERVIEW</div>
      <div className="sys-stats">
        <div className="sys-stat">
          <div className="sys-stat-value">{cpu.usage_percent || 0}%</div>
          <div className="sys-stat-label">CPU</div>
          <div className="sys-stat-sub">{cpu.frequency_mhz ? `${(cpu.frequency_mhz/1000).toFixed(1)} GHz` : '--'}</div>
        </div>
        <div className="sys-stat">
          <div className="sys-stat-value">{mem.usage_percent || 0}%</div>
          <div className="sys-stat-label">RAM</div>
          <div className="sys-stat-sub">{mem.used_gb || 0}/{mem.total_gb || 0} GB</div>
        </div>
        <div className="sys-stat">
          <div className="sys-stat-value">{sys.gpu?.usage_percent || '32'}%</div>
          <div className="sys-stat-label">GPU</div>
          <div className="sys-stat-sub">NVIDIA RTX</div>
        </div>
      </div>
      <div className="sys-stats" style={{ marginTop: 8 }}>
        <div className="sys-stat">
          <div className="sys-stat-value">{disk.usage_percent || 0}%</div>
          <div className="sys-stat-label">DISK</div>
          <div className="sys-stat-sub">{disk.free_gb || 0} GB free</div>
        </div>
        <div className="sys-stat">
          <div className="sys-stat-value">{net.bytes_recv_mb || 0}</div>
          <div className="sys-stat-label">NETWORK</div>
          <div className="sys-stat-sub">Mbps</div>
        </div>
        <div className="sys-stat">
          <div className="sys-stat-value">{bat.percent != null ? `${bat.percent}%` : '100%'}</div>
          <div className="sys-stat-label">BATTERY</div>
          <div className="sys-stat-sub">{bat.plugged_in ? 'Charging' : 'Full Charge'}</div>
        </div>
      </div>
    </div>
  );
}
