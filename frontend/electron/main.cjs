/**
 * J.A.R.V.I.S Electron Main Process v2.5
 * Secure: contextIsolation=true, preload script, no nodeIntegration.
 * Features: system tray, single instance lock, global shortcut, auto-backend.
 */

const { app, BrowserWindow, ipcMain, globalShortcut, session, Tray, Menu, nativeImage } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let backendProcess;
let tray;
const isDev = !app.isPackaged;

// ── Single Instance Lock ─────────────────────────────────────────────
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  console.log('[Electron] Another instance is already running. Quitting.');
  app.quit();
}

app.on('second-instance', () => {
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.show();
    mainWindow.focus();
  }
});

// ── Backend Management ───────────────────────────────────────────────
function startBackend() {
  const backendDir = path.join(__dirname, '..', '..', 'backend');
  console.log('[Electron] Starting backend from:', backendDir);
  backendProcess = spawn('python', ['main.py'], {
    cwd: backendDir,
    stdio: 'pipe',
    windowsHide: true,
  });
  backendProcess.stdout.on('data', (d) => console.log('[Backend]', d.toString().trim()));
  backendProcess.stderr.on('data', (d) => console.log('[Backend]', d.toString().trim()));
  backendProcess.on('error', (e) => console.error('[Electron] Backend start error:', e));
  backendProcess.on('exit', (code) => {
    console.log(`[Electron] Backend exited with code ${code}`);
    backendProcess = null;
  });
}

function stopBackend() {
  if (backendProcess) {
    try {
      backendProcess.kill();
    } catch (e) {
      console.error('[Electron] Error killing backend:', e);
    }
    backendProcess = null;
  }
}

// ── Window Creation ──────────────────────────────────────────────────
function createWindow() {
  // Auto-allow microphone/audio permissions for voice recognition
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    // Always grant mic, audio, media permissions for JARVIS voice
    const allowedPermissions = ['media', 'microphone', 'audio', 'audioCapture', 'mediaKeySystem'];
    if (allowedPermissions.includes(permission)) {
      console.log(`[Electron] Granted permission: ${permission}`);
      callback(true);
      return;
    }
    callback(true); // Allow all other permissions too
  });

  // Also handle permission checks (needed for Web Speech API in newer Electron)
  session.defaultSession.setPermissionCheckHandler((webContents, permission) => {
    return true; // Allow all permission checks
  });

  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1100,
    minHeight: 700,
    frame: false,
    titleBarStyle: 'hidden',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: true,
      sandbox: false,
      autoplayPolicy: 'no-user-gesture-required',
    },
    icon: path.join(__dirname, '../public/icon.png'),
    backgroundColor: '#0a0e1a',
    show: false,
  });

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    mainWindow.focus();
  });

  // Minimize to tray instead of closing
  mainWindow.on('close', (event) => {
    if (!app.isQuitting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// ── System Tray ──────────────────────────────────────────────────────
function createTray() {
  try {
    const iconPath = path.join(__dirname, '../public/icon.png');
    let trayIcon;
    try {
      trayIcon = nativeImage.createFromPath(iconPath).resize({ width: 16, height: 16 });
    } catch (e) {
      // Fallback: create a simple colored icon
      trayIcon = nativeImage.createEmpty();
    }

    tray = new Tray(trayIcon);
    tray.setToolTip('J.A.R.V.I.S — AI Desktop Assistant');

    const contextMenu = Menu.buildFromTemplate([
      {
        label: 'Show J.A.R.V.I.S',
        click: () => {
          if (mainWindow) {
            mainWindow.show();
            mainWindow.focus();
          }
        },
      },
      { type: 'separator' },
      {
        label: 'Quit J.A.R.V.I.S',
        click: () => {
          app.isQuitting = true;
          app.quit();
        },
      },
    ]);

    tray.setContextMenu(contextMenu);
    tray.on('double-click', () => {
      if (mainWindow) {
        mainWindow.show();
        mainWindow.focus();
      }
    });
  } catch (e) {
    console.error('[Electron] Tray creation failed:', e);
  }
}

// ── App Lifecycle ────────────────────────────────────────────────────
app.whenReady().then(() => {
  // Start backend first
  startBackend();

  // Wait for backend, then open window
  setTimeout(() => {
    createWindow();
    createTray();
  }, 2000);

  // Global shortcut: Ctrl+Shift+J to show/hide
  globalShortcut.register('CommandOrControl+Shift+J', () => {
    if (mainWindow) {
      if (mainWindow.isVisible()) {
        mainWindow.hide();
      } else {
        mainWindow.show();
        mainWindow.focus();
      }
    }
  });
});

// ── IPC Handlers ─────────────────────────────────────────────────────
ipcMain.on('window-minimize', () => mainWindow?.minimize());
ipcMain.on('window-maximize', () => {
  if (mainWindow?.isMaximized()) mainWindow.unmaximize();
  else mainWindow?.maximize();
});
ipcMain.on('window-close', () => mainWindow?.hide()); // Hide to tray
ipcMain.on('app-quit', () => {
  app.isQuitting = true;
  app.quit();
});

// ── Cleanup ──────────────────────────────────────────────────────────
app.on('window-all-closed', () => {
  // Don't quit on window close (tray keeps running)
  if (process.platform !== 'darwin' && app.isQuitting) {
    app.quit();
  }
});

app.on('before-quit', () => {
  app.isQuitting = true;
  globalShortcut.unregisterAll();
  stopBackend();
  if (tray) {
    tray.destroy();
    tray = null;
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
