import React, { useState, useEffect } from 'react';

export default function TitleBar() {
  const [time, setTime] = useState(new Date());
  useEffect(() => { const t = setInterval(() => setTime(new Date()), 1000); return () => clearInterval(t); }, []);

  const minimize = () => { try { require('electron').ipcRenderer.send('window-minimize'); } catch {} };
  const maximize = () => { try { require('electron').ipcRenderer.send('window-maximize'); } catch {} };
  const close = () => { try { require('electron').ipcRenderer.send('window-close'); } catch {} };

  return (
    <div className="title-bar">
      <div className="title-bar-brand">
        <div className="title-bar-logo">J</div>
        <span className="title-bar-name">J.A.R.V.I.S</span>
        <span className="title-bar-version">v2.5.0</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span className="title-bar-center">J.A.R.V.I.S</span>
        <span className="title-bar-status">● ONLINE</span>
      </div>
      <div className="title-bar-right">
        <div className="title-bar-clock">
          <div>{time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</div>
          <div style={{ fontSize: 9 }}>{time.toLocaleDateString([], { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</div>
        </div>
        <div className="title-bar-btns">
          <button className="title-bar-btn btn-min" onClick={minimize} />
          <button className="title-bar-btn btn-max" onClick={maximize} />
          <button className="title-bar-btn btn-close" onClick={close} />
        </div>
      </div>
    </div>
  );
}
