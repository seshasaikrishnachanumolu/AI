(function () {
  const $ = (id) => document.getElementById(id);
  const input = $("image"), preview = $("preview"), video = $("video"), canvas = $("canvas");
  const startBtn = $("cam-start"), snapBtn = $("cam-snap"), form = $("classify-form");
  const submitBtn = $("submit-btn"), drop = $("dropzone"), errBox = $("error"), loc = $("location_id");
  let stream = null;

  // Remember the last used location.
  const saved = localStorage.getItem("sw-location");
  if (saved && [...loc.options].some((o) => o.value === saved)) loc.value = saved;

  function showError(msg) { errBox.textContent = msg; errBox.style.display = msg ? "block" : "none"; }

  function showPreview(file) {
    preview.src = URL.createObjectURL(file);
    preview.style.display = "block";
    showError("");
  }
  input.addEventListener("change", () => { if (input.files[0]) showPreview(input.files[0]); });
  ["dragenter", "dragover"].forEach((e) => drop.addEventListener(e, () => drop.classList.add("over")));
  ["dragleave", "drop"].forEach((e) => drop.addEventListener(e, () => drop.classList.remove("over")));

  function stopCamera() {
    if (stream) stream.getTracks().forEach((t) => t.stop());
    stream = null; video.style.display = "none"; snapBtn.style.display = "none";
  }
  startBtn.addEventListener("click", async () => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      showError("Webcam is not supported in this browser. Please upload a file instead."); return;
    }
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: true });
      video.srcObject = stream; video.style.display = "block"; snapBtn.style.display = "inline-flex";
    } catch (e) { showError("Could not access the webcam: " + e.message); }
  });
  snapBtn.addEventListener("click", () => {
    canvas.width = video.videoWidth; canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);
    canvas.toBlob((blob) => {
      if (!blob) return;
      const file = new File([blob], "capture.jpg", { type: "image/jpeg" });
      const dt = new DataTransfer(); dt.items.add(file); input.files = dt.files;
      showPreview(file); stopCamera();
    }, "image/jpeg", 0.92);
  });

  function render(d) {
    $("placeholder").style.display = "none";
    $("result").style.display = "block";
    $("r-cat").textContent = d.category;
    $("r-tip").textContent = d.recommendation;
    $("r-link").href = d.result_url;
    const rec = $("r-rec");
    rec.textContent = d.recyclable ? "Recyclable" : "Non-recyclable (compostable / general)";
    rec.className = "badge" + (d.recyclable ? "" : " almost");
    $("r-bin").textContent = d.assigned
      ? d.bin + " (" + d.location + "), " + d.category + " compartment"
      : "No space left in the " + d.category + " compartment at this location. Collection is required.";
    const ring = $("ring");
    ring.style.setProperty("--brand", SW.colors[d.category] || "#16a34a");
    ring.style.setProperty("--p", 0);
    requestAnimationFrame(() => requestAnimationFrame(() => ring.style.setProperty("--p", d.confidence)));
    $("ring-val").textContent = Math.round(d.confidence) + "%";
    if (!d.assigned) SW.toast("Compartment full: item saved but not assigned to a bin.");
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    showError("");
    if (!loc.value) { showError("Select the disposal location."); return; }
    if (!input.files[0]) { showError("Choose an image or capture one with the webcam."); return; }
    localStorage.setItem("sw-location", loc.value);
    submitBtn.disabled = true;
    const label = submitBtn.innerHTML;
    submitBtn.textContent = "Analyzing...";
    try {
      const res = await fetch("/api/classify", {
        method: "POST",
        headers: { "X-CSRFToken": SW.csrf() },
        body: new FormData(form),
        credentials: "same-origin",
      });
      let data = {};
      try { data = await res.json(); } catch (_) {}
      if (!res.ok) { showError(data.error || "Something went wrong (" + res.status + ")."); return; }
      render(data);
    } catch (err) {
      showError("Network error. Check your connection and try again.");
    } finally {
      submitBtn.disabled = false; submitBtn.innerHTML = label;
    }
  });

  $("again").addEventListener("click", () => {
    $("result").style.display = "none"; $("placeholder").style.display = "block";
    input.value = ""; preview.style.display = "none"; showError("");
  });
})();
