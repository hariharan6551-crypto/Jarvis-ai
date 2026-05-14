"""
J.A.R.V.I.S File Manager Service
Find, create, move, delete, compress files on Windows.
"""

import asyncio, os, shutil, zipfile
from pathlib import Path
from datetime import datetime
from core.logger import get_logger

log = get_logger("file_manager")

USER_HOME = Path.home()
DESKTOP = USER_HOME / "Desktop"
DOWNLOADS = USER_HOME / "Downloads"
DOCUMENTS = USER_HOME / "Documents"


class FileManager:
    def __init__(self):
        log.info("File manager initialized")

    async def find_file(self, filename: str, search_path: str = None) -> dict:
        search_dirs = [search_path] if search_path else [str(DESKTOP), str(DOWNLOADS), str(DOCUMENTS)]
        results = []
        def _search():
            for base in search_dirs:
                if not os.path.exists(base): continue
                try:
                    for root, dirs, files in os.walk(base):
                        dirs[:] = [d for d in dirs if d not in ('node_modules','__pycache__','.git','AppData','Windows','$Recycle.Bin')]
                        for f in files:
                            if filename.lower() in f.lower():
                                fp = os.path.join(root, f)
                                try:
                                    st = os.stat(fp)
                                    results.append({"name": f, "path": fp, "size": self._hs(st.st_size), "modified": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")})
                                except: pass
                        if len(results) >= 20: return
                except: continue
        await asyncio.to_thread(_search)
        if results:
            return {"success": True, "message": f"Found {len(results)} file(s) matching '{filename}'.", "files": results[:10]}
        return {"success": False, "message": f"Couldn't find '{filename}' on your system, Sir."}

    async def create_file(self, filename: str, content: str = "", directory: str = None) -> dict:
        target = Path(directory) if directory else DESKTOP
        target.mkdir(parents=True, exist_ok=True)
        fp = target / filename
        try:
            await asyncio.to_thread(lambda: fp.write_text(content, encoding="utf-8"))
            return {"success": True, "message": f"Created {filename} on {target.name}, Sir.", "path": str(fp)}
        except Exception as e:
            return {"success": False, "message": f"Failed to create {filename}: {e}"}

    async def delete_file(self, filepath: str) -> dict:
        p = Path(filepath)
        if not p.exists(): return {"success": False, "message": f"File not found: {filepath}"}
        try:
            from send2trash import send2trash
            await asyncio.to_thread(send2trash, str(p))
            return {"success": True, "message": f"Moved {p.name} to Recycle Bin, Sir."}
        except ImportError:
            if p.is_file(): os.remove(p)
            else: shutil.rmtree(p)
            return {"success": True, "message": f"Deleted {p.name}, Sir."}

    async def move_file(self, source: str, dest: str) -> dict:
        src = Path(source)
        if not src.exists(): return {"success": False, "message": f"Source not found: {source}"}
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(shutil.move, str(src), dest)
        return {"success": True, "message": f"Moved {src.name}, Sir."}

    async def copy_file(self, source: str, dest: str) -> dict:
        src = Path(source)
        if not src.exists(): return {"success": False, "message": f"Source not found: {source}"}
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        if src.is_file(): await asyncio.to_thread(shutil.copy2, str(src), dest)
        else: await asyncio.to_thread(shutil.copytree, str(src), dest)
        return {"success": True, "message": f"Copied {src.name}, Sir."}

    async def compress_folder(self, folder_path: str) -> dict:
        folder = Path(folder_path)
        if not folder.exists(): return {"success": False, "message": f"Folder not found"}
        zp = folder.parent / f"{folder.name}.zip"
        def _zip():
            with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, _, files in os.walk(folder):
                    for f in files:
                        full = os.path.join(root, f)
                        zf.write(full, os.path.relpath(full, folder.parent))
        await asyncio.to_thread(_zip)
        return {"success": True, "message": f"Compressed to {zp.name} ({self._hs(zp.stat().st_size)}), Sir."}

    async def list_directory(self, directory: str = None) -> dict:
        target = Path(directory) if directory else DOWNLOADS
        if not target.exists(): return {"success": False, "message": f"Directory not found"}
        items = []
        for item in sorted(target.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:20]:
            try:
                st = item.stat()
                items.append({"name": item.name, "is_dir": item.is_dir(), "size": self._hs(st.st_size) if item.is_file() else "", "modified": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")})
            except: pass
        return {"success": True, "message": f"{target.name} has {len(items)} items.", "items": items}

    async def find_large_files(self, min_mb: int = 100) -> dict:
        min_bytes = min_mb * 1024 * 1024
        results = []
        def _s():
            for root, dirs, files in os.walk(USER_HOME):
                dirs[:] = [d for d in dirs if d not in ('node_modules','.git','AppData','Windows')]
                for f in files:
                    try:
                        fp = os.path.join(root, f)
                        sz = os.path.getsize(fp)
                        if sz >= min_bytes: results.append({"name": f, "path": fp, "size": self._hs(sz), "size_bytes": sz})
                    except: pass
                if len(results) >= 20: return
        await asyncio.to_thread(_s)
        results.sort(key=lambda x: x.get("size_bytes",0), reverse=True)
        return {"success": True, "message": f"Found {len(results)} large file(s), Sir.", "files": results[:15]}

    @staticmethod
    def _hs(b: int) -> str:
        for u in ['B','KB','MB','GB','TB']:
            if b < 1024: return f"{b:.1f} {u}"
            b /= 1024
        return f"{b:.1f} PB"
