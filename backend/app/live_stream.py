"""Gemini Live API streaming for real-time narration."""

import asyncio
import base64
import logging
from google import genai
from google.genai import types

from app.config import get_settings
from app.browser_adapters.base_adapter import BrowserAdapter
from app.websocket import manager as ws_manager

logger = logging.getLogger(__name__)
settings = get_settings()


async def run_live_stream(
    session_id: str,
    task: str,
    browser: BrowserAdapter,
):
    """Run a Gemini Live API streaming session for real-time narration.

    Continuously streams screenshots to Gemini and receives
    natural language narration of what's happening on screen.
    """
    client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    config = types.LiveConnectConfig(
        response_modalities=["TEXT"],
        system_instruction=types.Content(
            parts=[
                types.Part(
                    text=(
                        "You are a real-time screen narrator for a digital accessibility agent. "
                        "You observe screenshots of a web browser and describe what you see "
                        "in simple, clear language. Focus on: what is currently on screen, "
                        "what the agent is doing, and what will happen next. "
                        "Keep narrations short (1-2 sentences). "
                        "Use friendly, encouraging language suitable for elderly or "
                        "non-technical users. Example: 'The agent is now typing your "
                        "destination in the search box. It found the train booking page.'"
                    )
                )
            ]
        ),
    )

    try:
        async with client.aio.live.connect(
            model=settings.LIVE_MODEL,
            config=config,
        ) as session:
            logger.info(f"Live API session started for {session_id}")

            # Send initial context
            await session.send_client_content(
                turns=types.Content(
                    parts=[types.Part(text=f"The user wants to: {task}")]
                )
            )

            # Background task to receive narration
            async def receive_narration():
                try:
                    while True:
                        async for response in session.receive():
                            if response.text:
                                await ws_manager.send_narration(
                                    session_id, response.text
                                )
                                logger.debug(f"Narration: {response.text[:100]}")
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"Narration receive error: {e}")

            receiver = asyncio.create_task(receive_narration())

            try:
                # Stream screenshots periodically
                while True:
                    if not browser.page:
                        await asyncio.sleep(1)
                        continue

                    try:
                        screenshot_bytes = await browser.capture_screenshot()

                        # Send as realtime input
                        await session.send_realtime_input(
                            media=types.Blob(
                                data=screenshot_bytes,
                                mime_type="image/png",
                            )
                        )
                    except Exception as e:
                        logger.debug(f"Screenshot stream error: {e}")

                    await asyncio.sleep(settings.SCREENSHOT_INTERVAL)

            except asyncio.CancelledError:
                logger.info(f"Live stream cancelled for {session_id}")
            finally:
                receiver.cancel()
                try:
                    await receiver
                except asyncio.CancelledError:
                    pass

    except Exception as e:
        logger.error(f"Live API connection error: {e}")
        # Live stream is optional — don't crash the agent loop
        await ws_manager.send_narration(
            session_id,
            "Real-time narration is temporarily unavailable."
        )
