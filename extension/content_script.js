// content_script.js
// Responsible for executing actions on the DOM and extracting data

window.udaa = {
    getDOMSnapshot: () => {
        return document.documentElement.outerHTML;
    },

    performClick: (x, y) => {
        // elementFromPoint evaluates viewport-relative coords, whereas x,y are layout relative
        // We must subtract scroll distances
        const viewportX = x - window.scrollX;
        const viewportY = y - window.scrollY;
        
        let element = document.elementFromPoint(viewportX, viewportY);
        // Fallback to absolute point if off-screen heuristics fail
        if (!element) element = document.elementFromPoint(x, y);

        if (element) {
            if (window.udaaOverlay) {
                window.udaaOverlay.drawHighlight(x, y);
            }

            const eventInit = {
                view: window,
                bubbles: true,
                cancelable: true,
                clientX: x,
                clientY: y,
                button: 0,
                buttons: 1
            };

            // Dispatch full event sequence for better compatibility with SPAs
            element.dispatchEvent(new PointerEvent('pointerdown', eventInit));
            element.dispatchEvent(new MouseEvent('mousedown', eventInit));
            element.dispatchEvent(new PointerEvent('pointerup', { ...eventInit, buttons: 0 }));
            element.dispatchEvent(new MouseEvent('mouseup', { ...eventInit, buttons: 0 }));
            element.dispatchEvent(new MouseEvent('click', { ...eventInit, buttons: 0 }));
            
            // Focus the element so that subsequent type actions target this element
            if (typeof element.focus === 'function') {
                element.focus();
            }

            console.log(`UDAA: Clicked at ${x}, ${y}`);
            return true;
        }
        return false;
    },

    performType: (text) => {
        const element = document.activeElement;
        if (element && (element.tagName === "INPUT" || element.tagName === "TEXTAREA" || element.isContentEditable)) {
            
            console.log(`UDAA: Received type command:`, text);

            // 1. Clean duplicated strings if AI repeated itself due to lag
            // Sometimes the model outputs "HELLOHELLO" instead of "HELLO". Let's use a heuristic:
            // If the string is exactly the same half repeated (e.g., "wordword"), cut it in half.
            if (text.length > 3) {
                const halfLen = Math.floor(text.length / 2);
                if (text.slice(0, halfLen) === text.slice(halfLen)) {
                    text = text.slice(0, halfLen);
                }
                // Check for 3 repeats (e.g. "youtube.comyoutube.comyoutube.com")
                const thirdLen = Math.floor(text.length / 3);
                if (thirdLen > 2 && text.slice(0, thirdLen) === text.slice(thirdLen, thirdLen * 2) && text.slice(0, thirdLen) === text.slice(thirdLen * 2, thirdLen * 3)) {
                    text = text.slice(0, thirdLen);
                }
            }

            // 2. Extract special shortcuts (e.g. control+a, delete, backspace*N)
            const specialKeysRegex = /(control\+[a-z]|cmd\+[a-z]|shift\+[a-z]|alt\+[a-z]|enter|backspace(?:\*\d+)?|delete(?:\*\d+)?|tab|escape)/gi;
            let specialActions = text.match(specialKeysRegex) || [];
            let remainingText = text.replace(specialKeysRegex, '').trim();

            // 3. Apply standard text if any remains
            if (remainingText.length > 0) {
                if (element.isContentEditable) {
                    // This creates proper input events for WhatsApp/Facebook
                    const range = document.createRange();
                    range.selectNodeContents(element);
                    const sel = window.getSelection();
                    sel.removeAllRanges();
                    sel.addRange(range);
                    document.execCommand('delete', false, null); // clear existing
                    document.execCommand('insertText', false, remainingText);
                } else {
                    // React/Vue friendly value setting
                    let nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value")?.set;
                    let nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value")?.set;
                    
                    if (element.tagName === 'INPUT' && nativeInputValueSetter) {
                        nativeInputValueSetter.call(element, remainingText);
                    } else if (element.tagName === 'TEXTAREA' && nativeTextAreaValueSetter) {
                        nativeTextAreaValueSetter.call(element, remainingText);
                    } else {
                        element.value = remainingText; // fallback
                    }
                }
            }

            // 4. Apply special actions
            for (let action of specialActions) {
                action = action.toLowerCase();
                
                if (action === 'control+a' || action === 'cmd+a') {
                    if (element.setSelectionRange && element.value !== undefined) {
                        element.setSelectionRange(0, element.value.length);
                    } else if (element.isContentEditable) {
                        const range = document.createRange();
                        range.selectNodeContents(element);
                        const sel = window.getSelection();
                        sel.removeAllRanges();
                        sel.addRange(range);
                    }
                } else if (action.startsWith('backspace')) {
                    let count = 1;
                    const match = action.match(/backspace\*(\d+)/);
                    if (match) count = parseInt(match[1]);
                    if (element.value) element.value = element.value.slice(0, -count);
                    else if (element.innerText) element.innerText = element.innerText.slice(0, -count);
                } else if (action.startsWith('delete')) {
                    let count = 1;
                    const match = action.match(/delete\*(\d+)/);
                    if (match) count = parseInt(match[1]);
                    // Delete is tricky without knowing cursor position, fallback to clearing value
                    if (element.value !== undefined) element.value = "";
                    else if (element.innerText !== undefined) element.innerText = "";
                } else if (action === 'enter') {
                    // Fire a more complete set of enter key events
                    setTimeout(() => {
                        const keyEvents = ['keydown', 'keypress', 'keyup'];
                        for (let ev of keyEvents) {
                            element.dispatchEvent(new KeyboardEvent(ev, { 
                                key: 'Enter', 
                                code: 'Enter', 
                                keyCode: 13, 
                                which: 13, 
                                bubbles: true,
                                cancelable: true
                            }));
                        }
                        if (element.form) element.form.submit();
                    }, 50);
                } else if (action === 'escape') {
                    element.blur();
                }
            }
            
            element.dispatchEvent(new Event('input', { bubbles: true }));
            element.dispatchEvent(new Event('change', { bubbles: true }));
            console.log(`UDAA: Applied type result`);
            return true;
        }
        return false;
    },

    performHover: (x, y) => {
        const element = document.elementFromPoint(x, y);
        if (element) {
            if (window.udaaOverlay) {
                window.udaaOverlay.drawHighlight(x, y);
            }
            const eventInit = {
                view: window,
                bubbles: true,
                cancelable: true,
                clientX: x,
                clientY: y
            };
            element.dispatchEvent(new PointerEvent('pointermove', eventInit));
            element.dispatchEvent(new MouseEvent('mouseover', eventInit));
            element.dispatchEvent(new MouseEvent('mouseenter', eventInit));
            element.dispatchEvent(new MouseEvent('mousemove', eventInit));
            console.log(`UDAA: Hovered at ${x}, ${y}`);
            return true;
        }
        return false;
    },

    performKeyCombination: (keysRaw) => {
        const element = document.activeElement || document.body;
        
        // Fix for TypeError: keys.join is not a function
        let keys = [];
        if (Array.isArray(keysRaw)) {
            keys = keysRaw;
        } else if (typeof keysRaw === 'string') {
            keys = [keysRaw];
        } else {
            return false;
        }
        
        console.log(`UDAA: Key combo: ${keys.join('+')}`);
        
        // Dispatch keydown for all
        for (let key of keys) {
            element.dispatchEvent(new KeyboardEvent('keydown', {
                key: key,
                code: key,
                bubbles: true,
                cancelable: true
            }));
        }
        
        // Dispatch keyup in reverse
        for (let i = keys.length - 1; i >= 0; i--) {
            element.dispatchEvent(new KeyboardEvent('keyup', {
                key: keys[i],
                code: keys[i],
                bubbles: true,
                cancelable: true
            }));
        }
        return true;
    },

    performScroll: (direction, amount = 3) => {
        const delta = direction === "down" ? amount * 100 : -(amount * 100);
        window.scrollBy({ top: delta, behavior: "smooth" });
        console.log(`UDAA: Scrolled ${direction} by ${delta}`);
        return true;
    }
};

// Listen for action commands from the background service worker
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.type === "EXECUTE_ACTION") {
        let success = false;
        const { action, args } = request.payload;

        try {
            if (action === "click_at" || action === "click" || action === "left_click") {
                // Gemini returns normalized coordinates [0, 1000]
                let x = args.x;
                let y = args.y;
                
                if (args.coordinates && args.coordinates.length >= 2) {
                    // Convert from 1000x1000 grid to actual viewport sizing
                    x = Math.round((args.coordinates[0] / 1000) * window.innerWidth);
                    y = Math.round((args.coordinates[1] / 1000) * window.innerHeight);
                } else if (typeof x === "number" && typeof y === "number") {
                    x = Math.round((x / 1000) * window.innerWidth);
                    y = Math.round((y / 1000) * window.innerHeight);
                }
                
                success = window.udaa.performClick(x, y);
            } else if (action === "type_text_at" || action === "type") {
                // If coordinates are provided, focus/click the element first
                if (args.x !== undefined && args.y !== undefined) {
                    let tx = args.x;
                    let ty = args.y;
                    if (args.coordinates && args.coordinates.length >= 2) {
                        tx = Math.round((args.coordinates[0] / 1000) * window.innerWidth);
                        ty = Math.round((args.coordinates[1] / 1000) * window.innerHeight);
                    } else if (typeof tx === "number" && typeof ty === "number") {
                        tx = Math.round((tx / 1000) * window.innerWidth);
                        ty = Math.round((ty / 1000) * window.innerHeight);
                    }
                    window.udaa.performClick(tx, ty);
                }
                success = window.udaa.performType(args.text);
            } else if (action === "hover_at" || action === "hover") {
                let hx = args.x;
                let hy = args.y;
                if (args.coordinates && args.coordinates.length >= 2) {
                    hx = Math.round((args.coordinates[0] / 1000) * window.innerWidth);
                    hy = Math.round((args.coordinates[1] / 1000) * window.innerHeight);
                } else if (typeof hx === "number" && typeof hy === "number") {
                    hx = Math.round((hx / 1000) * window.innerWidth);
                    hy = Math.round((hy / 1000) * window.innerHeight);
                }
                success = window.udaa.performHover(hx, hy);
            } else if (action === "key_combination") {
                success = window.udaa.performKeyCombination(args.keys || []);
            } else if (action === "scroll_document" || action === "scroll") {
                success = window.udaa.performScroll(args.direction || "down", args.amount || 3);
            } else if (action === "scroll_at") {
                // Hover first, then scroll
                let sx = args.x;
                let sy = args.y;
                if (args.coordinates && args.coordinates.length >= 2) {
                    sx = Math.round((args.coordinates[0] / 1000) * window.innerWidth);
                    sy = Math.round((args.coordinates[1] / 1000) * window.innerHeight);
                } else if (typeof sx === "number" && typeof sy === "number") {
                    sx = Math.round((sx / 1000) * window.innerWidth);
                    sy = Math.round((sy / 1000) * window.innerHeight);
                }
                window.udaa.performHover(sx, sy);
                success = window.udaa.performScroll(args.direction || "down", args.amount || 3);
            } else if (action === "navigate") {
                window.location.href = args.url;
                success = true;
            } else if (action === "open_web_browser") {
                if (args.url && args.url !== "about:blank") window.location.href = args.url;
                success = true;
            }

            sendResponse({ success, action });
        } catch (e) {
            console.error("UDAA execution error:", e);
            sendResponse({ success: false, action, detail: e.toString() });
        }
    } else if (request.type === "UDAA_STATUS") {
        if (request.payload) {
            const status = request.payload.status;
            const msg = `UDAA: ${request.payload.message}`;
            const type = (status === "completed" || status === "error" || status === "timeout" || status === "cancelled") 
                ? (status === "completed" ? "completed" : "error") 
                : "active";

            // If the overlay library loaded, use it
            if (window.udaaOverlay && typeof window.udaaOverlay.showStatus === 'function') {
                if (status === "cancelled") {
                     window.udaaOverlay.hideStatus();
                } else {
                     window.udaaOverlay.showStatus(msg, type);
                     if (type !== 'active') {
                         setTimeout(() => window.udaaOverlay.hideStatus(), 5000);
                     }
                }
            } else {
                // Fallback: Build banner directly if overlay.js was blocked by CSP
                let banner = document.getElementById("udaa-status-banner-fallback");
                if (!banner) {
                    banner = document.createElement("div");
                    banner.id = "udaa-status-banner-fallback";
                    banner.style.position = "fixed";
                    banner.style.bottom = "20px";
                    banner.style.right = "20px";
                    banner.style.padding = "12px 20px";
                    banner.style.borderRadius = "8px";
                    banner.style.backgroundColor = "#1a1a2e";
                    banner.style.color = "#ffffff";
                    banner.style.fontFamily = "sans-serif";
                    banner.style.fontSize = "14px";
                    banner.style.fontWeight = "bold";
                    banner.style.zIndex = "999999";
                    banner.style.boxShadow = "0 4px 15px rgba(0,0,0,0.5)";
                    document.body.appendChild(banner);
                }
                
                banner.textContent = msg;
                if (type === 'active') {
                    banner.style.border = "2px solid #00f2fe";
                    banner.style.color = "#00f2fe";
                } else if (type === 'completed') {
                    banner.style.border = "2px solid #2ecc71";
                    banner.style.color = "#2ecc71";
                    setTimeout(() => { if (banner) banner.remove(); }, 5000);
                } else {
                    banner.style.border = "2px solid #e74c3c";
                    banner.style.color = "#e74c3c";
                    setTimeout(() => { if (banner) banner.remove(); }, 5000);
                }
                if (status === "cancelled") {
                    if (banner) banner.remove();
                }
            }
        }
    }
});

if (!window.__udaaConnectInitialized) {
    window.__udaaConnectInitialized = true;
    
    // Auto-connect flow: check if a session ID was passed via URL or injected by Playwright
    let connectAttempts = 0;
    const connectInterval = setInterval(() => {
        connectAttempts++;
        
        // 1. Check URL parameters (for native webbrowser launch)
        const urlParams = new URLSearchParams(window.location.search);
        let sessionId = urlParams.get('udaa_session_id');
        
        // 2. Check localStorage (for Playwright launch)
        if (!sessionId) {
            sessionId = window.localStorage.getItem('udaa_session_id');
        }

        if (sessionId) {
            console.log("UDAA Content Script: Found Session ID. Instructing background worker to connect...");
            chrome.runtime.sendMessage({ type: "CONNECT_WS", sessionId: sessionId });
            clearInterval(connectInterval);
        } else if (connectAttempts > 10) {
            // Stop trying after 5 seconds (10 * 500ms)
            clearInterval(connectInterval);
        }
    }, 500);
}
