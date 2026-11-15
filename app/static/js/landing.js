/* Landing page: real aggregate counters from /api/public-stats. */
(async function () {
  try {
    const res = await fetch("/api/public-stats");
    if (!res.ok) return;
    const d = await res.json();
    document.querySelectorAll("[data-s]").forEach((el) => {
      const v = d[el.dataset.s];
      if (typeof v === "number") SW.countUp(el, v);
    });
  } catch (e) { /* counters stay at 0 */ }
})();
