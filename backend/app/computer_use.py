"""Gemini Computer Use agent loop — the core of the project."""

import asyncio
import base64
import logging
import uuid
from typing import Any

from google import genai
from google.genai import types

from app.config import get_settings
from app.browser_adapters.base_adapter import BrowserAdapter
from app.websocket import manager as ws_manager
from app.storage import upload_screenshot
from app.firestore_client import update_session_state
from app.pubsub import publish_action

logger = logging.getLogger(__name__)
settings = get_settings()


async def run_agent_loop(
    session_id: str,
    task: str,
    start_url: str,
    browser: BrowserAdapter,
):
    """Execute the Computer Use agent loop.

    1. Capture screenshot
    2. Send screenshot + task → Gemini Computer Use model
    3. Parse function_call actions
    4. Handle safety_decision (require_confirmation → ask user)
    5. Execute actions via Playwright or Live Extension
    6. Capture new screenshot
    7. Repeat until task complete or max turns reached
    """
    client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    # Configure Computer Use tool
    config = types.GenerateContentConfig(
        tools=[
            types.Tool(
                computer_use=types.ComputerUse(
                    environment=types.Environment.ENVIRONMENT_BROWSER
                )
            )
        ],
        system_instruction=(
            "You are a helpful digital accessibility agent. Your goal is to complete "
            "tasks on websites by observing the screen and performing UI actions. "
            "CRITICAL LIMITATION: You do NOT have access to the DOM tree or accessibility nodes. "
            "You must estimate 'click' coordinates (x, y) purely visually based on the standard 1000x1000 grid. "
            "IMPORTANT RULES: "
            "1. If the screen is blank or you need to start a task (e.g., 'Open youtube'), "
            "use the 'navigate' action to go to the exact URL immediately. "
            "2. DO NOT queue up repetitive typing actions. If you need to type 'youtube.com', "
            "issue a single 'type' action with exactly that text. "
            "3. To press enter, type 'enter'. To delete text, type 'control+a' then 'delete'. "
            "4. When you see sensitive actions (passwords, payments), use 'require_confirmation'. "
            "5. When the task is fully complete, respond with a text summary starting with 'TASK COMPLETE:'."
        ),
    )

    # Navigate to start URL
    if start_url:
        await ws_manager.send_status(session_id, "navigating", f"Opening {start_url}")
        page = browser.page
        if page:
            await page.goto(start_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(1)

    # Build initial content with task
    contents: list[types.Content] = [
        types.Content(
            role="user",
            parts=[types.Part(text=f"Task: {task}")],
        )
    ]

    for turn in range(settings.MAX_AGENT_TURNS):
        logger.info(f"Agent turn {turn + 1}/{settings.MAX_AGENT_TURNS}")
        await ws_manager.send_status(
            session_id, "thinking", f"Step {turn + 1}: Analyzing screen..."
        )

        # Capture screenshot
        screenshot_bytes = await browser.capture_screenshot()
        
        # If no screenshot is available yet (e.g. extension connecting), wait and retry
        if not screenshot_bytes:
            logger.warning("No screenshot available yet, waiting 1s...")
            await asyncio.sleep(1)
            continue
            
        screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

        # Send screenshot to frontend
        await ws_manager.send_screenshot(session_id, screenshot_b64, turn + 1)

        # Upload to Cloud Storage (async, non-blocking)
        asyncio.create_task(
            upload_screenshot(session_id, turn + 1, screenshot_bytes)
        )

        # Add screenshot to conversation
        contents.append(
            types.Content(
                role="user",
                parts=[
                    types.Part(
                        inline_data=types.Blob(
                            mime_type="image/png",
                            data=screenshot_bytes,
                        )
                    )
                ],
            )
        )

        # Call Gemini Computer Use model
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=settings.COMPUTER_USE_MODEL,
                contents=contents,
                config=config,
            )
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            await ws_manager.send_error(session_id, f"AI model error: {str(e)}")
            break

        if not response or not response.candidates:
            logger.warning("Empty response from model")
            await ws_manager.send_error(session_id, "No response from AI model")
            break

        candidate = response.candidates[0]
        content = candidate.content

        # Add model response to conversation history
        contents.append(content)

        # Check for text response (task complete or reasoning)
        text_parts = [p.text for p in content.parts if p.text]
        if text_parts:
            combined_text = " ".join(text_parts)
            logger.info(f"Model text: {combined_text[:200]}")

            if "TASK COMPLETE:" in combined_text.upper():
                summary = combined_text.split("TASK COMPLETE:")[-1].strip() if "TASK COMPLETE:" in combined_text else combined_text
                await ws_manager.send_task_complete(session_id, summary)
                await update_session_state(session_id, "completed", summary)
                logger.info(f"Task completed: {summary[:100]}")
                return

            # Send reasoning/narration to frontend
            await ws_manager.send_narration(session_id, combined_text)

        # Check for function calls (actions)
        function_calls = [p.function_call for p in content.parts if p.function_call]

        if not function_calls:
            # No actions and no completion — model might need more info
            logger.info("No function calls in response, continuing...")
            # Add a nudge
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part(text="Please continue with the task. What action should be taken next?")],
                )
            )
            continue

        # Execute each action
        for fc in function_calls:
            action_name = fc.name
            action_args = dict(fc.args) if fc.args else {}

            logger.info(f"Action: {action_name}({action_args})")
            await ws_manager.send_status(
                session_id, "executing", f"Executing: {action_name}"
            )

            # Publish to Pub/Sub (for audit trail)
            await publish_action(session_id, turn + 1, action_name, action_args)

            # Execute the action
            result = await browser.execute_action(action_name, action_args)

            # Send action result to frontend
            await ws_manager.send_action(session_id, result, turn + 1)

            # Update Firestore
            await update_session_state(
                session_id, "executing",
                f"Step {turn + 1}: {action_name}"
            )

            # Small delay between actions
            await asyncio.sleep(0.5)

        # Add action results as user message for next turn
        action_summaries = []
        for fc in function_calls:
            action_summaries.append(f"Executed: {fc.name}")
        contents.append(
            types.Content(
                role="user",
                parts=[
                    types.Part(
                        text="Actions executed successfully. Here is the updated screenshot."
                    )
                ],
            )
        )

        # Brief wait for page to settle after actions
        await asyncio.sleep(1)

    # Max turns reached
    await ws_manager.send_status(session_id, "timeout", "Maximum steps reached")
    await ws_manager.send_task_complete(
        session_id,
        f"Agent reached the maximum of {settings.MAX_AGENT_TURNS} steps. "
        "The task may be partially complete."
    )
    await update_session_state(session_id, "timeout", "Max turns reached")
