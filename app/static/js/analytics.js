(function () {
  const COLORS = { plastic: "#1e88e5", paper: "#8d6e63", metal: "#78909c", glass: "#26a69a", organic: "#7cb342" };
  const FALLBACK = ["#ab47bc", "#ef5350", "#ffa726", "#5c6bc0", "#26c6da", "#9ccc65"];
  let charts = {};

  function draw(id, config) {
    if (charts[id]) charts[id].destroy();
    charts[id] = new Chart(document.getElementById(id), config);
  }

  async function load(period) {
    const res = await fetch("/admin/api/analytics?period=" + period, { credentials: "same-origin" });
    if (!res.ok) { alert("Could not load analytics."); return; }
    const d = await res.json();
    document.getElementById("empty").style.display = d.count ? "none" : "block";

    draw("timeChart", {
      type: "bar",
      data: {
        labels: d.labels,
        datasets: Object.keys(d.series).map((c) => ({ label: c, data: d.series[c], backgroundColor: COLORS[c] || "#999" })),
      },
      options: { maintainAspectRatio: false, scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true, ticks: { precision: 0 } } } },
    });

    const cats = Object.keys(d.by_category);
    draw("catChart", {
      type: "doughnut",
      data: { labels: cats, datasets: [{ data: cats.map((c) => d.by_category[c]), backgroundColor: cats.map((c, i) => COLORS[c] || FALLBACK[i % FALLBACK.length]) }] },
      options: { maintainAspectRatio: false },
    });

    const locs = Object.keys(d.by_location);
    draw("locChart", {
      type: "bar",
      data: { labels: locs, datasets: [{ label: "Items", data: locs.map((l) => d.by_location[l]), backgroundColor: "#2e7d32" }] },
      options: { maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
    });
  }

  document.querySelectorAll(".tabs button").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tabs button").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      load(btn.dataset.p);
    });
  });
  load("daily");
})();
