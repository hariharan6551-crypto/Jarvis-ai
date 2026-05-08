const { app, BrowserWindow, ipcMain, globalShortcut, session } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let backendProcess;
const isDev = !app.isPackaged;

function startBackend() {
  const backendDir = path.join(__dirname, '..', '..', 'backend');
  console.log('Starting backend from:', backendDir);
  backendProcess = spawn('python', ['main.py'], {
    cwd: backendDir,
    stdio: 'pipe',
    windowsHide: true,
  });
  backendProcess.stdout.on('data', (d) => console.log('[Backend]', d.toString().trim()));
  backendProcess.stderr.on('data', (d) => console.log('[Backend]', d.toString().trim()));
  backendProcess.on('error', (e) => console.error('Backend start error:', e));
}

function createWindow() {
  // Auto-allow microphone permissions
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    if (permission === 'media' || permission === 'microphone' || permission === 'audio') {
      callback(true);
    } else {
      callback(true);
    }
  });

  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1100,
    minHeight: 700,
    frame: false,
    titleBarStyle: 'hidden',
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      webSecurity: false,
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

  mainWindow.on('closed', () => { mainWindow = null; });
}

app.whenReady().then(() => {
  // Start backend first
  startBackend();

  // Wait 2s for backend, then open window
  setTimeout(createWindow, 2000);

  // Global shortcut: Ctrl+Shift+J to show/hide
  globalShortcut.register('CommandOrControl+Shift+J', () => {
    if (mainWindow) {
      if (mainWindow.isVisible()) mainWindow.hide();
      else { mainWindow.show(); mainWindow.focus(); }
    }
  });
});

ipcMain.on('window-minimize', () => mainWindow?.minimize());
ipcMain.on('window-maximize', () => {
  if (mainWindow?.isMaximized()) mainWindow.unmaximize();
  else mainWindow?.maximize();
});
ipcMain.on('window-close', () => mainWindow?.close());

app.on('window-all-closed', () => {
  globalShortcut.unregisterAll();
  // Kill backend when app closes
  if (backendProcess) {
    try { backendProcess.kill(); } catch (e) {}
  }
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  if (backendProcess) {
    try { backendProcess.kill(); } catch (e) {}
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
