// background.js
// Service worker managing extension lifecycle and the WebSocket bridge

let ws = null;
let streamingInterval = null;
let currentSessionId = null;

chrome.runtime.onInstalled.addListener(() => {
    console.log("UDAA Live Controller installed.");
});

function connectWebSocket(sessionId) {
    if (ws) ws.close();
    currentSessionId = sessionId;

    ws = new WebSocket(`ws://localhost:8080/ws/live_ext/${sessionId}`);

    ws.onopen = () => {
        console.log("UDAA Extension: Connected to backend for session", sessionId);
        startStreamingFrames();
    };

    ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === "execute_action") {
            executeInActiveTab(message);
        } else if (message.type === "stop_stream") {
            stopStreamingFrames();
        }
    };

    ws.onclose = () => {
        console.log("UDAA Extension: Disconnected");
        stopStreamingFrames();
    };
}

function executeInActiveTab(command) {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (tabs.length === 0) return;
        const activeTab = tabs[0];

        // Inject overlay if not already present
        chrome.scripting.executeScript({
            target: { tabId: activeTab.id },
            files: ["overlay.js", "content_script.js"]
        }, () => {
            // Send message to the content script in the active tab
            chrome.tabs.sendMessage(activeTab.id, {
                type: "EXECUTE_ACTION",
                payload: { action: command.action, args: command }
            }, (response) => {
                // Report result back to backend
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({
                        type: "action_result",
                        result: response || { action: command.action, success: false, detail: "No response from tab" }
                    }));
                }
            });
        });
    });
}

function startStreamingFrames() {
    if (streamingInterval) return;
    // Capture screen at ~2 FPS (500ms) and send to backend
    streamingInterval = setInterval(() => {
        chrome.tabs.captureVisibleTab(null, { format: "png" }, (dataUrl) => {
            if (chrome.runtime.lastError) {
                console.error(chrome.runtime.lastError.message);
                return;
            }

            if (dataUrl && ws && ws.readyState === WebSocket.OPEN) {
                chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
                    let url = "unknown";
                    if (tabs.length > 0) url = tabs[0].url;

                    ws.send(JSON.stringify({
                        type: "screen_frame",
                        image: dataUrl.split(',')[1],
                        url: url
                    }));
                });
            }
        });
    }, 500);
}

function stopStreamingFrames() {
    if (streamingInterval) {
        clearInterval(streamingInterval);
        streamingInterval = null;
    }
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.type === "CONNECT_WS") {
        console.log("UDAA Extension: Received auto-connect request for session", request.sessionId);
        connectWebSocket(request.sessionId);
    }
});

// Keep manual fallback just in case
chrome.action.onClicked.addListener((tab) => {
    chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: (current) => prompt("Enter UDAA Session ID to connect Live Browser:", current || ""),
        args: [currentSessionId]
    }, (results) => {
        if (chrome.runtime.lastError) {
            console.error(chrome.runtime.lastError.message);
            return;
        }
        if (results && results[0] && results[0].result) {
            connectWebSocket(results[0].result);
        }
    });
});
