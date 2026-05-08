"""
J.A.R.V.I.S Vision & OCR Engine
Screen reading, UI element detection, and intelligent clicking.
"""

import asyncio
import os
import time
from pathlib import Path
from typing import Optional
from core.logger import get_logger

log = get_logger("vision")


class VisionEngine:
    """Screen understanding through OCR, element detection, and smart interactions."""

    def __init__(self):
        self.tesseract_available = False
        self.pyautogui = None
        self._init_modules()
        log.info("Vision engine initialized")

    def _init_modules(self):
        """Initialize vision modules."""
        try:
            import pyautogui
            self.pyautogui = pyautogui
        except ImportError:
            log.warning("pyautogui not available for vision")

        try:
            import pytesseract
            # Try to find Tesseract
            tesseract_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                r"C:\Users\harih\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
            ]
            for p in tesseract_paths:
                if os.path.exists(p):
                    pytesseract.pytesseract.tesseract_cmd = p
                    break
            self.pytesseract = pytesseract
            self.tesseract_available = True
            log.info("Tesseract OCR available")
        except ImportError:
            log.warning("pytesseract not installed (OCR will be limited)")
            self.pytesseract = None

    # ─── Screen Capture ───────────────────────────────────────────────

    async def capture_screen(self, region=None) -> Optional[object]:
        """Capture screenshot of the full screen or a region."""
        try:
            if self.pyautogui:
                img = await asyncio.to_thread(self.pyautogui.screenshot, region=region)
                return img
            return None
        except Exception as e:
            log.error(f"Screen capture failed: {e}")
            return None

    async def capture_active_window(self) -> Optional[object]:
        """Capture screenshot of only the active window."""
        try:
            import pygetwindow as gw
            win = gw.getActiveWindow()
            if win:
                region = (win.left, win.top, win.width, win.height)
                return await self.capture_screen(region=region)
            return await self.capture_screen()
        except Exception as e:
            log.warning(f"Active window capture fallback to full screen: {e}")
            return await self.capture_screen()

    # ─── OCR Text Extraction ─────────────────────────────────────────

    async def read_screen_text(self, region=None) -> dict:
        """Read all text visible on screen using OCR."""
        img = await self.capture_screen(region=region)
        if img is None:
            return {"success": False, "message": "Screen capture failed", "text": ""}

        if not self.tesseract_available:
            return {"success": False, "message": "Tesseract OCR not installed", "text": ""}

        try:
            text = await asyncio.to_thread(self.pytesseract.image_to_string, img)
            return {
                "success": True,
                "text": text.strip(),
                "char_count": len(text.strip()),
            }
        except Exception as e:
            log.error(f"OCR failed: {e}")
            return {"success": False, "message": str(e), "text": ""}

    async def read_active_window_text(self) -> dict:
        """Read text from the active window only."""
        img = await self.capture_active_window()
        if img is None:
            return {"success": False, "message": "Window capture failed", "text": ""}

        if not self.tesseract_available:
            return {"success": False, "message": "Tesseract OCR not installed", "text": ""}

        try:
            text = await asyncio.to_thread(self.pytesseract.image_to_string, img)
            return {"success": True, "text": text.strip()}
        except Exception as e:
            return {"success": False, "message": str(e), "text": ""}

    # ─── UI Element Detection ────────────────────────────────────────

    async def find_text_on_screen(self, target_text: str, region=None) -> dict:
        """Find the screen coordinates of specific text using OCR."""
        img = await self.capture_screen(region=region)
        if img is None or not self.tesseract_available:
            return {"success": False, "message": "Vision not available"}

        try:
            # Get bounding boxes for all detected text
            data = await asyncio.to_thread(
                self.pytesseract.image_to_data, img, output_type=self.pytesseract.Output.DICT
            )

            target_lower = target_text.lower()
            matches = []

            # Search for multi-word matches
            words = data["text"]
            n = len(words)

            for i in range(n):
                # Build consecutive word groups
                for j in range(i + 1, min(i + 6, n + 1)):
                    phrase = " ".join(words[i:j]).strip()
                    if not phrase:
                        continue
                    if target_lower in phrase.lower():
                        # Calculate bounding box of the phrase
                        left = min(data["left"][k] for k in range(i, j) if data["text"][k].strip())
                        top = min(data["top"][k] for k in range(i, j) if data["text"][k].strip())
                        right = max(
                            data["left"][k] + data["width"][k]
                            for k in range(i, j)
                            if data["text"][k].strip()
                        )
                        bottom = max(
                            data["top"][k] + data["height"][k]
                            for k in range(i, j)
                            if data["text"][k].strip()
                        )

                        cx = (left + right) // 2
                        cy = (top + bottom) // 2

                        matches.append({
                            "text": phrase,
                            "x": cx,
                            "y": cy,
                            "left": left,
                            "top": top,
                            "width": right - left,
                            "height": bottom - top,
                            "confidence": sum(
                                data["conf"][k] for k in range(i, j) if data["text"][k].strip()
                            ) / max(1, j - i),
                        })
                        break

            if matches:
                # Sort by confidence
                matches.sort(key=lambda m: m["confidence"], reverse=True)
                return {
                    "success": True,
                    "found": True,
                    "matches": matches[:5],
                    "best_match": matches[0],
                    "message": f"Found '{target_text}' at ({matches[0]['x']}, {matches[0]['y']})",
                }

            return {
                "success": True,
                "found": False,
                "matches": [],
                "message": f"Text '{target_text}' not found on screen",
            }
        except Exception as e:
            log.error(f"Text search failed: {e}")
            return {"success": False, "message": str(e)}

    async def click_on_text(self, target_text: str) -> dict:
        """Find text on screen using OCR and click on it."""
        result = await self.find_text_on_screen(target_text)
        if not result.get("found"):
            return {"success": False, "message": f"Could not find '{target_text}' on screen"}

        match = result["best_match"]
        x, y = match["x"], match["y"]

        if self.pyautogui:
            await asyncio.to_thread(self.pyautogui.click, x, y)
            return {
                "success": True,
                "message": f"Clicked on '{target_text}' at ({x}, {y})",
                "coordinates": {"x": x, "y": y},
            }
        return {"success": False, "message": "pyautogui not available for clicking"}

    # ─── Active Window Detection ──────────────────────────────────────

    async def get_active_window_info(self) -> dict:
        """Get information about the currently active window."""
        try:
            import pygetwindow as gw
            win = gw.getActiveWindow()
            if win:
                return {
                    "success": True,
                    "title": win.title,
                    "position": {"x": win.left, "y": win.top},
                    "size": {"width": win.width, "height": win.height},
                    "is_maximized": win.isMaximized,
                    "is_minimized": win.isMinimized,
                }
            return {"success": False, "message": "No active window detected"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def list_all_windows(self) -> dict:
        """List all open windows."""
        try:
            import pygetwindow as gw
            windows = gw.getAllWindows()
            visible = [
                {
                    "title": w.title,
                    "position": {"x": w.left, "y": w.top},
                    "size": {"width": w.width, "height": w.height},
                    "visible": w.visible,
                }
                for w in windows
                if w.title.strip() and w.visible
            ]
            return {"success": True, "windows": visible, "count": len(visible)}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ─── Smart Button Detection ──────────────────────────────────────

    async def find_button(self, button_text: str) -> dict:
        """
        Find a button on screen by its text label.
        Looks for common button patterns (OK, Cancel, Submit, etc.)
        """
        result = await self.find_text_on_screen(button_text)
        if result.get("found"):
            return {
                "success": True,
                "button_found": True,
                "location": result["best_match"],
                "message": f"Button '{button_text}' found",
            }
        return {
            "success": True,
            "button_found": False,
            "message": f"Button '{button_text}' not found on screen",
        }

    async def click_button(self, button_text: str) -> dict:
        """Find and click a button by its text."""
        return await self.click_on_text(button_text)

    # ─── Screen State Analysis ────────────────────────────────────────

    async def analyze_screen(self) -> dict:
        """
        Comprehensive screen analysis: active window + visible text + detected elements.
        Useful for AI reasoning about what's on screen.
        """
        window_info = await self.get_active_window_info()
        screen_text = await self.read_active_window_text()

        return {
            "success": True,
            "active_window": window_info,
            "screen_text": screen_text.get("text", "")[:3000],
            "timestamp": time.time(),
        }
