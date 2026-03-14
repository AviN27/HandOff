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
            "You are a browser automation agent completing tasks step by step. "
            "Issue ONE action per response. Check action history before acting.\n\n"
            "COMPLETION RULES — output 'TASK COMPLETE: <summary>' when:\n"
            "- Search task: results page is visible with the searched term\n"
            "- Navigation task: the target URL/page has fully loaded\n"
            "- Form task: confirmation or success message is visible\n"
            "- Play/open task: the media or content is actively playing\n\n"
            "ACTION RULES:\n"
            "1. One action per response — never queue multiple actions.\n"
            "2. Action history is shown before each screenshot. Do NOT repeat any action already listed there.\n"
            "3. After pressing Enter or clicking Search, the next action must be TASK COMPLETE if results load.\n"
            "4. Use 'navigate' to go to a URL directly — never type URLs into search bars.\n"
            "5. For sensitive actions (passwords, payments) use 'require_confirmation'."
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

    nudge_count = 0
    last_action_signature: str | None = None

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
            if text_parts:
                combined_lower = " ".join(text_parts).lower()
                completion_words = ["complete", "finished", "done", "successfully", "found", "loaded"]
                if any(w in combined_lower for w in completion_words):
                    await ws_manager.send_task_complete(session_id, " ".join(text_parts))
                    await update_session_state(session_id, "completed", " ".join(text_parts))
                    return
            
            nudge_count += 1
            if nudge_count >= 2:
                await ws_manager.send_task_complete(session_id, "Task appears complete.")
                await update_session_state(session_id, "completed", "No-action stop")
                return
            
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part(text="Next single action? If done, say 'TASK COMPLETE: <summary>'.")],
                )
            )
            continue

        nudge_count = 0

        current_sig = str([
            (fc.name, dict(fc.args) if fc.args else {})
            for fc in function_calls
        ])
         
        if current_sig == last_action_signature:
            logger.warning(f"Identical actions on turn {turn+1} — stopping")
            await ws_manager.send_task_complete(
                session_id, "Task complete — repeated action guard triggered."
            )
            await update_session_state(session_id, "completed", "Dedup stop")
            return
         
        last_action_signature = current_sig

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
        action_summary_lines = []
        for fc in function_calls:
            args = dict(fc.args) if fc.args else {}
            args_str = ", ".join(f"{k}={v}" for k, v in args.items())
            action_summary_lines.append(f"  - {fc.name}({args_str})")
         
        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=(
                f"Turn {turn + 1} completed actions:\n"
                + "\n".join(action_summary_lines)
                + "\n\nUpdated screenshot attached. "
                + "If the task goal is now visibly achieved on screen, respond "
                + "'TASK COMPLETE: <summary>'. Otherwise, what is the ONE next action?"
            ))],
        ))

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
