/* Shared helpers: mobile menu, CSRF token, toasts, relative time. */
(function () {
  const btn = document.getElementById("menu-btn");
  const side = document.getElementById("sidebar");
  if (btn && side) btn.addEventListener("click", () => side.classList.toggle("open"));

  window.SW = {
    csrf() {
      const m = document.querySelector('meta[name="csrf-token"]');
      return m ? m.content : "";
    },
    toast(message, ok) {
      const box = document.getElementById("toasts");
      if (!box) return;
      const t = document.createElement("div");
      t.className = "toast" + (ok ? " ok" : "");
      t.textContent = message;
      box.appendChild(t);
      setTimeout(() => t.remove(), 8000);
    },
    ago(iso) {
      const s = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
      if (s < 10) return "just now";
      if (s < 60) return s + "s ago";
      if (s < 3600) return Math.floor(s / 60) + "m ago";
      if (s < 86400) return Math.floor(s / 3600) + "h ago";
      return Math.floor(s / 86400) + "d ago";
    },
    colors: { plastic: "#3b82f6", paper: "#d97706", metal: "#64748b", glass: "#14b8a6", organic: "#84cc16" },
    countUp(el, to) {
      const start = performance.now(), dur = 900;
      (function tick(now) {
        const p = Math.min(1, (now - start) / dur);
        el.textContent = Math.round(to * p).toLocaleString();
        if (p < 1) requestAnimationFrame(tick);
      })(start);
    },
  };
})();
