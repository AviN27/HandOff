// content_script.js
// Responsible for executing actions on the DOM and extracting data

window.udaa = {
    getDOMSnapshot: () => {
        return document.documentElement.outerHTML;
    },

    performClick: (x, y) => {
        // We expect absolute coordinates within the layout viewport
        const element = document.elementFromPoint(x, y);
        if (element) {
            if (window.udaaOverlay) {
                window.udaaOverlay.drawHighlight(x, y);
            }

            // Simulate click
            element.dispatchEvent(new MouseEvent('click', {
                view: window,
                bubbles: true,
                cancelable: true,
                clientX: x,
                clientY: y
            }));
            console.log(`UDAA: Clicked at ${x}, ${y}`);
            return true;
        }
        return false;
    },

    performType: (text) => {
        const element = document.activeElement;
        if (element && (element.tagName === "INPUT" || element.tagName === "TEXTAREA" || element.isContentEditable)) {
            element.value = (element.value || "") + text;
            element.dispatchEvent(new Event('input', { bubbles: true }));
            element.dispatchEvent(new Event('change', { bubbles: true }));
            console.log(`UDAA: Typed text`);
            return true;
        }
        return false;
    },

    performScroll: (direction) => {
        const amount = direction === "down" ? 500 : -500;
        window.scrollBy({ top: amount, behavior: "smooth" });
        console.log(`UDAA: Scrolled ${direction}`);
        return true;
    }
};

// Listen for action commands from the background service worker
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.type === "EXECUTE_ACTION") {
        let success = false;
        const { action, args } = request.payload;

        if (action === "click_at") {
            success = window.udaa.performClick(args.x, args.y);
        } else if (action === "type_text_at" || action === "type") {
            success = window.udaa.performType(args.text);
        } else if (action === "scroll_document" || action === "scroll") {
            success = window.udaa.performScroll(args.direction || "down");
        }

        sendResponse({ success, action });
        sendResponse({ success, action });
    }
});

// Auto-connect flow: check if a session ID was injected into localStorage by the Playwright launch process
setTimeout(() => {
    const sessionId = window.localStorage.getItem('udaa_session_id');
    if (sessionId) {
        console.log("UDAA Content Script: Found auto-injected Session ID. Instructing background worker to connect...");
        chrome.runtime.sendMessage({ type: "CONNECT_WS", sessionId: sessionId });
    }
}, 500);
