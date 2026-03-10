// websocket_client.js
// Handles communication with the UDAA FastAPI backend

class UDAAWebSocketClient {
    constructor(endpoint) {
        this.endpoint = endpoint;
        this.ws = null;
        this.streamingInterval = null;
    }

    connect(sessionId) {
        this.ws = new WebSocket(`${this.endpoint}/${sessionId}`);

        this.ws.onopen = () => {
            console.log("UDAA Extension: Connected to backend");
        };

        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            if (message.type === "execute_action") {
                this.handleAction(message.action, message);
            } else if (message.type === "start_stream") {
                this.startStreamingFrames();
            } else if (message.type === "stop_stream") {
                this.stopStreamingFrames();
            }
        };

        this.ws.onclose = () => {
            console.log("UDAA Extension: Disconnected");
            this.stopStreamingFrames();
        };
    }

    startStreamingFrames() {
        if (this.streamingInterval) return;
        // Capture screen at ~2 FPS and send to backend
        this.streamingInterval = setInterval(() => {
            chrome.runtime.sendMessage({ type: "CAPTURE_SCREENSHOT" }, (response) => {
                if (response && response.dataUrl) {
                    this.ws.send(JSON.stringify({
                        type: "screen_frame",
                        image: response.dataUrl.split(',')[1],
                        url: window.location.href
                    }));
                }
            });
        }, 500);
    }

    stopStreamingFrames() {
        if (this.streamingInterval) {
            clearInterval(this.streamingInterval);
            this.streamingInterval = null;
        }
    }

    handleAction(actionName, msg) {
        let result = { action: actionName, success: false };

        if (actionName === "click_at") {
            result.success = window.udaa.performClick(msg.x, msg.y);
        } else if (actionName === "type_text_at" || actionName === "type") {
            result.success = window.udaa.performType(msg.text);
        } else if (actionName === "scroll") {
            result.success = window.udaa.performScroll(msg.direction);
        }

        this.ws.send(JSON.stringify({
            type: "action_result",
            result: result
        }));
    }
}

window.udaaClient = new UDAAWebSocketClient("ws://localhost:8080/ws/live_ext");
