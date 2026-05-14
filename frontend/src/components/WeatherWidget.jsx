import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import useStore from '../stores/useStore';

const weatherIcons = {
  'clear': '☀️', 'sunny': '☀️',
  'cloud': '☁️', 'overcast': '☁️', 'partly': '⛅',
  'rain': '🌧️', 'drizzle': '🌦️', 'shower': '🌧️',
  'thunder': '⛈️', 'storm': '⛈️',
  'snow': '❄️', 'sleet': '🌨️',
  'fog': '🌫️', 'mist': '🌫️', 'haze': '🌫️',
  'wind': '💨',
};

function getWeatherIcon(condition) {
  if (!condition) return '🌤️';
  const lower = condition.toLowerCase();
  for (const [key, icon] of Object.entries(weatherIcons)) {
    if (lower.includes(key)) return icon;
  }
  return '🌤️';
}

export default function WeatherWidget() {
  const systemInfo = useStore(s => s.systemInfo);
  const weather = systemInfo?.weather || {};
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const timeStr = time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true });
  const dateStr = time.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });

  const temp = weather.temp || '--';
  const condition = weather.condition || 'Loading...';
  const humidity = weather.humidity || '--';
  const windSpeed = weather.wind_speed || '--';
  const feelsLike = weather.feels_like || temp;
  const icon = getWeatherIcon(condition);

  return (
    <div className="panel" style={{ padding: 12 }}>
      <div className="panel-title"><span className="panel-title-dot" />WEATHER & TIME</div>

      {/* Clock */}
      <div style={{ textAlign: 'center', marginBottom: 10 }}>
        <div style={{
          fontFamily: 'var(--font-display)', fontSize: 26, color: 'var(--cyan)',
          textShadow: '0 0 15px rgba(0,180,255,0.3)', letterSpacing: 2,
        }}>
          {timeStr}
        </div>
        <div style={{
          fontSize: 11, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)',
          marginTop: 2, letterSpacing: 1,
        }}>
          {dateStr}
        </div>
      </div>

      {/* Divider */}
      <div style={{ height: 1, background: 'var(--border-dim)', margin: '8px 0' }} />

      {/* Weather */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <motion.div
          animate={{ rotate: [0, 5, -5, 0] }}
          transition={{ repeat: Infinity, duration: 4, ease: 'easeInOut' }}
          style={{ fontSize: 36, lineHeight: 1 }}
        >
          {icon}
        </motion.div>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
            <span style={{
              fontFamily: 'var(--font-display)', fontSize: 28, fontWeight: 700,
              background: 'linear-gradient(135deg, var(--cyan), var(--purple-bright))',
              WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
            }}>
              {temp}°
            </span>
            <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>C</span>
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 1 }}>
            {condition}
          </div>
        </div>
      </div>

      {/* Weather details */}
      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6, marginTop: 10,
      }}>
        <div style={{ textAlign: 'center', padding: '6px 0', borderRadius: 6, background: 'rgba(0,180,255,0.05)', border: '1px solid var(--border-dim)' }}>
          <div style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--cyan)' }}>{feelsLike}°</div>
          <div style={{ fontSize: 8, color: 'var(--text-dim)', letterSpacing: 1, fontFamily: 'var(--font-display)' }}>FEELS</div>
        </div>
        <div style={{ textAlign: 'center', padding: '6px 0', borderRadius: 6, background: 'rgba(0,180,255,0.05)', border: '1px solid var(--border-dim)' }}>
          <div style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--cyan)' }}>{humidity}%</div>
          <div style={{ fontSize: 8, color: 'var(--text-dim)', letterSpacing: 1, fontFamily: 'var(--font-display)' }}>HUMID</div>
        </div>
        <div style={{ textAlign: 'center', padding: '6px 0', borderRadius: 6, background: 'rgba(0,180,255,0.05)', border: '1px solid var(--border-dim)' }}>
          <div style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--cyan)' }}>{windSpeed}</div>
          <div style={{ fontSize: 8, color: 'var(--text-dim)', letterSpacing: 1, fontFamily: 'var(--font-display)' }}>KM/H</div>
        </div>
      </div>

      <div style={{
        fontSize: 9, color: 'var(--text-dim)', textAlign: 'center',
        marginTop: 8, fontFamily: 'var(--font-display)', letterSpacing: 1,
      }}>
        📍 CHENNAI, TAMIL NADU
      </div>
    </div>
  );
}
