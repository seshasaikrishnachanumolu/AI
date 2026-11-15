/* Live admin dashboard: polls /admin/api/live and updates the page in place. */
(function () {
  const POLL_MS = 5000;
  const ALMOST = 70, ALERT = 90;
  const liveEl = document.getElementById("live"), liveTxt = document.getElementById("live-txt");
  const feed = document.getElementById("feed"), binsEl = document.getElementById("bins"), alertsEl = document.getElementById("alerts");
  const cats = ["plastic", "paper", "metal", "glass", "organic"];
  let lastAlertId = null, lastRecordId = null, first = true, chart = null;

  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  const barCls = (v) => (v >= ALERT ? "full" : v >= ALMOST ? "almost" : "");

  function setStat(key, value) {
    const box = document.querySelector('[data-k="' + key + '"]');
    if (!box) return;
    const num = box.querySelector(".num");
    if (num && num.textContent !== String(value)) {
      num.textContent = value;
      box.classList.remove("flash-up"); void box.offsetWidth; box.classList.add("flash-up");
    }
  }

  function drawChart(counts) {
    const data = cats.map((c) => counts[c] || 0);
    if (!chart) {
      chart = new Chart(document.getElementById("catChart"), {
        type: "doughnut",
        data: { labels: cats.map((c) => c[0].toUpperCase() + c.slice(1)), datasets: [{ data, backgroundColor: cats.map((c) => SW.colors[c]), borderWidth: 2 }] },
        options: { maintainAspectRatio: false, cutout: "62%", plugins: { legend: { position: "bottom" } } },
      });
    } else {
      chart.data.datasets[0].data = data; chart.update();
    }
  }

  function renderBins(bins) {
    binsEl.replaceChildren();
    if (!bins.length) { binsEl.appendChild(el("div", "empty", "No bins yet. Create one on the Smart bins page.")); return; }
    bins.forEach((b) => {
      const cls = b.status === "Collection Required" ? "full" : b.status === "Almost Full" ? "almost" : "";
      const a = el("a", "bin-card " + cls); a.href = b.url;
      const hd = el("div", "hd");
      const left = el("div"); left.appendChild(el("div", "nm", b.name)); left.appendChild(el("div", "loc", b.location));
      hd.appendChild(left); hd.appendChild(el("span", "badge " + cls, b.status)); a.appendChild(hd);
      b.compartments.forEach((c) => {
        const row = el("div", "comp"); row.style.setProperty("--cc", SW.colors[c.category]);
        row.appendChild(el("span", "k", c.category));
        const p = el("div", "progress"); const s = el("span", c.fill >= ALERT ? "full" : ""); s.style.width = c.fill + "%"; p.appendChild(s);
        row.appendChild(p); row.appendChild(el("span", "v", Math.round(c.fill) + "%")); a.appendChild(row);
      });
      binsEl.appendChild(a);
    });
  }

  function renderFeed(recent) {
    feed.replaceChildren();
    if (!recent.length) { feed.appendChild(el("li", "empty", "No activity yet. Classified items will appear here instantly.")); return; }
    recent.forEach((r) => {
      const li = el("li", !first && lastRecordId !== null && r.id > lastRecordId ? "new" : "");
      li.appendChild(el("span", "pill " + r.category, r.category));
      li.appendChild(el("span", null, r.confidence + "% · " + r.user + (r.location ? " · " + r.location : " · unassigned")));
      li.appendChild(el("span", "t", SW.ago(r.at)));
      feed.appendChild(li);
    });
  }

  function renderAlerts(alerts) {
    alertsEl.replaceChildren();
    if (!alerts.length) { alertsEl.appendChild(el("li", "empty", "No open alerts.")); return; }
    alerts.forEach((a) => {
      const li = el("li"); li.appendChild(el("span", "badge full", "Alert")); li.appendChild(el("span", null, a.message));
      li.appendChild(el("span", "t", SW.ago(a.at))); alertsEl.appendChild(li);
    });
  }

  function setLive(ok, txt) {
    liveEl.classList.toggle("off", !ok);
    liveTxt.textContent = txt;
  }

  async function poll() {
    try {
      const res = await fetch("/admin/api/live", { credentials: "same-origin", cache: "no-store" });
      if (res.status === 401 || res.status === 403 || res.redirected) { setLive(false, "Session expired. Log in again"); return; }
      if (!res.ok) throw new Error(res.status);
      const d = await res.json();

      Object.entries(d.stats).forEach(([k, v]) => { if (typeof v === "number") setStat(k, v); });
      cats.forEach((c) => setStat("cat-" + c, d.stats.categories[c] || 0));
      drawChart(d.stats.categories);
      renderBins(d.bins);
      renderFeed(d.recent);
      renderAlerts(d.alerts);

      if (lastAlertId !== null && d.latest_alert_id > lastAlertId) {
        d.alerts.filter((a) => a.id > lastAlertId).forEach((a) => SW.toast("⚠ " + a.message));
      }
      lastAlertId = d.latest_alert_id;
      lastRecordId = d.recent.length ? d.recent[0].id : 0;
      first = false;
      setLive(true, "Live · updated " + new Date().toLocaleTimeString());
    } catch (e) {
      setLive(false, "Reconnecting…");
    }
  }

  poll();
  setInterval(() => { if (!document.hidden) poll(); }, POLL_MS);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) poll(); });
})();
