// Report moodboard — a rotating 3D cloud of the brand's captured imagery.
// Shares the Brand3Cloud engine with the scan loader: drag to rotate (with
// inertia), wheel to zoom, shuffle to recompose. Dark "scanner" stage with film
// grain to match the loader aesthetic. Falls back gracefully if the engine or
// data is missing.
(() => {
  const stage = document.querySelector("[data-moodboard-stage]");
  const dataNode = document.querySelector("[data-moodboard-items]");
  if (!stage || !dataNode || !window.Brand3Cloud) return;

  let items = [];
  try { items = JSON.parse(dataNode.textContent || "[]"); } catch { return; }
  if (!Array.isArray(items) || items.length === 0) return;

  const cloud = window.Brand3Cloud.mount(stage, {
    autoRotate: true,
    interactive: true,
    allowZoom: true,
  });
  cloud.setImages(items);

  const shuffleButton = document.querySelector("[data-moodboard-shuffle]");
  if (shuffleButton) {
    shuffleButton.addEventListener("click", () => cloud.reshuffle());
  }

  // Film grain overlay to match the loader's scanner texture.
  const grain = stage.querySelector("[data-moodboard-grain]");
  if (grain instanceof HTMLCanvasElement) {
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const gctx = grain.getContext("2d");
    let noiseTile = null;
    let raf = 0;
    let last = 0;
    let visible = true;

    const size = () => {
      const rect = stage.getBoundingClientRect();
      grain.width = Math.max(160, Math.round(rect.width / 2));
      grain.height = Math.max(120, Math.round(rect.height / 2));
      noiseTile = gctx.createImageData(96, 72);
    };
    const draw = () => {
      if (!gctx || !noiseTile) return;
      const data = noiseTile.data;
      for (let i = 0; i < data.length; i += 4) {
        const v = (Math.random() * 255) | 0;
        data[i] = data[i + 1] = data[i + 2] = v;
        data[i + 3] = (Math.random() * 36) | 0;
      }
      const tmp = document.createElement("canvas");
      tmp.width = noiseTile.width;
      tmp.height = noiseTile.height;
      tmp.getContext("2d").putImageData(noiseTile, 0, 0);
      gctx.clearRect(0, 0, grain.width, grain.height);
      gctx.fillStyle = gctx.createPattern(tmp, "repeat");
      gctx.fillRect(0, 0, grain.width, grain.height);
    };
    const loop = (t) => {
      if (!visible) { raf = 0; return; }
      if (t - last > 90) { draw(); last = t; }
      raf = requestAnimationFrame(loop);
    };
    const start = () => {
      if (reducedMotion.matches) { draw(); return; }
      if (!raf) { last = 0; raf = requestAnimationFrame(loop); }
    };
    const stop = () => { if (raf) { cancelAnimationFrame(raf); raf = 0; } };

    size();
    start();
    let resizeTimer = 0;
    window.addEventListener("resize", () => {
      window.clearTimeout(resizeTimer);
      resizeTimer = window.setTimeout(size, 200);
    });
    document.addEventListener("visibilitychange", () => {
      visible = !document.hidden;
      cloud.setVisible(visible);
      if (visible) start();
      else stop();
    });
  }
})();
