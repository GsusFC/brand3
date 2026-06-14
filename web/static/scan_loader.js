// Generative scan loader for the in-flight waiting screen.
//
// A dark "scanner" stage boots with procedural film grain + RGB glitch and a
// rotating 3D cloud of skeleton cards (precarga). As the /assets endpoint
// surfaces the brand's real captured imagery, cards fill in and the cloud keeps
// spinning with inertia. Decorative + non-blocking; degrades to a calm static
// cloud under prefers-reduced-motion.
(() => {
  const loader = document.querySelector("[data-scan-loader]");
  if (!loader || !window.Brand3Cloud) return;

  const statusRoot = document.querySelector("[data-status-waiting]");
  const stage = loader.querySelector("[data-loader-stage]");
  const grain = loader.querySelector("[data-loader-grain]");
  const captionNode = loader.querySelector("[data-loader-caption]");
  const countNode = loader.querySelector("[data-loader-count]");
  if (!stage || !(grain instanceof HTMLCanvasElement)) return;

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const assetsHref = loader.getAttribute("data-assets-href") || "";
  const pollMs = Number(loader.getAttribute("data-poll-interval")) || 2500;

  let captions = {};
  const captionData = loader.querySelector("[data-loader-captions]");
  if (captionData) {
    try { captions = JSON.parse(captionData.textContent || "{}"); } catch { captions = {}; }
  }

  // --- rotating cloud (shared engine) ---------------------------------------
  const cloud = window.Brand3Cloud.mount(stage, {
    autoRotate: true,
    interactive: true,
    allowZoom: false,
    onFill: (n) => { if (countNode) countNode.textContent = String(n); },
  });
  cloud.buildPlaceholders(20);

  // --- procedural grain + glitch --------------------------------------------
  const gctx = grain.getContext("2d");
  let noiseTile = null;
  // Reused noise patch canvas — allocated once, not per frame, to keep the
  // grain loop allocation-free.
  const noiseCanvas = document.createElement("canvas");
  const noiseCtx = noiseCanvas.getContext("2d");
  let grainRaf = 0;
  let lastGrain = 0;
  let visible = true;

  const sizeGrain = () => {
    const rect = stage.getBoundingClientRect();
    grain.width = Math.max(160, Math.round(rect.width / 2));
    grain.height = Math.max(120, Math.round(rect.height / 2));
    noiseTile = gctx.createImageData(96, 72);
    noiseCanvas.width = noiseTile.width;
    noiseCanvas.height = noiseTile.height;
  };

  const drawNoise = () => {
    if (!gctx || !noiseTile) return;
    const data = noiseTile.data;
    for (let i = 0; i < data.length; i += 4) {
      const v = (Math.random() * 255) | 0;
      data[i] = data[i + 1] = data[i + 2] = v;
      data[i + 3] = (Math.random() * 42) | 0;
    }
    noiseCtx.putImageData(noiseTile, 0, 0);
    const pattern = gctx.createPattern(noiseCanvas, "repeat");
    gctx.clearRect(0, 0, grain.width, grain.height);
    gctx.fillStyle = pattern;
    gctx.fillRect(0, 0, grain.width, grain.height);
    if (Math.random() < 0.22) {
      const bands = 1 + ((Math.random() * 3) | 0);
      gctx.globalCompositeOperation = "screen";
      for (let b = 0; b < bands; b += 1) {
        const y = (Math.random() * grain.height) | 0;
        const h = 1 + ((Math.random() * 6) | 0);
        const off = 2 + ((Math.random() * 8) | 0);
        gctx.fillStyle = "rgba(255,0,40,0.5)";
        gctx.fillRect(-off, y, grain.width, h);
        gctx.fillStyle = "rgba(0,225,255,0.5)";
        gctx.fillRect(off, y + 1, grain.width, h);
      }
      gctx.globalCompositeOperation = "source-over";
    }
  };

  const grainLoop = (time) => {
    if (!visible) { grainRaf = 0; return; }
    if (time - lastGrain > 80) { drawNoise(); lastGrain = time; }
    grainRaf = requestAnimationFrame(grainLoop);
  };
  const startGrain = () => {
    if (reducedMotion.matches) { drawNoise(); return; }
    if (!grainRaf) { lastGrain = 0; grainRaf = requestAnimationFrame(grainLoop); }
  };
  const stopGrain = () => { if (grainRaf) { cancelAnimationFrame(grainRaf); grainRaf = 0; } };

  // --- caption follows the pipeline phase -----------------------------------
  const syncCaption = () => {
    if (!captionNode || !statusRoot) return;
    const phase = statusRoot.getAttribute("data-phase") || "";
    const text = captions[phase];
    if (text && captionNode.textContent !== text) captionNode.textContent = text;
  };

  // --- asset polling --------------------------------------------------------
  const isWaiting = () => {
    const status = statusRoot ? statusRoot.getAttribute("data-status") : "running";
    return status === "queued" || status === "running";
  };
  let pollInFlight = false;
  const pollAssets = async () => {
    if (pollInFlight || !assetsHref || document.hidden || !isWaiting()) return;
    pollInFlight = true;
    try {
      const res = await fetch(assetsHref, { cache: "no-store", credentials: "same-origin" });
      if (!res.ok) return;
      const data = await res.json();
      if (Array.isArray(data.images) && data.images.length) cloud.addImages(data.images);
    } catch {
      // transient — retry next interval
    } finally {
      pollInFlight = false;
    }
  };

  // --- lifecycle ------------------------------------------------------------
  const setVisible = (next) => {
    visible = next;
    cloud.setVisible(next);
    if (next) startGrain();
    else stopGrain();
  };

  sizeGrain();
  startGrain();
  syncCaption();
  pollAssets();
  window.setInterval(pollAssets, pollMs);
  window.setInterval(syncCaption, 1000);

  let resizeTimer = 0;
  window.addEventListener("resize", () => {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(sizeGrain, 200);
  });
  document.addEventListener("visibilitychange", () => setVisible(!document.hidden));
  if ("IntersectionObserver" in window) {
    new IntersectionObserver(
      ([entry]) => setVisible(entry.isIntersecting && !document.hidden),
      { threshold: 0.05 },
    ).observe(stage);
  }
  if (reducedMotion.addEventListener) {
    reducedMotion.addEventListener("change", () => { stopGrain(); startGrain(); });
  }
})();
