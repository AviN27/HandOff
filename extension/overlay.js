// overlay.js
// Injects a visual overlay to highlight target elements for explainability

window.udaaOverlay = {
    drawHighlight: (x, y, width = 20, height = 20) => {
        const el = document.createElement("div");
        el.style.position = "fixed";
        el.style.left = `${x - width / 2}px`;
        settingsTop = `${y - height / 2}px`;
        el.style.top = settingsTop;
        el.style.width = `${width}px`;
        el.style.height = `${height}px`;
        el.style.border = "3px solid #00f2fe"; // UDAA cyan
        el.style.backgroundColor = "rgba(0, 242, 254, 0.2)";
        el.style.borderRadius = "4px";
        el.style.pointerEvents = "none";
        el.style.zIndex = "999999";
        el.style.transition = "all 0.3s ease";

        document.body.appendChild(el);

        // Auto-remove after 1.5 seconds
        setTimeout(() => {
            el.style.opacity = "0";
            setTimeout(() => el.remove(), 300);
        }, 1500);
    }
};
