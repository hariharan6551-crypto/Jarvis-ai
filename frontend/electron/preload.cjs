/**
 * J.A.R.V.I.S Electron Preload Script
 * Secure contextBridge API — exposes safe IPC methods to renderer.
 * This replaces direct require('electron') calls in React components.
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('jarvisAPI', {
  // Window controls
  minimize: () => ipcRenderer.send('window-minimize'),
  maximize: () => ipcRenderer.send('window-maximize'),
  close: () => ipcRenderer.send('window-close'),

  // Platform info
  platform: process.platform,
  isElectron: true,

  // IPC helpers
  send: (channel, data) => {
    const validChannels = [
      'window-minimize', 'window-maximize', 'window-close',
      'tray-show', 'tray-hide', 'app-quit',
    ];
    if (validChannels.includes(channel)) {
      ipcRenderer.send(channel, data);
    }
  },

  on: (channel, callback) => {
    const validChannels = ['backend-status', 'update-available'];
    if (validChannels.includes(channel)) {
      ipcRenderer.on(channel, (event, ...args) => callback(...args));
    }
  },
});

console.log('[Preload] J.A.R.V.I.S contextBridge API loaded');
