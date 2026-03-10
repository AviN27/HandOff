"""Playwright browser manager and action executor."""

import base64
import logging
from typing import Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


from .base_adapter import BrowserAdapter

class PlaywrightAdapter(BrowserAdapter):
    """Manages a headless Chromium browser via Playwright."""

    def __init__(self):
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    async def launch(self) -> Page:
        """Launch the browser and return the page."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ]
        )
        self._context = await self._browser.new_context(
            viewport={
                "width": settings.SCREEN_WIDTH,
                "height": settings.SCREEN_HEIGHT,
            },
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        self._page = await self._context.new_page()
        logger.info(
            f"Browser launched: {settings.SCREEN_WIDTH}x{settings.SCREEN_HEIGHT}"
        )
        return self._page

    @property
    def page(self) -> Page | None:
        return self._page

    async def capture_screenshot(self) -> bytes:
        """Capture a PNG screenshot of the current page."""
        if not self._page:
            raise RuntimeError("Browser not launched")
        return await self._page.screenshot(type="png", full_page=False)

    async def capture_screenshot_b64(self) -> str:
        """Capture screenshot and return as base64 string."""
        raw = await self.capture_screenshot()
        return base64.b64encode(raw).decode("utf-8")

    def denormalize_coords(self, x_norm: int, y_norm: int) -> tuple[int, int]:
        """Convert normalized 0-999 coordinates to screen pixels."""
        x = int((x_norm * settings.SCREEN_WIDTH) / 1000)
        y = int((y_norm * settings.SCREEN_HEIGHT) / 1000)
        return x, y

    async def execute_action(self, action_name: str, args: dict[str, Any]) -> dict:
        """Execute a Computer Use action on the browser page.

        Returns a dict describing what was done.
        """
        if not self._page:
            raise RuntimeError("Browser not launched")

        page = self._page
        result = {"action": action_name, "args": args, "success": True}

        try:
            if action_name == "click_at":
                x, y = self.denormalize_coords(args["x"], args["y"])
                button = args.get("button", "left")
                await page.mouse.click(x, y, button=button)
                result["detail"] = f"Clicked at ({x}, {y})"

            elif action_name == "type_text_at":
                x, y = self.denormalize_coords(args["x"], args["y"])
                text = args["text"]
                await page.mouse.click(x, y)
                await page.keyboard.type(text, delay=50)
                result["detail"] = f"Typed '{text[:50]}' at ({x}, {y})"

            elif action_name == "hover_at":
                x, y = self.denormalize_coords(args["x"], args["y"])
                await page.mouse.move(x, y)
                result["detail"] = f"Hovered at ({x}, {y})"

            elif action_name == "scroll_document":
                direction = args.get("direction", "down")
                amount = args.get("amount", 3)
                delta = amount * 100 if direction == "down" else -(amount * 100)
                await page.mouse.wheel(0, delta)
                result["detail"] = f"Scrolled {direction} by {amount}"

            elif action_name == "scroll_at":
                x, y = self.denormalize_coords(args["x"], args["y"])
                direction = args.get("direction", "down")
                amount = args.get("amount", 3)
                delta = amount * 100 if direction == "down" else -(amount * 100)
                await page.mouse.move(x, y)
                await page.mouse.wheel(0, delta)
                result["detail"] = f"Scrolled {direction} at ({x}, {y})"

            elif action_name == "navigate":
                url = args["url"]
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                result["detail"] = f"Navigated to {url}"

            elif action_name == "open_web_browser":
                url = args.get("url", "about:blank")
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                result["detail"] = f"Opened browser at {url}"

            elif action_name == "go_back":
                await page.go_back(wait_until="domcontentloaded", timeout=15000)
                result["detail"] = "Went back"

            elif action_name == "go_forward":
                await page.go_forward(wait_until="domcontentloaded", timeout=15000)
                result["detail"] = "Went forward"

            elif action_name == "key_combination":
                keys = args.get("keys", [])
                for key in keys:
                    await page.keyboard.down(key)
                for key in reversed(keys):
                    await page.keyboard.up(key)
                result["detail"] = f"Key combo: {'+'.join(keys)}"

            elif action_name == "drag_and_drop":
                sx, sy = self.denormalize_coords(
                    args["start_x"], args["start_y"]
                )
                ex, ey = self.denormalize_coords(
                    args["end_x"], args["end_y"]
                )
                await page.mouse.move(sx, sy)
                await page.mouse.down()
                await page.mouse.move(ex, ey, steps=10)
                await page.mouse.up()
                result["detail"] = f"Dragged ({sx},{sy}) → ({ex},{ey})"

            elif action_name == "wait_5_seconds":
                import asyncio
                await asyncio.sleep(5)
                result["detail"] = "Waited 5 seconds"

            else:
                result["success"] = False
                result["detail"] = f"Unknown action: {action_name}"
                logger.warning(f"Unknown action: {action_name}")

        except Exception as e:
            result["success"] = False
            result["detail"] = f"Error: {str(e)}"
            logger.error(f"Action {action_name} failed: {e}")

        return result

    async def close(self):
        """Close the browser and cleanup."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Browser closed")
