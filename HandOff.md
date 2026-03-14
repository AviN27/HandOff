UDAA Project Handoff Context
Project Name: Universal Digital Accessibility Agent (UDAA)
Current Status: Version 1.0 (Live Browser Stable)
Last Updated: 2026-03-14

🚀 Mission Statement
UDAA is a multimodal AI agent designed to assist users with accessibility needs by autonomously navigating digital interfaces. It observes the screen via real-time screenshots, processes the UI context using Gemini, and executes native browser actions (click, type, scroll).

🛠 Technical Architecture
The system uses a Hybrid architecture to balance user persistence with AI autonomy.

- **Backend**: FastAPI (Python 3.11).
- **Frontend**: Next.js 15+ (TypeScript, Tailwind CSS).
- **Browser Control**:
    - **Remote Mode**: Playwright (Isolated sandboxed browser).
    - **Live Mode**: Chrome Extension + Python `webbrowser` module. This bypasses profile locks and allows the AI to operate within the user's logged-in Chrome session (Netflix, WhatsApp, etc.).
- **AI Core**:
    - **Action Engine**: `gemini-2.5-computer-use-preview-10-2025`.
    - **Narration Engine**: `gemini-2.0-flash-exp` (via Gemini Live API).

💡 Key Features & Recent Fixes (CRITICAL)

1. **Live Browser Persistence**
   - We moved away from Playwright for Live Mode to avoid OS-level file locks on the user's Chrome profile.
   - The backend now opens a standard Chrome tab with a `udaa_session_id` parameter. The extension auto-connects to the backend via WebSocket.

2. **Keystroke & Action Parsing**
   - Gemini's Computer Use model emits special strings like `backspace*11` or `control+a`.
   - The `content_script.js` now contains a robust parser to translate these strings into real DOM keyboard events and value deletions.
   - Coordinates are scaled from Gemini's 1000x1000 grid to the user's actual `window.innerWidth/Height`.

3. **UI Status Banner**
   - Added a persistent, dark-themed overlay banner in the active tab.
   - It pulses blue during actions and turns green upon task completion.
   - It works even on sites with strict Content Security Policies (CSP) via a fallback renderer in `content_script.js`.

⚙️ Environment Configuration
Ensure `backend/.env` has:
- `COMPUTER_USE_MODEL=gemini-2.5-computer-use-preview-10-2025`
- `LIVE_MODEL=gemini-2.0-flash-exp`
- `USE_FIRESTORE=false` (unless you have a Service Account key).

🤝 Collaboration Protocol
**CRITICAL (Windows)**: Do NOT use `--reload` if you intend to use the Remote Browser (Playwright). It conflicts with the `WindowsProactorEventLoopPolicy`.

- **Start Backend**: `cd backend && .\venv\Scripts\python.exe -m app.main`
- **Start Frontend**: `cd frontend && npm run dev`
- **Extension**: Load the `extension/` folder as an "Unpacked Extension" in Chrome.

📂 Check `task.md` for the current checklist status.