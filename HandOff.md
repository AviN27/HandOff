# Universal Digital Accessibility Agent (UDAA)

An AI-powered agent that autonomously navigates digital interfaces using the Gemini Computer Use API and provides real-time narration via the Gemini Live API.

Built for the Gemini Live Agent Challenge under the UI Navigator category.

## Features

- **Autonomous UI Interaction**: Uses Playwright and `gemini-2.5-flash-preview-04-17` to click, type, scroll, and navigate purely from visual understanding.
- **Live Narration**: Uses `gemini-2.5-flash` Live API to narrate what the agent is doing in real-time.
- **Accessibility-First UI**: High-contrast, large font dark theme designed for non-technical users.
- **Safety Driven**: Built-in "require_confirmation" handling for sensitive operations via a frontend modal.
- **GCP Native**: Integrates with Cloud Storage (screenshots), Firestore (session state), Pub/Sub (action queue), and Cloud Logging.

## Architecture

- **Frontend**: Next.js 15, TypeScript, Vanilla CSS, WebSockets
- **Backend**: Python 3.11, FastAPI, Playwright (headless Chromium), Google GenAI SDK

## Quick Start (Local Development)

### 1. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Set your API key in .env
cp .env.example .env

# Run FastAPI server
uvicorn app.main:app --port 8080
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` in your browser.

## Google Cloud Deployment

This project is built to deploy on Google Cloud Run. 

1. **Enable APIs**: Vertex AI, Cloud Storage, Firestore, Pub/Sub, Cloud Run
2. **Build Backend Image**: `docker build -t gcr.io/udaa-489513/backend backend/`
3. **Deploy Backend**: `gcloud run deploy udaa-backend --image gcr.io/udaa-489513/backend --memory 2Gi --cpu 2`
4. **Deploy Frontend**: Deploy the `frontend/` directory to Vercel or Cloud Run.
