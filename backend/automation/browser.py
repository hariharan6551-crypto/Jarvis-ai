"""
J.A.R.V.I.S Browser Automation Engine
Chrome profile detection, browser control, and Playwright-based automation.
"""

import asyncio
import json
import os
import re
import subprocess
import shutil
from pathlib import Path
from typing import Optional
from core.logger import get_logger

log = get_logger("browser")


class BrowserEngine:
    """Handles browser automation: profile detection, navigation, form filling, tab management."""

    def __init__(self):
        self.chrome_user_data_dir = self._find_chrome_user_data()
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        log.info("Browser engine initialized")

    def _find_chrome_user_data(self) -> str:
        """Locate Chrome's user data directory."""
        possible_paths = [
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data"),
            os.path.expandvars(r"%USERPROFILE%\AppData\Local\Google\Chrome\User Data"),
        ]
        for p in possible_paths:
            if os.path.isdir(p):
                log.info(f"Chrome user data found: {p}")
                return p
        log.warning("Chrome user data directory not found")
        return ""

    # ─── Chrome Profile Detection ─────────────────────────────────────

    def detect_chrome_profiles(self) -> list[dict]:
        """
        Detect all Chrome profiles by reading the Local State file.
        Returns list of dicts: [{"name": "Profile Name", "dir": "Profile 1", "email": "..."}, ...]
        """
        profiles = []
        if not self.chrome_user_data_dir:
            return profiles

        local_state_path = os.path.join(self.chrome_user_data_dir, "Local State")
        if not os.path.exists(local_state_path):
            log.warning("Chrome Local State file not found")
            return profiles

        try:
            with open(local_state_path, "r", encoding="utf-8") as f:
                state = json.load(f)

            info_cache = state.get("profile", {}).get("info_cache", {})
            for dir_name, profile_data in info_cache.items():
                name = profile_data.get("name", dir_name)
                gaia_name = profile_data.get("gaia_name", "")
                email = profile_data.get("user_name", "")
                avatar = profile_data.get("avatar_icon", "")

                profiles.append({
                    "name": gaia_name or name,
                    "display_name": name,
                    "dir": dir_name,
                    "email": email,
                    "avatar": avatar,
                    "is_using_default_name": profile_data.get("is_using_default_name", True),
                })

            log.info(f"Detected {len(profiles)} Chrome profiles: {[p['name'] for p in profiles]}")
        except Exception as e:
            log.error(f"Failed to read Chrome profiles: {e}")

        return profiles

    def find_profile_by_name(self, target_name: str) -> Optional[dict]:
        """
        Find a Chrome profile matching the given name (fuzzy match).
        Searches across name, display_name, gaia_name, and email.
        """
        profiles = self.detect_chrome_profiles()
        target_lower = target_name.lower().strip()

        # Exact match first
        for p in profiles:
            if p["name"].lower() == target_lower or p["display_name"].lower() == target_lower:
                return p
            if p.get("email", "").lower().split("@")[0] == target_lower:
                return p

        # Partial match
        for p in profiles:
            if target_lower in p["name"].lower() or target_lower in p["display_name"].lower():
                return p
            if target_lower in p.get("email", "").lower():
                return p

        # Word-level fuzzy match
        target_words = set(target_lower.split())
        best_match = None
        best_score = 0
        for p in profiles:
            name_words = set(p["name"].lower().split())
            display_words = set(p["display_name"].lower().split())
            all_words = name_words | display_words
            overlap = len(target_words & all_words)
            if overlap > best_score:
                best_score = overlap
                best_match = p

        if best_match and best_score > 0:
            return best_match

        return None

    async def open_chrome_with_profile(self, profile_name: str) -> dict:
        """Open Chrome with a specific profile."""
        profile = self.find_profile_by_name(profile_name)
        if not profile:
            available = self.detect_chrome_profiles()
            names = [p["name"] for p in available]
            return {
                "success": False,
                "message": f"Profile '{profile_name}' not found. Available profiles: {', '.join(names)}",
                "available_profiles": names,
            }

        profile_dir = profile["dir"]
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]

        chrome_exe = None
        for p in chrome_paths:
            if os.path.exists(p):
                chrome_exe = p
                break

        if not chrome_exe:
            # Fallback: use 'start chrome' and hope for the best
            chrome_exe = "chrome"

        try:
            cmd = f'"{chrome_exe}" --profile-directory="{profile_dir}"'
            log.info(f"Launching Chrome: {cmd}")
            await asyncio.to_thread(
                subprocess.Popen, cmd, shell=True,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return {
                "success": True,
                "message": f"Chrome opened with profile: {profile['name']}",
                "profile": profile,
            }
        except Exception as e:
            log.error(f"Failed to open Chrome with profile: {e}")
            return {"success": False, "message": f"Failed to open Chrome: {str(e)}"}

    async def list_profiles(self) -> dict:
        """List all detected Chrome profiles."""
        profiles = self.detect_chrome_profiles()
        return {
            "success": True,
            "profiles": profiles,
            "count": len(profiles),
            "message": f"Found {len(profiles)} Chrome profiles",
        }

    # ─── Playwright Browser Automation ────────────────────────────────

    async def init_playwright(self, profile_dir: str = None):
        """Initialize Playwright with optional Chrome profile."""
        try:
            from playwright.async_api import async_playwright

            self.playwright = await async_playwright().start()

            launch_args = ["--start-maximized"]
            if profile_dir and self.chrome_user_data_dir:
                user_data = self.chrome_user_data_dir
                launch_args.extend([
                    f"--profile-directory={profile_dir}",
                ])
                self.browser = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=user_data,
                    headless=False,
                    args=launch_args,
                    channel="chrome",
                )
                self.page = self.browser.pages[0] if self.browser.pages else await self.browser.new_page()
            else:
                self.browser = await self.playwright.chromium.launch(
                    headless=False,
                    args=launch_args,
                    channel="chrome",
                )
                self.context = await self.browser.new_context()
                self.page = await self.context.new_page()

            log.info("Playwright browser initialized")
            return True
        except ImportError:
            log.warning("Playwright not installed. Install with: pip install playwright && playwright install")
            return False
        except Exception as e:
            log.error(f"Playwright init failed: {e}")
            return False

    async def navigate_to(self, url: str) -> dict:
        """Navigate Playwright browser to a URL."""
        if not self.page:
            return {"success": False, "message": "Browser not initialized. Use init_playwright first."}
        try:
            await self.page.goto(url, wait_until="domcontentloaded")
            return {"success": True, "message": f"Navigated to {url}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def fill_form_field(self, selector: str, value: str) -> dict:
        """Fill a form field by CSS selector."""
        if not self.page:
            return {"success": False, "message": "Browser not initialized"}
        try:
            await self.page.fill(selector, value)
            return {"success": True, "message": f"Filled field: {selector}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def click_element(self, selector: str) -> dict:
        """Click an element by CSS selector or text content."""
        if not self.page:
            return {"success": False, "message": "Browser not initialized"}
        try:
            await self.page.click(selector, timeout=5000)
            return {"success": True, "message": f"Clicked: {selector}"}
        except Exception:
            try:
                # Try by text content
                await self.page.get_by_text(selector, exact=False).first.click(timeout=5000)
                return {"success": True, "message": f"Clicked text: {selector}"}
            except Exception as e:
                return {"success": False, "message": str(e)}

    async def get_page_text(self) -> dict:
        """Get all visible text from the current page."""
        if not self.page:
            return {"success": False, "message": "Browser not initialized"}
        try:
            text = await self.page.inner_text("body")
            return {"success": True, "text": text[:5000]}  # Limit for safety
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def screenshot_page(self) -> dict:
        """Take a screenshot of the current page."""
        if not self.page:
            return {"success": False, "message": "Browser not initialized"}
        try:
            import time
            path = Path.home() / "Pictures" / "JARVIS_Screenshots" / f"browser_{int(time.time())}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            await self.page.screenshot(path=str(path))
            return {"success": True, "message": "Browser screenshot saved", "path": str(path)}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def get_tabs(self) -> dict:
        """List all open tabs."""
        if not self.context and not self.browser:
            return {"success": False, "message": "Browser not initialized"}
        try:
            ctx = self.context or self.browser
            pages = ctx.pages
            tabs = [{"index": i, "title": p.title, "url": p.url} for i, p in enumerate(pages)]
            return {"success": True, "tabs": tabs, "count": len(tabs)}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def switch_tab(self, index: int) -> dict:
        """Switch to a specific tab by index."""
        if not self.context and not self.browser:
            return {"success": False, "message": "Browser not initialized"}
        try:
            ctx = self.context or self.browser
            pages = ctx.pages
            if 0 <= index < len(pages):
                self.page = pages[index]
                await self.page.bring_to_front()
                return {"success": True, "message": f"Switched to tab {index}: {self.page.title}"}
            return {"success": False, "message": f"Tab index {index} out of range (0-{len(pages)-1})"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def close_playwright(self):
        """Clean up Playwright resources."""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            self.browser = None
            self.context = None
            self.page = None
            self.playwright = None
            log.info("Playwright closed")
        except Exception as e:
            log.error(f"Playwright cleanup error: {e}")
