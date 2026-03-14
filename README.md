# Universal Digital Accessibility Agent (UDAA) ☸️

**UDAA** is an AI-powered co-pilot designed to become the "hands on screen" for users with accessibility needs. By combining **Gemini 2.5 Computer Use** for visual navigation and **Gemini 2.0 Live API** for real-time narration, UDAA bridge the gap between user intent and complex digital interfaces.

Built for the **Gemini Live Agent Challenge** under the **UI Navigator** category.

---

## 🌟 Key Features

- **Hybrid Browser Engine**: 
    - **Remote Mode**: Uses Playwright for an isolated, sandboxed experience.
    - **Live Mode**: Uses a custom Chrome Extension to pilot the user's *actual* browser session—perfect for Netflix, WhatsApp, or any site where the user is already logged in.
- **Multimodal Visual Intelligence**: Interprets screens purely through images/screenshots using `gemini-2.5-computer-use-preview`.
- **Real-Time Audio/Text Narration**: Summarizes every action and observation as it happens via `gemini-2.0-flash-exp` (Gemini Live).
- **Interactive Overlay**: A floating status banner in the browser tab keeps the user informed of the AI's thoughts and current actions.
- **Safety First**: Built-in "Require Confirmation" system stops the AI before performing sensitive actions like payments or password changes.

---

## 🛠 Tech Stack

- **AI**: Gemini Multi-modal (Computer Use), Gemini Live (Narration)
- **Frontend**: Next.js 15, TypeScript, Vanilla CSS (Premium Dark Mode)
- **Backend**: FastAPI, Python 3.11, Playwright (Remote Engine)
- **Integration**: Chrome Manifest V3 Extension (Live Engine)
- **Infrastructure**: Designed for Google Cloud Run & Firestore

---

## 🚀 Quick Start

### 1. Backend Setup
```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Install deps:
pip install -r requirements.txt
playwright install chromium
```
Create `backend/.env` with your `GOOGLE_API_KEY`.

**Run (Windows Warning: Do not use --reload if using Remote Mode):**
```bash
.\venv\Scripts\python.exe -m app.main
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000).

### 3. Live Browser Extension
1. Open Chrome and go to `chrome://extensions`.
2. Enable "Developer mode" (top right).
3. Click "Load unpacked" and select the `extension/` folder in this repo.

Once loaded, UDAA will automatically connect to any tab it opens!

---

## 🏆 Hackathon Alignment: UI Navigator Track

UDAA addresses the core requirements of the **UI Navigator** track by:
1. **Becoming the user's hands**: Direct physical manipulation of the browser.
2. **Visual Understanding**: Interpreting UI with or *without* DOM access (Live mode is 100% visual coordinate based).
3. **Multimodal Core**: Every action is guided by the latest Gemini multimodal screenshot processing.
